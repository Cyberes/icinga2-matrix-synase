#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import sys
import time
import traceback
import urllib
from datetime import datetime
from uuid import uuid4

from nio import AsyncClient, AsyncClientConfig, JoinError, JoinResponse, LoginResponse, RoomCreateError, RoomGetEventResponse, RoomSendError

import checker.nagios as nagios
from checker.synapse_client import leave_all_rooms_async, leave_room_async

parser = argparse.ArgumentParser(description='Test federation between two homeservers.')
parser.add_argument('--bot1-user', required=True, help='User ID for bot 1.')
parser.add_argument('--bot1-pw', required=True, help='Password for bot 1.')
parser.add_argument('--bot1-hs', required=True, help='Homeserver for bot 1.')
parser.add_argument('--bot1-auth-file', help="File to cache the bot's login details to.")
parser.add_argument('--bot2-user', required=True, help='User ID for bot 2.')
parser.add_argument('--bot2-pw', required=True, help='Password for bot 2.')
parser.add_argument('--bot2-hs', required=True, help='Homeserver for bot 2.')
parser.add_argument('--bot2-auth-file', help="File to cache the bot's login details to.")
parser.add_argument('--timeout', type=float, default=90, help='Request timeout limit.')
parser.add_argument('--warn', type=float, default=2.0, help='Manually set warn level.')
parser.add_argument('--crit', type=float, default=2.5, help='Manually set critical level.')
args = parser.parse_args()

bot1_hs_domain = urllib.parse.urlparse(args.bot1_hs).netloc
bot2_hs_domain = urllib.parse.urlparse(args.bot2_hs).netloc


def write_details_to_disk(resp: LoginResponse, homeserver, config_file) -> None:
    """Writes the required login details to disk so we can log in later without
    using a password.
    Arguments:
        resp {LoginResponse} -- the successful client login response.
        homeserver -- URL of homeserver, e.g. "https://matrix.example.org"
    """
    # open the config file in write-mode
    with open(config_file, "w") as f:
        # write the login details to disk
        json.dump({"homeserver": homeserver,  # e.g. "https://matrix.example.org"
                   "user_id": resp.user_id,  # e.g. "@user:example.org"
                   "device_id": resp.device_id,  # device ID, 10 uppercase letters
                   "access_token": resp.access_token,  # cryptogr. access token
                   }, f, )


async def test_one_direction(sender_client, receiver_client, receiver_user_id):
    # The sender creates the room and invites the receiver
    test_room_name = str(uuid4())
    new_test_room = await sender_client.room_create(name=test_room_name, invite=[receiver_user_id])
    if isinstance(new_test_room, RoomCreateError):
        return f'UNKNOWN: failed to create room "{new_test_room}"', nagios.UNKNOWN, []
    new_test_room_id = new_test_room.room_id

    time.sleep(2)

    # The receiver joins via invite
    timeout_start = datetime.now()
    while True:
        resp = await receiver_client.join(new_test_room_id)
        if isinstance(resp, JoinResponse):
            break
        elif isinstance(resp, JoinError):
            leave = [await leave_room_async(new_test_room_id, sender_client)]
            leave_failures = []
            for event in leave:
                if not event[0]:
                    leave_failures.append((event[1], event[2]))
            return f'UNKNOWN: failed to join room "{vars(resp)}"', nagios.UNKNOWN, leave_failures
        if (datetime.now() - timeout_start).total_seconds() >= args.timeout:
            leave = [await leave_room_async(new_test_room_id, sender_client)]
            leave_failures = []
            for event in leave:
                if not event[0]:
                    leave_failures.append((event[1], event[2]))
            return 'UNKNOWN: failed to join room, timeout.', nagios.UNKNOWN, leave_failures

    time.sleep(2)

    # Sender sends the msg to room
    send_msg_time = datetime.now()
    msg = {'id': str(uuid4()), 'ts': send_msg_time.microsecond}
    resp = (await sender_client.room_send(new_test_room_id, 'm.room.message', {'body': json.dumps(msg), 'msgtype': 'm.room.message'}))
    if isinstance(resp, RoomSendError):
        leave = [await leave_room_async(new_test_room_id, sender_client), await leave_room_async(new_test_room_id, receiver_client)]
        leave_failures = []
        for event in leave:
            if not event[0]:
                leave_failures.append((event[1], event[2]))
        return f'UNKNOWN: failed to send message "{resp}', nagios.UNKNOWN, leave_failures
    msg_event_id = resp.event_id

    # Sender watches for the message
    start_check = datetime.now()
    while True:
        resp = await receiver_client.room_get_event(new_test_room_id, msg_event_id)
        if isinstance(resp, RoomGetEventResponse):
            recv_msg_time = datetime.now()
            recv_msg = json.loads(resp.event.source['content']['body'])
            break
        if (datetime.now() - start_check).total_seconds() >= args.timeout:
            leave = [await leave_room_async(new_test_room_id, sender_client), await leave_room_async(new_test_room_id, receiver_client)]
            leave_failures = []
            for event in leave:
                if not event[0]:
                    leave_failures.append((event[1], event[2]))
            return "CRITICAL: timeout - receiver did not recieve the sender's message.", nagios.CRITICAL, leave_failures

    # Double check everything makes sense
    if not msg == recv_msg:
        leave = [await leave_room_async(new_test_room_id, sender_client), await leave_room_async(new_test_room_id, receiver_client)]
        leave_failures = []
        for event in leave:
            if not event[0]:
                leave_failures.append((event[1], event[2]))
        return "CRITICAL: sender's message did not match the receiver's.", nagios.CRITICAL, leave_failures

    # Calculate the time it took to recieve the message, including sync
    bot1_msg_delta = (recv_msg_time - send_msg_time).total_seconds()

    return bot1_msg_delta, nagios.OK, new_test_room_id


async def login(user_id, passwd, homeserver, config_file=None):
    client = AsyncClient(homeserver, user_id, config=AsyncClientConfig(request_timeout=args.timeout, max_timeout_retry_wait_time=10))
    if config_file:
        # If there are no previously-saved credentials, we'll use the password
        if not os.path.exists(config_file):
            resp = await client.login(passwd)

            # check that we logged in successfully
            if isinstance(resp, LoginResponse):
                write_details_to_disk(resp, homeserver, config_file)
            else:
                print(f'UNKNOWN: failed to log in "{resp}"')
                sys.exit(nagios.UNKNOWN)
        else:
            # Otherwise the config file exists, so we'll use the stored credentials
            with open(config_file, "r") as f:
                config = json.load(f)
                client = AsyncClient(config["homeserver"])
                client.access_token = config["access_token"]
                client.user_id = config["user_id"]
                client.device_id = config["device_id"]
    else:
        await client.login(passwd)
    return client


async def main() -> None:
    bot1 = await login(args.bot1_user, args.bot1_pw, args.bot1_hs, args.bot1_auth_file)
    bot2 = await login(args.bot2_user, args.bot2_pw, args.bot2_hs, args.bot2_auth_file)

    bot1_output_msg, bot1_output_code, bot1_new_room_id = await test_one_direction(bot1, bot2, args.bot2_user)
    bot2_output_msg, bot2_output_code, bot2_new_room_id = await test_one_direction(bot2, bot1, args.bot1_user)

    # Clean up
    leave = [await leave_room_async(bot1_new_room_id, bot1), await leave_room_async(bot2_new_room_id, bot1), await leave_room_async(bot1_new_room_id, bot2), await leave_room_async(bot2_new_room_id, bot2)]
    leave_failures = []
    for event in leave:
        if not event[0]:
            leave_failures.append((event[1], event[2]))

    bot1_leave_all_failures = await leave_all_rooms_async(bot1, exclude_starting_with='_PERM_')
    bot2_leave_all_failures = await leave_all_rooms_async(bot2, exclude_starting_with='_PERM_')
    await bot1.close()
    await bot2.close()

    nagios_output = nagios.OK
    prints = []

    if bot1_output_code != nagios.OK:
        prints.append(bot1_output_msg)
        nagios_output = bot1_output_code
    if bot2_output_code != nagios.OK:
        prints.append(bot2_output_msg)
        if nagios_output < bot2_output_code:
            # Only set the code if our code is more severe
            nagios_output = bot2_output_code

    # bot1 -> bot2
    if isinstance(bot1_output_msg, float):  # only do this if the func returned a value
        bot1_output_msg = round(bot1_output_msg, 2)
        if bot1_output_msg >= args.crit:
            if nagios_output < nagios.CRITICAL:
                nagios_output = nagios.CRITICAL
            prints.append(f'CRITICAL: {bot1_hs_domain} -> {bot2_hs_domain} is {bot1_output_msg} seconds.')
        elif bot1_output_msg >= args.warn:
            if nagios_output < nagios.WARNING:
                nagios_output = nagios.WARNING
            prints.append(f'WARNING: {bot1_hs_domain} -> {bot2_hs_domain} is {bot1_output_msg} seconds.')
        else:
            prints.append(f'OK: {bot1_hs_domain} -> {bot2_hs_domain} is {bot1_output_msg} seconds.')

    # bot2 -> bot1
    if isinstance(bot2_output_msg, float):
        bot2_output_msg = round(bot2_output_msg, 2)
        if bot2_output_msg >= args.crit:
            if nagios_output < nagios.CRITICAL:
                nagios_output = nagios.CRITICAL
            prints.append(f'CRITICAL: {bot1_hs_domain} <- {bot2_hs_domain} is {bot2_output_msg} seconds.')
        elif bot2_output_msg >= args.warn:
            if nagios_output < nagios.WARNING:
                nagios_output = nagios.WARNING
            prints.append(f'WARNING: {bot1_hs_domain} <- {bot2_hs_domain} is {bot2_output_msg} seconds.')
        else:
            prints.append(f'OK: {bot1_hs_domain} <- {bot2_hs_domain} is {bot2_output_msg} seconds.')

    if len(leave_failures):
        prints.append('=================================')
        prints.append('WARN: a bot failed to leave a room:')
        for err in leave_failures:
            prints.append(err)
        if nagios_output < nagios.WARNING:
            nagios_output = nagios.WARNING

    bot1_leave_warned = False
    for err in bot1_leave_all_failures:
        if not err[0]:
            if not bot1_leave_warned:
                prints.append('=================================')
                prints.append('WARN: bot1 failed to leave room:')
                bot1_leave_warned = True
            prints.append(err)
            if nagios_output < nagios.WARNING:
                nagios_output = nagios.WARNING

    bot2_leave_warned = False
    for err in bot2_leave_all_failures:
        if not err[0]:
            if not bot2_leave_warned:
                prints.append('=================================')
                prints.append('WARN: bot2 failed to leave room:')
                bot2_leave_warned = True
            prints.append(err)
            if nagios_output < nagios.WARNING:
                nagios_output = nagios.WARNING

    for x in prints:
        print(f'\n{x}', end=' ')
    print(f"|'{bot1_hs_domain}_outbound'={bot1_output_msg}s;;; '{bot1_hs_domain}_inbound'={bot2_output_msg}s;;;")

    sys.exit(nagios_output)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"UNKNOWN: exception\n{e}")
        print(traceback.format_exc())
        sys.exit(nagios.UNKNOWN)
