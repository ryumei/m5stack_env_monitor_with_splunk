# -*- coding: utf-8 -*-
import sys
import time
import gc
sys.path[1] = '/flash/lib'
import utime
import network
import ujson
from m5stack import lcd, speaker, buttonA, buttonB, buttonC
from machine import RTC, I2C, Pin
import machine

from hec import post2hec

# ---------- Initial config -----------
lcd.setBrightness(5)
speaker.volume(0)

# ---------- M5Cloud ------------
OFFLINE_MODE = False
STATUS_COLOR = lcd.LIGHTGREY

def sync_rtc(interval=11, max_count=100):
    print("Try to synchronize network time")
    rtc = RTC()
    rtc.ntp_sync('ntp.nict.jp', tz='JST-9')

    count = 0
    while count < max_count:
        if rtc.synced():
            message = 'RTC synced. {}'.format(utime.localtime())
            print(message)
            lcd.println(message, color=lcd.GREEN)
            break
        utime.sleep_ms(interval)
        #print('.')
        count += 1

def reconnect(offline=OFFLINE_MODE):
    lcd.print("Reconnecting...", 10, 10, lcd.RED)
    if offline:
        return
    if not wifisetup.isconnected():
        wifisetup.auto_connect()
        sync_rtc()
    lcd.print("done")

def disconnect(offline=OFFLINE_MODE):
    lcd.print("Disconnecting...", 10, 10, lcd.RED)
    if offline:
        return
    if not wifisetup.isconnected():
        wlan = network.WLAN(network.STA_IF)  # create station interface
        wlan.active(False)                   # activate the interface
    lcd.print("done")

# ----------------------------------------------------------
# Entry point

if buttonB.isPressed():
    STATUS_COLOR = lcd.CYAN
    OFFLINE_MODE = True
    lcd.println('On: OFF-LINE Mode', color=STATUS_COLOR)
else:
    import wifisetup
    sync_rtc()
    disconnect()

lcd.print("Entering measurement mode...")
time.sleep(3)

HOSTNAME = 'M5Stack'
CONFIG_FILE = 'config.json'

hec_url = None
hec_token = None
hostname = HOSTNAME
try:
    with open(CONFIG_FILE) as f:
        jdata = ujson.loads(f.read())
        if 'hec' in jdata:
            hec_url = jdata['hec'].get('url', None)
            hec_token = jdata['hec'].get('token', None)
            hostname = jdata['hec'].get('hostname', HOSTNAME)
except Exception as exp:
    print(exp)

# Draw atmosphere data

#lcd.font(lcd.FONT_Ubuntu)
lcd.font(lcd.FONT_DejaVu18)
lcd.clear()

lcd.print('DHT12',        10,  50)
lcd.print('humidity:',    30,  75)
lcd.print('temperature:', 30, 100)
lcd.print('BMP280',       10, 125)
lcd.print('temperature:', 30, 150)
lcd.print('pressure:',    30, 175)

def display_measurement(localtime_str, d_h, d_t, b_t, b_p):
    lcd.print(localtime_str, 10, 10, color=STATUS_COLOR)
    lcd.print('{:8.2f}%'.format(d_h),   160,  75) # DHT12の湿度
    lcd.print('{:8.2f}C'.format(d_t),   160, 100) # DHT12の気温
    lcd.print('{:8.2f}C'.format(b_t),   160, 150) # BMP280の気温
    lcd.print('{:8.2f}hPa'.format(b_p), 160, 175) # BMP280の気圧

from bme280 import BME280
from dht12 import DHT12

i2c = I2C(scl=Pin(22), sda=Pin(21))
bme = BME280(i2c=i2c)
dht = DHT12(i2c=i2c)

interval_ms = 3 * 1000
post_interval_sec = 30

last_recorded = 0
while True:
    try:
        b_data = bme.read_compensated_data()
        b_t = b_data[0] / 100.0 # deg C
        b_h = b_data[2] / 1024.0 # %
        b_p = b_data[1] / 25600.0 # hPa

        dht.measure()
        d_h = dht.humidity()
        d_t = dht.temperature()

        localtime = utime.localtime()
        localtime_epoch = utime.mktime(localtime)
        localtime_str = time.strftime('%Y-%m-%d %H:%M:%S', localtime)

        display_measurement(localtime_str, d_h, d_t, b_t, b_p)

        if (localtime_epoch - last_recorded) > post_interval_sec:
            values = [
                {'sensor': 'DHT12', 'name': 'humidity', 'value': d_h},
                {'sensor': 'DHT12', 'name': 'temperature', 'value': d_t},
                {'sensor': 'BMP280', 'name': 'pressure', 'value': b_p},
            ]
            lcd.print("Sending to HEC...", 10, 10, lcd.RED)
            reconnect()
            #post2hec(url=hec_url, token=hec_token, host=hostname,
            #         values=values)
            post2hec(url=hec_url, token=hec_token, host=hostname,
                     values=values, timestamp=localtime_epoch)
            disconnect()
            last_recorded = localtime_epoch

        utime.sleep_ms(interval_ms - int(localtime_epoch % 1 * 1000))
    except Exception as exp:
        # 時々I2C bus error が起きる。
        # データを取得できなかった時は時刻を赤字で表示
        lcd.print(localtime_str, 10, 10, lcd.RED)
        print(localtime_str, ' Script Name: ', __name__)
        print('Exception: ', exp)

    gc.collect()
