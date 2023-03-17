#!/usr/bin/env python3
import argparse
import sys

import requests

from checker import nagios

parser = argparse.ArgumentParser(description='')
parser.add_argument('--metrics-endpoint', required=True, help='Target URL to scrape.')
parser.add_argument('--domain', required=True, help='Our domain.')
parser.add_argument('--ignore', nargs='*', default=[], help='Ignore these hosts.')
parser.add_argument('--timeout', type=float, default=90, help='Request timeout limit.')
parser.add_argument('--warn', type=float, default=20, help='Manually set warn level for response time in seconds.')
parser.add_argument('--crit', type=float, default=30, help='Manually set critical levelfor response time in seconds.')
parser.add_argument('--warn-percent', type=int, default=30, help='Manually set warn level for the percentage of hosts that must fail the checks.')
parser.add_argument('--crit-percent', type=int, default=50, help='Manually set crit level for the percentage of hosts that must fail the checks.')
args = parser.parse_args()


def make_percent(num: float):
    return int(num * 100)


def main():
    from bs4 import BeautifulSoup
    import re

    # Split the values since icinga will quote the args
    if len(args.ignore) == 1:
        args.ignore = args.ignore[0].strip(' ').split(' ')

    def get_sec(time_str):
        """Get seconds from time."""
        h, m, s = time_str.split(':')
        return int(h) * 3600 + int(m) * 60 + int(s)

    def ms_to_s(s):
        min_m = re.match(r'^(\d+)m([\d.]+)s', s)
        if min_m:
            return get_sec(f'0:{min_m.group(1)}:{int(float(min_m.group(2)))}')
        elif s.endswith('ms'):
            return float('0.' + s.strip('ms'))
        elif s.endswith('s'):
            return float(s.strip('ms'))

    r = requests.get(args.metrics_endpoint)
    if r.status_code != 200:
        sys.exit(nagios.UNKNOWN)
    soup = BeautifulSoup(r.text, 'html.parser')
    tooltips = soup.find_all('span', {'class', 'tooltip'})
    data = {}
    for item in tooltips:
        m = re.match(r'<span class="tooltip">\s*Send: (.*?)\s*<br\/>\s*Receive: (.*?)\s*<\/span>', str(item))
        if m:
            domain = item.parent.parent.find('span', {'class': 'domain'}).text
            s = ms_to_s(m.group(1))
            r = ms_to_s(m.group(2))
            data[domain] = {
                'send': (s if s else -1),
                'receive': (r if r else -1),
            }
    exit_code = nagios.OK
    info_str = []
    data_str = []
    warn_failed_hosts = []
    crit_failed_hosts = []

    if len(data.keys()) == 0:
        print('UNKNOWN: failed to find any servers.')
        sys.exit(nagios.UNKNOWN)

    for domain, values in data.items():
        if domain not in args.ignore:
            if 'send' in values.keys():
                if values['send'] >= args.crit:
                    info_str.append(f'CRITICAL: {domain} send is {values["send"]}s.')
                    crit_failed_hosts.append(domain)
                elif values['send'] >= args.warn:
                    info_str.append(f'WARN: {domain} send is {values["send"]}s.')
                    warn_failed_hosts.append(domain)
            else:
                info_str.append(f'UNKNOWN: {domain} send is empty.')

            if 'receive' in values.keys():
                if values['receive'] >= args.crit:
                    info_str.append(f'CRITICAL: {domain} receive is {values["receive"]}s.')
                    crit_failed_hosts.append(domain)
                elif values['receive'] >= args.warn:
                    info_str.append(f'WARN: {domain} receive is {values["receive"]}s.')
                    warn_failed_hosts.append(domain)
            else:
                info_str.append(f'UNKNOWN: {domain} receive is empty.')

        if 'send' in values.keys() and 'receive' in values.keys():
            data_str.append(
                f"'{domain}-send'={values['send']}s;;; '{domain}-receive'={values['receive']}s;;;"
            )

    if not len(crit_failed_hosts) and not len(warn_failed_hosts):
        print(f'OK: ping time is good.', end=' ')
    else:
        if len(crit_failed_hosts) / len(data.keys()) >= (args.crit_percent / 100):
            # CRIT takes precedence
            exit_code = nagios.CRITICAL
            print(f'CRITICAL: {make_percent(len(crit_failed_hosts) / len(data.keys()))}% of hosts are marked as critical.')
        elif len(warn_failed_hosts) / len(data.keys()) >= (args.warn_percent / 100):
            exit_code = nagios.WARNING
            print(f'WARN: {make_percent(len(warn_failed_hosts) / len(data.keys()))}% of hosts are marked as warn.')

        if exit_code != nagios.OK:
            for x in info_str:
                print(x, end=('\n' if info_str.index(x) + 1 < len(info_str) else ''))
        else:
            print('OK: ping is good')
            print(f'Warn hosts: {", ".join(warn_failed_hosts) if len(warn_failed_hosts) else "none"}')
            print(f'Critical hosts: {", ".join(crit_failed_hosts) if len(crit_failed_hosts) else "none"}')
    print(f'|{" ".join(data_str)}')

    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f'UNKNOWN: exception "{e}"')
        import traceback

        print(traceback.format_exc())
        sys.exit(nagios.UNKNOWN)
