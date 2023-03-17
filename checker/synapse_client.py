import asyncio
import copy
import json
import os
import sys
import time

import aiofiles.os
import magic
import markdown
from PIL import Image
from nio import AsyncClient, LoginResponse, MatrixRoom, RoomForgetResponse, RoomLeaveResponse, RoomSendError, UploadResponse

from . import nagios


def handle_err(func):
    def wrapper(*args, **kwargs):
        try:
            crit, ret = func(*args, **kwargs)
        except Exception as e:
            print(f"UNKNOWN: exception '{e}'")
            sys.exit(nagios.UNKNOWN)
        if crit:
            print(f"CRITICAL: {crit}")
            sys.exit(nagios.CRITICAL)
        else:
            return ret

    return wrapper


def write_login_details_to_disk(resp: LoginResponse, homeserver, config_file) -> None:
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


async def send_image(client, room_id, image):
    """Send image to room.
    Arguments:
    ---------
    client : Client
    room_id : str
    image : str, file name of image
    This is a working example for a JPG image.
        "content": {
            "body": "someimage.jpg",
            "info": {
                "size": 5420,
                "mimetype": "image/jpeg",
                "thumbnail_info": {
                    "w": 100,
                    "h": 100,
                    "mimetype": "image/jpeg",
                    "size": 2106
                },
                "w": 100,
                "h": 100,
                "thumbnail_url": "mxc://example.com/SomeStrangeThumbnailUriKey"
            },
            "msgtype": "m.image",
            "url": "mxc://example.com/SomeStrangeUriKey"
        }
    """
    mime_type = magic.from_file(image, mime=True)  # e.g. "image/jpeg"
    if not mime_type.startswith("image/"):
        print(f'UNKNOWN: wrong mime type "{mime_type}"')
        sys.exit(nagios.UNKNOWN)

    im = Image.open(image)
    (width, height) = im.size  # im.size returns (width,height) tuple

    # first do an upload of image, then send URI of upload to room
    file_stat = await aiofiles.os.stat(image)
    async with aiofiles.open(image, "r+b") as f:
        resp, maybe_keys = await client.upload(f, content_type=mime_type,  # image/jpeg
                                               filename=os.path.basename(image), filesize=file_stat.st_size, )
    if not isinstance(resp, UploadResponse):
        print(f'UNKNOWN: failed to upload image "{vars(resp)}"')
        sys.exit(nagios.UNKNOWN)

    content = {"body": os.path.basename(image),  # descriptive title
               "info": {"size": file_stat.st_size, "mimetype": mime_type, "thumbnail_info": None,  # TODO
                        "w": width,  # width in pixel
                        "h": height,  # height in pixel
                        "thumbnail_url": None,  # TODO
                        }, "msgtype": "m.image", "url": resp.content_uri, }

    try:
        return await client.room_send(room_id, message_type="m.room.message", content=content)
    except Exception as e:
        print(f"Image send of file {image} failed.")
        print(f'UNKNOWN: failed to send image event "{e}"')
        sys.exit(nagios.UNKNOWN)


def send_msg(client, room, msg):
    async def inner(client, room, msg):
        r = await client.room_send(room_id=room, message_type="m.room.message", content={"msgtype": "m.text", "body": msg, "format": "org.matrix.custom.html", "formatted_body": markdown.markdown(msg), }, )
        if isinstance(r, RoomSendError):
            print(r)
        await client.close()

    return asyncio.run(inner(client, room, msg))


def login(user, pw, hs, auth_file, room):
    async def inner(user, pw, hs, auth_file, room):
        client = AsyncClient(hs, user)
        if auth_file:
            # If there are no previously-saved credentials, we'll use the password
            if not os.path.exists(auth_file):
                resp = await client.login(pw)
                # check that we logged in successfully
                if isinstance(resp, LoginResponse):
                    write_login_details_to_disk(resp, hs, auth_file)
                else:
                    print(f'Failed to log in "{resp}"')
            else:
                # Otherwise the config file exists, so we'll use the stored credentials
                with open(auth_file, "r") as f:
                    config = json.load(f)
                    client = AsyncClient(config["homeserver"])
                    client.access_token = config["access_token"]
                    client.user_id = config["user_id"]
                    client.device_id = config["device_id"]
        else:
            await client.login(pw)

        await client.join(room)
        x = client.access_token
        await client.close()
        return x, client

    return asyncio.run(inner(user, pw, hs, auth_file, room))


async def leave_room_async(room_id, client):
    l = await client.room_leave(room_id)
    time.sleep(1)
    f = await client.room_forget(room_id)
    return isinstance(l, RoomLeaveResponse) and isinstance(f, RoomForgetResponse), l, f


async def leave_all_rooms_async(client, exclude_starting_with=None):
    results = []
    for room_id in (await client.joined_rooms()).rooms:
        room = MatrixRoom(room_id, client.user_id)
        # if exclude_starting_with and room.named_room_name() is not None and room.named_room_name().startswith(exclude_starting_with):
        #     continue
        s, l, f = await leave_room_async(room_id, client)
        results.append((s, l, f))
        time.sleep(1)
    await client.sync()
    invited_rooms = copy.copy(client.invited_rooms)  # RuntimeError: dictionary changed size during iteration
    for name, room in invited_rooms.items():
        # if exclude_starting_with and room.named_room_name() is not None and room.named_room_name().startswith(exclude_starting_with):
        #     continue
        s, l, f = await leave_room_async(room.room_id, client)
        results.append((s, l, f))
        time.sleep(1)
    await client.close()
    return results


def leave_all_rooms(client, exclude_starting_with=None):
    return asyncio.run(leave_all_rooms_async(client, exclude_starting_with))
