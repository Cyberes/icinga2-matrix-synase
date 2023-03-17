import json

import numpy as np
import requests
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


def get_avg_python_gc_time(api_key, interval, data_range, endpoint):
    json_data = {
        'queries': [
            {
                'datasource': {
                    'type': 'prometheus',
                    'uid': 'AbuT5CJ4z',
                },
                'expr': 'rate(python_gc_time_sum{instance="10.0.0.34:9000",job=~"(federation-receiver|federation-sender|initialsync|synapse|synchrotron)",index=~".*"}[30s])/rate(python_gc_time_count[30s])',
                'format': 'time_series',
                'intervalFactor': 2,
                'refId': 'A',
                'step': 20,
                'target': '',
                'interval': '',
                # 'key': 'Q-7edaea76-89bd-4b29-8412-a68bf4646712-0',
                'queryType': 'timeSeriesQuery',
                'exemplar': False,
                # 'requestId': 'Q-7edaea76-89bd-4b29-8412-a68bf4646712-0A',
                'utcOffsetSec': -25200,
                'legendFormat': '',
                'datasourceId': 1,
                'intervalMs': interval * 1000,
                # 'maxDataPoints': 1383,
            },
        ],
        'from': f'now-{data_range}m',
        'to': 'now',
    }
    response = requests.post(f'{endpoint}/api/ds/query', headers={'Authorization': f'Bearer {api_key}'}, json=json_data, verify=False).json()
    good = []
    for i in response['results']['A']['frames']:
        # This one can sometimes be null
        new = []
        for x in range(len(i['data']['values'][1])):
            if i['data']['values'][1][x] is not None:
                new.append(i['data']['values'][1][x])
        good.append(new)
    # Remove empty arrays
    results = []
    for x in good:
        if len(x) > 0:
            results.append(x)
    return [np.round(np.average(i), 5) for i in results]


def get_outgoing_http_request_rate(api_key, interval, data_range, endpoint):
    json_data = {
        'queries': [
            {
                'datasource': {
                    'type': 'prometheus',
                    'uid': 'AbuT5CJ4z',
                },
                'editorMode': 'code',
                'expr': 'rate(synapse_http_client_requests_total{job=~"(federation-receiver|federation-sender|initialsync|synapse|synchrotron)",index=~".*",instance="10.0.0.34:9000"}[2m])',
                'range': True,
                'refId': 'A',
                'interval': '',
                # 'key': 'Q-8b3dabd7-358e-45ed-a9ba-7be3f5fcf274-0',
                'queryType': 'timeSeriesQuery',
                'exemplar': False,
                # 'requestId': 'Q-8b3dabd7-358e-45ed-a9ba-7be3f5fcf274-0Q-c5c08c6b-7591-424c-8eac-53837fa51e89-1A',
                'utcOffsetSec': -25200,
                'legendFormat': '',
                'datasourceId': 1,
                'intervalMs': interval * 1000,
                # 'maxDataPoints': 10,
            },
            {
                'datasource': {
                    'type': 'prometheus',
                    'uid': 'AbuT5CJ4z',
                },
                'editorMode': 'code',
                'expr': 'rate(synapse_http_matrixfederationclient_requests_total{job=~"(federation-receiver|federation-sender|initialsync|synapse|synchrotron)",index=~".*",instance="10.0.0.34:9000"}[2m])',
                'range': True,
                'refId': 'B',
                'interval': '',
                # 'key': 'Q-c5c08c6b-7591-424c-8eac-53837fa51e89-1',
                'queryType': 'timeSeriesQuery',
                'exemplar': False,
                # 'requestId': 'Q-8b3dabd7-358e-45ed-a9ba-7be3f5fcf274-0Q-c5c08c6b-7591-424c-8eac-53837fa51e89-1B',
                'utcOffsetSec': -25200,
                'legendFormat': '',
                'datasourceId': 1,
                'intervalMs': interval * 1000,
                # 'maxDataPoints': 10,
            },
        ],
        'from': f'now-{data_range}m',
        'to': 'now',
    }
    response = requests.post(f'{endpoint}/api/ds/query', headers={'Authorization': f'Bearer {api_key}'}, json=json_data, verify=False).json()
    output = {}
    for letter, result in response['results'].items():
        name = result['frames'][0]['schema']['name'].split('=')[-1].strip('}').strip('"')
        output[name] = np.round(np.average(result['frames'][0]['data']['values'][1]), 2)
    return output
    # return {
    #     'GET': np.round(np.average(response['results']['A']['frames'][0]['data']['values'][1]), 2),
    #     'POST': np.round(np.average(response['results']['A']['frames'][1]['data']['values'][1]), 2),
    #     'PUT': np.round(np.average(response['results']['A']['frames'][2]['data']['values'][1]), 2),
    #     'fedr_GET': np.round(np.average(response['results']['B']['frames'][0]['data']['values'][1]), 2)
    # }


def get_event_send_time(api_key, interval, data_range, endpoint):
    json_data = {
        'queries': [
            {
                'datasource': {
                    'type': 'prometheus',
                    'uid': 'AbuT5CJ4z',
                },
                'expr': 'histogram_quantile(0.99, sum(rate(synapse_http_server_response_time_seconds_bucket{servlet=\'RoomSendEventRestServlet\',index=~".*",instance="10.0.0.34:9000",code=~"2.."}[2m])) by (le))',
                'format': 'time_series',
                'intervalFactor': 1,
                'refId': 'D',
                'interval': '',
                # 'key': 'Q-d8eb3572-9aea-4a73-92f2-e08b33c21ecb-0',
                'editorMode': 'builder',
                'range': True,
                'instant': True,
                'queryType': 'timeSeriesQuery',
                'exemplar': False,
                # 'requestId': 'Q-d8eb3572-9aea-4a73-92f2-e08b33c21ecb-0Q-a9222e59-18ff-4b3b-80ae-27bea8f149a9-1Q-0378a458-1ade-410e-a4b3-ae4aaa91d709-2Q-da4c00b6-61c1-49f5-8a0a-9f19990acfb7-3Q-21254889-3cf6-4d97-8dc5-ddf68360847e-4Q-502b8ed5-4050-461c-befc-76f6796dce68-5Q-364dc896-c399-4e58-8930-cba2e3d1d579-6Q-9072e904-da8d-4b00-b454-dac45b7c38f0-7D',
                'utcOffsetSec': -25200,
                'legendFormat': '',
                'datasourceId': 1,
                'intervalMs': interval * 1000,
                # 'maxDataPoints': 1383,
            },
            {
                'datasource': {
                    'type': 'prometheus',
                    'uid': 'AbuT5CJ4z',
                },
                'expr': 'histogram_quantile(0.9, sum(rate(synapse_http_server_response_time_seconds_bucket{servlet=\'RoomSendEventRestServlet\',index=~".*",instance="10.0.0.34:9000",code=~"2.."}[2m])) by (le))',
                'format': 'time_series',
                'interval': '',
                'intervalFactor': 1,
                'refId': 'A',
                # 'key': 'Q-a9222e59-18ff-4b3b-80ae-27bea8f149a9-1',
                'queryType': 'timeSeriesQuery',
                'exemplar': False,
                # 'requestId': 'Q-d8eb3572-9aea-4a73-92f2-e08b33c21ecb-0Q-a9222e59-18ff-4b3b-80ae-27bea8f149a9-1Q-0378a458-1ade-410e-a4b3-ae4aaa91d709-2Q-da4c00b6-61c1-49f5-8a0a-9f19990acfb7-3Q-21254889-3cf6-4d97-8dc5-ddf68360847e-4Q-502b8ed5-4050-461c-befc-76f6796dce68-5Q-364dc896-c399-4e58-8930-cba2e3d1d579-6Q-9072e904-da8d-4b00-b454-dac45b7c38f0-7A',
                'utcOffsetSec': -25200,
                'legendFormat': '',
                'datasourceId': 1,
                'intervalMs': interval * 1000,
                # 'maxDataPoints': 1383,
            },
            {
                'datasource': {
                    'type': 'prometheus',
                    'uid': 'AbuT5CJ4z',
                },
                'expr': 'histogram_quantile(0.75, sum(rate(synapse_http_server_response_time_seconds_bucket{servlet=\'RoomSendEventRestServlet\',index=~".*",instance="10.0.0.34:9000",code=~"2.."}[2m])) by (le))',
                'format': 'time_series',
                'intervalFactor': 1,
                'refId': 'C',
                'interval': '',
                # 'key': 'Q-0378a458-1ade-410e-a4b3-ae4aaa91d709-2',
                'queryType': 'timeSeriesQuery',
                'exemplar': False,
                # 'requestId': 'Q-d8eb3572-9aea-4a73-92f2-e08b33c21ecb-0Q-a9222e59-18ff-4b3b-80ae-27bea8f149a9-1Q-0378a458-1ade-410e-a4b3-ae4aaa91d709-2Q-da4c00b6-61c1-49f5-8a0a-9f19990acfb7-3Q-21254889-3cf6-4d97-8dc5-ddf68360847e-4Q-502b8ed5-4050-461c-befc-76f6796dce68-5Q-364dc896-c399-4e58-8930-cba2e3d1d579-6Q-9072e904-da8d-4b00-b454-dac45b7c38f0-7C',
                'utcOffsetSec': -25200,
                'legendFormat': '',
                'datasourceId': 1,
                'intervalMs': interval * 1000,
                # 'maxDataPoints': 1383,
            },
            {
                'datasource': {
                    'type': 'prometheus',
                    'uid': 'AbuT5CJ4z',
                },
                'expr': 'histogram_quantile(0.5, sum(rate(synapse_http_server_response_time_seconds_bucket{servlet=\'RoomSendEventRestServlet\',index=~".*",instance="10.0.0.34:9000",code=~"2.."}[2m])) by (le))',
                'format': 'time_series',
                'intervalFactor': 1,
                'refId': 'B',
                'interval': '',
                # 'key': 'Q-da4c00b6-61c1-49f5-8a0a-9f19990acfb7-3',
                'queryType': 'timeSeriesQuery',
                'exemplar': False,
                # 'requestId': 'Q-d8eb3572-9aea-4a73-92f2-e08b33c21ecb-0Q-a9222e59-18ff-4b3b-80ae-27bea8f149a9-1Q-0378a458-1ade-410e-a4b3-ae4aaa91d709-2Q-da4c00b6-61c1-49f5-8a0a-9f19990acfb7-3Q-21254889-3cf6-4d97-8dc5-ddf68360847e-4Q-502b8ed5-4050-461c-befc-76f6796dce68-5Q-364dc896-c399-4e58-8930-cba2e3d1d579-6Q-9072e904-da8d-4b00-b454-dac45b7c38f0-7B',
                'utcOffsetSec': -25200,
                'legendFormat': '',
                'datasourceId': 1,
                'intervalMs': interval * 1000,
                # 'maxDataPoints': 1383,
            },
            {
                'datasource': {
                    'type': 'prometheus',
                    'uid': 'AbuT5CJ4z',
                },
                'expr': 'histogram_quantile(0.25, sum(rate(synapse_http_server_response_time_seconds_bucket{servlet=\'RoomSendEventRestServlet\',index=~".*",instance="10.0.0.34:9000",code=~"2.."}[2m])) by (le))',
                'refId': 'F',
                'interval': '',
                # 'key': 'Q-21254889-3cf6-4d97-8dc5-ddf68360847e-4',
                'queryType': 'timeSeriesQuery',
                'exemplar': False,
                # 'requestId': 'Q-d8eb3572-9aea-4a73-92f2-e08b33c21ecb-0Q-a9222e59-18ff-4b3b-80ae-27bea8f149a9-1Q-0378a458-1ade-410e-a4b3-ae4aaa91d709-2Q-da4c00b6-61c1-49f5-8a0a-9f19990acfb7-3Q-21254889-3cf6-4d97-8dc5-ddf68360847e-4Q-502b8ed5-4050-461c-befc-76f6796dce68-5Q-364dc896-c399-4e58-8930-cba2e3d1d579-6Q-9072e904-da8d-4b00-b454-dac45b7c38f0-7F',
                'utcOffsetSec': -25200,
                'legendFormat': '',
                'datasourceId': 1,
                'intervalMs': interval * 1000,
                # 'maxDataPoints': 1383,
            },
            {
                'datasource': {
                    'type': 'prometheus',
                    'uid': 'AbuT5CJ4z',
                },
                'expr': 'histogram_quantile(0.05, sum(rate(synapse_http_server_response_time_seconds_bucket{servlet=\'RoomSendEventRestServlet\',index=~".*",instance="10.0.0.34:9000",code=~"2.."}[2m])) by (le))',
                'refId': 'G',
                'interval': '',
                # 'key': 'Q-502b8ed5-4050-461c-befc-76f6796dce68-5',
                'queryType': 'timeSeriesQuery',
                'exemplar': False,
                # 'requestId': 'Q-d8eb3572-9aea-4a73-92f2-e08b33c21ecb-0Q-a9222e59-18ff-4b3b-80ae-27bea8f149a9-1Q-0378a458-1ade-410e-a4b3-ae4aaa91d709-2Q-da4c00b6-61c1-49f5-8a0a-9f19990acfb7-3Q-21254889-3cf6-4d97-8dc5-ddf68360847e-4Q-502b8ed5-4050-461c-befc-76f6796dce68-5Q-364dc896-c399-4e58-8930-cba2e3d1d579-6Q-9072e904-da8d-4b00-b454-dac45b7c38f0-7G',
                'utcOffsetSec': -25200,
                'legendFormat': '',
                'datasourceId': 1,
                'intervalMs': interval * 1000,
                # 'maxDataPoints': 1383,
            },
            {
                'datasource': {
                    'type': 'prometheus',
                    'uid': 'AbuT5CJ4z',
                },
                'expr': 'sum(rate(synapse_http_server_response_time_seconds_sum{servlet=\'RoomSendEventRestServlet\',index=~".*",instance="10.0.0.34:9000",code=~"2.."}[2m])) / sum(rate(synapse_http_server_response_time_seconds_count{servlet=\'RoomSendEventRestServlet\',index=~".*",instance="10.0.0.34:9000",code=~"2.."}[2m]))',
                'refId': 'H',
                'interval': '',
                # 'key': 'Q-364dc896-c399-4e58-8930-cba2e3d1d579-6',
                'queryType': 'timeSeriesQuery',
                'exemplar': False,
                # 'requestId': 'Q-d8eb3572-9aea-4a73-92f2-e08b33c21ecb-0Q-a9222e59-18ff-4b3b-80ae-27bea8f149a9-1Q-0378a458-1ade-410e-a4b3-ae4aaa91d709-2Q-da4c00b6-61c1-49f5-8a0a-9f19990acfb7-3Q-21254889-3cf6-4d97-8dc5-ddf68360847e-4Q-502b8ed5-4050-461c-befc-76f6796dce68-5Q-364dc896-c399-4e58-8930-cba2e3d1d579-6Q-9072e904-da8d-4b00-b454-dac45b7c38f0-7H',
                'utcOffsetSec': -25200,
                'legendFormat': '',
                'datasourceId': 1,
                'intervalMs': interval * 1000,
                # 'maxDataPoints': 1383,
            },
            {
                'datasource': {
                    'type': 'prometheus',
                    'uid': 'AbuT5CJ4z',
                },
                'expr': 'sum(rate(synapse_storage_events_persisted_events_total{instance="10.0.0.34:9000"}[2m]))',
                'hide': False,
                'instant': False,
                'refId': 'E',
                'interval': '',
                # 'key': 'Q-9072e904-da8d-4b00-b454-dac45b7c38f0-7',
                'editorMode': 'code',
                'queryType': 'timeSeriesQuery',
                'exemplar': False,
                # 'requestId': 'Q-d8eb3572-9aea-4a73-92f2-e08b33c21ecb-0Q-a9222e59-18ff-4b3b-80ae-27bea8f149a9-1Q-0378a458-1ade-410e-a4b3-ae4aaa91d709-2Q-da4c00b6-61c1-49f5-8a0a-9f19990acfb7-3Q-21254889-3cf6-4d97-8dc5-ddf68360847e-4Q-502b8ed5-4050-461c-befc-76f6796dce68-5Q-364dc896-c399-4e58-8930-cba2e3d1d579-6Q-9072e904-da8d-4b00-b454-dac45b7c38f0-7E',
                'utcOffsetSec': -25200,
                'legendFormat': '',
                'datasourceId': 1,
                'intervalMs': interval * 1000,
                # 'maxDataPoints': 1383,
            },
        ],
        'from': f'now-{data_range}m',
        'to': 'now',
    }
    response = requests.post(f'{endpoint}/api/ds/query', headers={'Authorization': f'Bearer {api_key}'}, json=json_data, verify=False).json()
    return np.round(np.average(response['results']['E']['frames'][0]['data']['values'][1]), 2)


def get_waiting_for_db(api_key, interval, data_range, endpoint):
    json_data = {
        'queries': [
            {
                'datasource': {
                    'type': 'prometheus',
                    'uid': 'AbuT5CJ4z',
                },
                'expr': 'rate(synapse_storage_schedule_time_sum{instance="10.0.0.34:9000",job=~"(federation-receiver|federation-sender|initialsync|synapse|synchrotron)",index=~".*"}[30s])/rate(synapse_storage_schedule_time_count[30s])',
                'format': 'time_series',
                'intervalFactor': 2,
                'refId': 'A',
                'step': 20,
                'interval': '',
                # 'key': 'Q-459af7f4-0427-4832-9353-46086b3f5c27-0',
                'queryType': 'timeSeriesQuery',
                'exemplar': False,
                # 'requestId': 'Q-459af7f4-0427-4832-9353-46086b3f5c27-0A',
                'utcOffsetSec': -25200,
                'legendFormat': '',
                'datasourceId': 1,
                'intervalMs': interval * 1000,
                # 'maxDataPoints': 1383,
            },
        ],
        'from': f'now-{data_range}m',
        'to': 'now',
    }
    response = requests.post(f'{endpoint}/api/ds/query', headers={'Authorization': f'Bearer {api_key}'}, json=json_data, verify=False).json()
    return np.round(np.average(response['results']['A']['frames'][0]['data']['values'][1]), 5)


def get_stateres_worst_case(api_key, interval, data_range, endpoint):
    """
    CPU and DB time spent on most expensive state resolution in a room, summed over all workers.
    This is a very rough proxy for "how fast is state res", but it doesn't accurately represent the system load (e.g. it completely ignores cheap state resolutions).
    """
    json_data = {
        'queries': [
            {
                'datasource': {
                    'type': 'prometheus',
                    'uid': 'AbuT5CJ4z',
                },
                'exemplar': False,
                'expr': 'sum(rate(synapse_state_res_db_for_biggest_room_seconds_total{instance="10.0.0.34:9000"}[1m]))',
                'format': 'time_series',
                'hide': False,
                'instant': False,
                'interval': '',
                'refId': 'B',
                'queryType': 'timeSeriesQuery',
                'utcOffsetSec': -25200,
                'legendFormat': '',
                'datasourceId': 1,
                'intervalMs': 15000,
                'maxDataPoints': 1863,
            },
            {
                'datasource': {
                    'type': 'prometheus',
                    'uid': 'AbuT5CJ4z',
                },
                'exemplar': False,
                'expr': 'sum(rate(synapse_state_res_cpu_for_biggest_room_seconds_total{instance="10.0.0.34:9000"}[1m]))',
                'format': 'time_series',
                'hide': False,
                'instant': False,
                'interval': '',
                'refId': 'C',
                'queryType': 'timeSeriesQuery',
                'utcOffsetSec': -25200,
                'legendFormat': '',
                'datasourceId': 1,
                'intervalMs': 15000,
                'maxDataPoints': 1863,
            },
        ],
        'range': {
            'from': '2023-02-23T04:36:12.870Z',
            'to': '2023-02-23T07:36:12.870Z',
            'raw': {
                'from': 'now-3h',
                'to': 'now',
            },
        },
        'from': f'now-{data_range}m',
        'to': 'now',
    }
    response = requests.post(f'{endpoint}/api/ds/query', headers={'Authorization': f'Bearer {api_key}'}, json=json_data, verify=False).json()


# AVerage CPU time per block
