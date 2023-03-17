import json
import os
import sys
from pathlib import Path

import urllib3
from flask import Flask, Response, request
from icinga2api.client import Client

from checker import nagios

endpoint = 'https://localhost:8080'  # Icinga2 URL for the API. Defaults to "https://localhost:8080"
icinga2_user = 'icingaweb2'  # API username. Defaults to "icingaweb2"
icinga2_pw = ''  # API password or set ICINGA2KUMA_ICINGA2_PW

if (icinga2_pw == '' or not icinga2_pw) and os.environ.get('ICINGA2KUMA_ICINGA2_PW'):
    icinga2_pw = os.environ.get('ICINGA2KUMA_ICINGA2_PW')
else:
    print('Must specify icinga2 API password.')
    sys.exit(1)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

client = Client(endpoint, icinga2_user, icinga2_pw)

app = Flask(__name__)


@app.route('/host')
@app.route('/host/')
@app.route("/host/<hostid>")
def get_host_state(hostid=None):
    path = Path(request.base_url)
    args_service = request.args.getlist('service')
    args_exclude_service = request.args.getlist('exclude')  # do not list these services
    args_ignore_service = request.args.getlist('ignore')  # do not trigger a fail if these services fail
    kuma_mode = True if request.args.get('kuma') == 'true' else False

    if not hostid:
        return Response(json.dumps({'error': 'must specify host'}), status=406, mimetype='application/json')

    result = {
        'host': {},
        'services': {},
        'failed_services': [],
        'excluded_services': [],
        'ignored_services': [],
    }

    host_status = client.objects.list('Host', filters='match(hpattern, host.name)', filter_vars={'hpattern': hostid})
    if not len(host_status):
        return Response(json.dumps({'error': 'could not find host'}), status=404, mimetype='application/json')
    else:
        host_status = host_status[0]

    result['host'] = {
        'name': host_status['name'],
        'state': 0 if (host_status['attrs']['acknowledgement'] or host_status['attrs']['acknowledgement_expiry']) else host_status['attrs']['state'],
        'actual_state': host_status['attrs']['state'],
        'attrs': {
            **host_status['attrs']
        }
    }

    services_status = client.objects.list('Service', filters='match(hpattern, host.name)', filter_vars={'hpattern': hostid})
    for attrs in services_status:
        name = attrs['name'].split('!')[1]
        if name in args_exclude_service:
            result['excluded_services'].append(name)
        else:
            result['services'][name] = {
                'state': 0 if (attrs['attrs']['acknowledgement'] or attrs['attrs']['acknowledgement_expiry']) else attrs['attrs']['state'],
                'actual_state': attrs['attrs']['state'],
                'attrs': {
                    **attrs
                }
            }

    if len(args_service):
        services = {}
        for service in args_service:
            if service in result['services'].keys():
                services[service] = result['services'][service]
            else:
                return Response(json.dumps({'error': 'service not found', 'service': service}), status=400, mimetype='application/json')
        result['services'] = services

    # if kuma_mode:
    for name, service in result['services'].items():
        if service['state'] != nagios.OK and name not in args_ignore_service:
            result['failed_services'].append({'name': name, 'state': service['state']})
    if result['host']['state'] != nagios.OK:
        result['failed_services'].append({'name': hostid, 'state': result['host']['state']})

    if kuma_mode and len(result['failed_services']):
        return Response(json.dumps(result), status=410, mimetype='application/json')
    else:
        return result
