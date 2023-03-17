#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import sys
import tempfile
import traceback
import urllib

import numpy as np
import requests
from PIL import Image
from nio import AsyncClient, AsyncClientConfig, LoginResponse, RoomSendError
from urllib3.exceptions import InsecureRequestWarning

from checker import nagios
from checker.synapse_client import send_image, write_login_details_to_disk

parser = argparse.ArgumentParser(description='')
parser.add_argument('--user', required=True, help='User ID for the bot.')
parser.add_argument('--pw', required=True, help='Password for the bot.')
parser.add_argument('--hs', required=True, help='Homeserver of the bot.')
parser.add_argument('--admin-endpoint', required=True, help='Admin endpoint that will be called to purge media for this user.')
parser.add_argument('--room', required=True, help='The room the bot should send its test messages in.')
parser.add_argument('--check-domain', required=True, help='The domain that should be present.')
parser.add_argument('--media-cdn-redirect', default='true', help='If set, the server must respond with a redirect to the media CDN domain.')
parser.add_argument('--required-headers', nargs='*', help="If these headers aren't set to the correct value, critical. Use the format 'key=value")
parser.add_argument('--auth-file', help="File to cache the bot's login details to.")
parser.add_argument('--timeout', type=float, default=90, help='Request timeout limit.')
parser.add_argument('--warn', type=float, default=2.0, help='Manually set warn level.')
parser.add_argument('--crit', type=float, default=2.5, help='Manually set critical level.')
args = parser.parse_args()

if args.media_cdn_redirect == 'true':
    args.media_cdn_redirect = True
elif args.media_cdn_redirect == 'false':
    args.media_cdn_redirect = False
else:
    print('UNKNOWN: could not parse the value for --media-cdn-redirect')
    sys.exit(nagios.UNKNOWN)


def verify_media_header(header: str, header_dict: dict, good_value: str = None, warn_value: str = None, critical_value: str = None):
    """
    If you don't specify good_value, warn_value, or critical_value then the header will only be checked for existience.
    """

    # Convert everything to lowercase strings to prevent any wierdness
    header_dict = {k.lower(): v for k, v in header_dict.items()}
    header = header.lower()
    header_value = str(header_dict.get(header))
    warn_value = str(warn_value)
    critical_value = str(critical_value)
    if not header_value:
        return f'CRITICAL: missing header\n"{header}"', nagios.CRITICAL

    if good_value:
        good_value = str(good_value)
        if header_value == good_value:
            return f'OK: {header}: "{header_value}"', nagios.OK
        else:
            return f'CRITICAL: {header} is not "{good_value}", is "{header_value}"', nagios.CRITICAL
    # elif warn_value and header_value == warn_value:
    #     return f'WARN: {header}: "{header_value}"', nagios.WARNING
    # elif critical_value and header_value == critical_value:
    #     return f'CRITICAL: {header}: "{header_value}"', nagios.CRITICAL
    return f'OK: {header} is present', nagios.OK  # with value "{header_value}"'


async def main() -> None:
    exit_code = nagios.OK

    async def cleanup(client, test_image_path, image_event_id=None):
        nonlocal exit_code
        # Clean up
        if image_event_id:
            await client.room_redact(args.room, image_event_id)
        os.remove(test_image_path)
        await client.close()

        requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
        try:
            r = requests.delete(f'{args.admin_endpoint}/_synapse/admin/v1/users/{args.user}/media', headers={'Authorization': f'Bearer {client.access_token}'}, verify=False)
            if r.status_code != 200:
                if nagios.WARNING < exit_code:
                    exit_code = nagios.WARNING
                return f"WARN: failed to purge media for this user.\n{r.text}"
            else:
                return None
        except Exception as e:
            if nagios.WARNING < exit_code:
                exit_code = nagios.WARNING
            return f"WARN: failed to purge media for this user.\n{e}"

    client = AsyncClient(args.hs, args.user, config=AsyncClientConfig(request_timeout=args.timeout, max_timeout_retry_wait_time=10))
    if args.auth_file:
        # If there are no previously-saved credentials, we'll use the password
        if not os.path.exists(args.auth_file):
            resp = await client.login(args.pw)

            # check that we logged in successfully
            if isinstance(resp, LoginResponse):
                write_login_details_to_disk(resp, args.hs, args.auth_file)
            else:
                print(f'CRITICAL: failed to log in.\n{resp}')
                sys.exit(nagios.CRITICAL)
        else:
            # Otherwise the config file exists, so we'll use the stored credentials
            with open(args.auth_file, "r") as f:
                config = json.load(f)
                client = AsyncClient(config["homeserver"])
                client.access_token = config["access_token"]
                client.user_id = config["user_id"]
                client.device_id = config["device_id"]
    else:
        await client.login(args.pw)

    await client.join(args.room)

    # Create a random image
    imarray = np.random.rand(100, 100, 3) * 255
    im = Image.fromarray(imarray.astype('uint8')).convert('RGBA')
    _, test_image_path = tempfile.mkstemp()
    test_image_path = test_image_path + '.png'
    im.save(test_image_path)

    # Send the image and get the event ID
    image_event_id = (await send_image(client, args.room, test_image_path))
    if isinstance(image_event_id, RoomSendError):
        await cleanup(client, test_image_path)
        print(f'CRITICAL: failed to send message.\n{image_event_id}')
        sys.exit(nagios.CRITICAL)
    image_event_id = image_event_id.event_id

    # Get the event
    image_event = (await client.room_get_event(args.room, image_event_id)).event

    # convert mxc:// to http://
    target_file_url = await client.mxc_to_http(image_event.url)

    # Check the headers. Ignore the non-async thing here, it doesn't
    # matter in this situation.
    r = requests.head(target_file_url, allow_redirects=False)

    prints = []

    if r.status_code != 200 and not args.media_cdn_redirect:
        await cleanup(client, test_image_path, image_event_id=image_event_id)
        prints.append(f'CRITICAL: status code is "{r.status_code}"')
        sys.exit(nagios.CRITICAL)
    else:
        prints.append(f'OK: status code is "{r.status_code}"')

    headers = dict(r.headers)

    # Check domain
    if args.media_cdn_redirect:
        if 'location' in headers:
            domain = urllib.parse.urlparse(headers['location']).netloc
            if domain != args.check_domain:
                exit_code = nagios.CRITICAL
                prints.append(f'CRITICAL: redirect to media CDN domain is "{domain}"')
            else:
                prints.append(f'OK: media CDN domain is "{domain}"')
        else:
            exit_code = nagios.CRITICAL
            prints.append(f'CRITICAL: was not redirected to the media CDN domain.')

        # Make sure we aren't redirected if we're a Synapse server
        test = requests.head(target_file_url, headers={'User-Agent': 'Synapse/1.77.3'}, allow_redirects=False)
        if test.status_code != 200:
            prints.append('CRITICAL: Synapse user-agent is redirected with status code', test.status_code)
            exit_code = nagios.CRITICAL
        else:
            prints.append(f'OK: Synapse user-agent is not redirected.')
    else:
        if 'location' in headers:
            exit_code = nagios.CRITICAL
            prints.append(f"CRITICAL: recieved 301 to {urllib.parse.urlparse(headers['location']).netloc}")
        else:
            prints.append(f'OK: was not redirected.')

    if args.required_headers:
        # Icinga may pass the values as one string
        if len(args.required_headers) == 1:
            args.required_headers = args.required_headers[0].split(' ')
        for item in args.required_headers:
            key, value = item.split('=')
            header_chk, code = verify_media_header(key, headers, good_value=value)
            prints.append(header_chk)
            if code > exit_code:
                exit_code = code

    # results = [verify_media_header('synapse-media-local-status', headers), verify_media_header('synapse-media-s3-status', headers, good_value='200'), verify_media_header('synapse-media-server', headers, good_value='s3')]
    # for header_chk, code in results:
    #     prints.append(header_chk)
    #     if code > exit_code:
    #         exit_code = code

    clean_msg = await cleanup(client, test_image_path, image_event_id=image_event_id)

    if exit_code == nagios.OK:
        print('OK: media CDN is good.')
    elif exit_code == nagios.UNKNOWN:
        print('UNKNOWN: media CDN is bad.')
    elif exit_code == nagios.WARNING:
        print('WARNING: media CDN is bad.')
    elif exit_code == nagios.CRITICAL:
        print('CRITICAL: media CDN is bad.')
    for msg in prints:
        print(msg)

    if clean_msg:
        print(clean_msg)

    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f'UNKNOWN: exception\n{e}')
        print(traceback.format_exc())
        sys.exit(nagios.UNKNOWN)
