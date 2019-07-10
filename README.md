Send M5Stack ENV Module data to Splunk HTTP Event Collector



### reference libraries
* [`urequests`](https://github.com/micropython/micropython-lib/blob/master/urequests/urequests.py)

### Splunk
```
| mstats avg(_value) span=10min WHERE metric_name=* AND index=atmosphere BY metric_name, host, sensor
```

