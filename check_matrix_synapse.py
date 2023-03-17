#!/usr/bin/env python3
import argparse
import sys
import time
import traceback

import numpy as np
import requests

from checker import nagios
from checker.synapse_grafana import get_avg_python_gc_time, get_event_send_time, get_outgoing_http_request_rate, get_waiting_for_db

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--grafana-server', required=True, help='Grafana server.')
parser.add_argument('--synapse-server', required=True, help='Matrix Synapse server.')
parser.add_argument('--grafana-api-key', required=True)
parser.add_argument('--interval', default=15, type=int, help='Data interval in seconds.')
parser.add_argument('--range', default=2, type=int, help='Data range in minutes. Used for comparison and averaging.')
parser.add_argument('--type', required=True, choices=['gc-time', 'response-time', 'outgoing-http-rate', 'avg-send', 'db-lag'])
parser.add_argument('--warn', type=float, help='Manually set warn level.')
parser.add_argument('--crit', type=float, help='Manually set critical level.')
args = parser.parse_args()


# TODO: add warn suppoort

def main():
    if args.type == 'gc-time':
        # in seconds
        python_gc_time_sum_MAX = 0.002 if not args.crit else args.crit
        try:
            python_gc_time_sum = np.round(np.average(get_avg_python_gc_time(args.grafana_api_key, args.interval, args.range, args.grafana_server)), 5)
            if python_gc_time_sum >= python_gc_time_sum_MAX:
                print(f"CRITICAL: average GC time per collection is {python_gc_time_sum} sec. |'garbage-collection'={python_gc_time_sum}s;;;")
                sys.exit(nagios.CRITICAL)
            else:
                print(f"OK: average GC time per collection is {python_gc_time_sum} sec. |'garbage-collection'={python_gc_time_sum}s;;;")
                sys.exit(nagios.OK)
        except Exception as e:
            print(f'UNKNOWN: failed to check avg. GC time "{e}"')
            print(traceback.format_exc())
            sys.exit(nagios.UNKNOWN)
    elif args.type == 'response-time':
        response_time_MAX = 1 if not args.crit else args.crit
        timeout = 10
        try:
            response_times = []
            for i in range(10):
                start = time.perf_counter()
                try:
                    response = requests.post(args.synapse_server, timeout=timeout, verify=False)
                except Exception as e:
                    print(f'UNKNOWN: failed to ping endpoint "{e}"')
                    print(traceback.format_exc())
                    sys.exit(nagios.UNKNOWN)
                request_time = time.perf_counter() - start
                response_times.append(np.round(request_time, 2))
                time.sleep(1)
            response_time = np.round(np.average(response_times), 2)
            if response_time > response_time_MAX:
                print(f"CRITICAL: response time is {response_time} sec. |'response-time'={response_time}s;;;")
                sys.exit(nagios.CRITICAL)
            else:
                print(f"OK: response time is {response_time} sec. |'response-time'={response_time}s;;;")
                sys.exit(nagios.OK)
        except Exception as e:
            print(f'UNKNOWN: failed to check response time "{e}"')
            print(traceback.format_exc())
            sys.exit(nagios.UNKNOWN)
    elif args.type == 'outgoing-http-rate':
        # outgoing req/sec
        outgoing_http_request_rate_MAX = 10 if not args.crit else args.crit
        try:
            outgoing_http_request_rate = get_outgoing_http_request_rate(args.grafana_api_key, args.interval, args.range, args.grafana_server)
            failed = {}
            perf_data = '|'
            for k, v in outgoing_http_request_rate.items():
                perf_data = perf_data + f"'{k}'={v}s;;; "
                if v > outgoing_http_request_rate_MAX:
                    failed[k] = v

            if len(failed.keys()) > 0:
                print(f'CRITICAL: outgoing HTTP request rate for {failed} req/sec.', perf_data)
                sys.exit(nagios.CRITICAL)
            print(f'OK: outgoing HTTP request rate is {outgoing_http_request_rate} req/sec.', perf_data)
            sys.exit(nagios.OK)
        except Exception as e:
            print(f'UNKNOWN: failed to check outgoing HTTP request rate "{e}"')
            print(traceback.format_exc())
            sys.exit(nagios.UNKNOWN)
    elif args.type == 'avg-send':
        # Average send time in seconds
        event_send_time_MAX = 1 if not args.crit else args.crit
        try:
            event_send_time = get_event_send_time(args.grafana_api_key, args.interval, args.range, args.grafana_server)
            if event_send_time > event_send_time_MAX:
                print(f"CRITICAL: average message send time is {event_send_time} sec. |'avg-send-time'={event_send_time}s;;;")
                sys.exit(nagios.CRITICAL)
            else:
                print(f"OK: average message send time is {event_send_time} sec. |'avg-send-time'={event_send_time}s;;;")
                sys.exit(nagios.OK)
        except Exception as e:
            print(f'UNKNOWN: failed to check average message send time "{e}"')
            print(traceback.format_exc())
            sys.exit(nagios.UNKNOWN)
    elif args.type == 'db-lag':
        # in seconds
        db_lag_MAX = 0.01 if not args.crit else args.crit
        try:
            db_lag = get_waiting_for_db(args.grafana_api_key, args.interval, args.range, args.grafana_server)
            if db_lag > db_lag_MAX:
                print(f"CRITICAL: DB lag is {db_lag} sec. |'db-lag'={db_lag}s;;;")
                sys.exit(nagios.CRITICAL)
            else:
                print(f"OK: DB lag is {db_lag} sec. |'db-lag'={db_lag}s;;;")
                sys.exit(nagios.OK)
        except Exception as e:
            print(f'UNKNOWN: failed to check DB lag "{e}"')
            print(traceback.format_exc())
            sys.exit(nagios.UNKNOWN)
    else:
        print('Wrong type')
        sys.exit(nagios.UNKNOWN)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f'UNKNOWN: exception "{e}"')
        print(traceback.format_exc())
        sys.exit(nagios.UNKNOWN)
