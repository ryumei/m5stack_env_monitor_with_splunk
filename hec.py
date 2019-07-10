# -*- coding: utf-8 -*-
import time
import urequests as requests

# See also http://dev.splunk.com/view/event-collector/SP-CAAAE7G

def post2hec(url, token, values, host='M5Stack', source=None, index=None, timestamp=None):
    u'Send measured data to Splunk HEC'
    headers = {'Authorization': 'Splunk {}'.format(token)}
    payload = []
    for data in values:
        p = {
            "event": "metric",
            "source": source if source is not None else data['sensor'],
            "host": host,
            "fields": {
                "metric_name": data['name'],
                "sensor": data['sensor'],
                "_value": data["value"],
            }
        }
        if index is not None:
            p['index'] = index
        if timestamp is not None:
            p['time'] = timestamp
        payload.append(p)

    print("[DEBUG] HEC payload", payload)
    try:
        res = requests.post(url, headers=headers, json=payload)
        print("[DEBUG] HEC Response:", res.status_code, res.text)
    except ValueError as exp:
        print('[ERROR] No valid response. {}'.format(exp))
        raise exp
    except OSError as exp:
        print('[ERROR] Connection Error. {}'.format(exp))
        raise exp
    except Exception as exp:
        print('[ERROR] HEC Error: {}'.format(exp))
        raise exp
    finally:
        res.close()
