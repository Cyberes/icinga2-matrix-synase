import argparse

import checker.synapse_client as synapse_client
from checker.notify import build_msg

parser = argparse.ArgumentParser(description='')
parser.add_argument('--user', required=True, help='User ID for the bot.')
parser.add_argument('--pw', required=True, help='Password for the bot.')
parser.add_argument('--hs', required=True, help='Homeserver of the bot.')
parser.add_argument('--room', required=True, help='The room the bot should send its messages in.')
parser.add_argument('--auth-file', help="File to cache the bot's login details to.")

parser.add_argument('--longdatetime', required=True, help='$icinga.long_date_time$')
parser.add_argument('--servicename', required=True, help='$service.name$')
parser.add_argument('--servicedisplayname', required=True, help='$service.name$')
parser.add_argument('--hostname', required=True, help='$host.name$')
parser.add_argument('--hostdisplayname', required=True, help='$host.display_name$')
parser.add_argument('--serviceoutput', required=True, help='$service.output$')
parser.add_argument('--servicestate', required=True, help='$service.state$')
parser.add_argument('--notificationtype', required=True, help='$notification.type$')

parser.add_argument('--hostaddress', required=False, help='$address$')
parser.add_argument('--notificationauthor', required=False, help='$notification.author$')
parser.add_argument('--notificationcomment', required=False, help='$notification.comment$')
parser.add_argument('--icinga2weburl', required=False, help='$notification.icingaweb2url$')

args = parser.parse_args()

if __name__ == '__main__':
    msg = build_msg(args.hostname, args.hostdisplayname, args.servicestate, args.longdatetime, args.serviceoutput, args.servicename, args.servicedisplayname, args.hostaddress, args.notificationcomment, args.notificationauthor, args.icinga2weburl)
    print(msg)
    access_token, client = synapse_client.login(args.user, args.pw, args.hs, args.auth_file, args.room)
    synapse_client.send_msg(client, args.room, msg)
