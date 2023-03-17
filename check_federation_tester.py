#!/usr/bin/env python3
import argparse
import sys
import traceback

import requests

import checker.nagios as nagios

parser = argparse.ArgumentParser(description='Test federation between two homeservers.')
parser.add_argument('--endpoint', required=True, help='Endpoint to parse. See fed.mau.dev or federationtester.matrix.org')
parser.add_argument('--timeout', type=float, default=90, help='Request timeout limit.')
parser.add_argument('--warn', type=float, default=2.0, help='Manually set warn level.')
parser.add_argument('--crit', type=float, default=2.5, help='Manually set critical level.')
args = parser.parse_args()


def main() -> None:
    r = requests.get(args.endpoint, timeout=args.timeout)
    if not r.status_code:
        print(f'UNKNOWN: tester endpoint failed with status code {r.status_code}\n', r.text)
        sys.exit(nagios.UNKNOWN)

    r_json = r.json()
    if r_json.get('FederationOK'):
        print('OK: federation tester reported success.')
        print(f"Version: {r_json.get('Version', {}).get('name')}/{r_json.get('Version', {}).get('version')}")
        print('WellKnown:', r_json.get('WellKnownResult', {}).get('m.server'))
        nagios_output = nagios.OK
    else:
        print('CRITICAL: federation tester reported failure.')
        print('Server Version:', r_json.get('m.server'))
        print('WellKnown:', r_json.get('WellKnownResult', {}).get('m.server'))
        print('WellKnown Result:', r_json.get('WellKnownResult', {}).get('result'))
        print('DNS Result:', r_json.get('DNSResult', {}).get('SRVError', {}).get('Message', {}))
        print('Version:', r_json.get('Version', {}).get('error'))
        print('Connection Report:', r_json.get('ConnectionReports'))
        print('Connection Errors:', r_json.get('ConnectionErrors'))
        nagios_output = nagios.CRITICAL

    sys.exit(nagios_output)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"UNKNOWN: exception\n{e}")
        print(traceback.format_exc())
        sys.exit(nagios.UNKNOWN)
