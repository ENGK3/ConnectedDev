#!/usr/bin/env python3

import json
import subprocess
import time

from dotenv import dotenv_values

json_filename = "/tmp/sensors.json"


def send_edc_event_data(event_code):
    try:
        # Run the command and capture output
        result = subprocess.run(
            ["python3", "/mnt/data/send_EDC_info.py", "-v", "-e", event_code],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("Error sending event data packet:", result.stderr)
            return False

    except Exception as e:
        print("Exception occurred:", e)
        return False

    return True


json_loaded = False
while not json_loaded:
    try:
        # get baseline system voltage & temperature
        # Open the JSON file in read mode
        with open(json_filename) as f:
            # Load the JSON data from the file
            data = json.load(f)
            voltage = data["gsc_hwmon-isa-0000"]["vdd_vin"]["in1_input"]
            json_loaded = True
            break

    except Exception as e:
        print("Exception occurred:", e)

    time.sleep(5)

# get event reporting frequency
config = dotenv_values(
    "/mnt/data/K3_config_settings"
)  # Load environment variables from .env file
delay = config.get("EVT_MON_PERIOD_SECS", "60")

# set initial values
ac_power_loss_reported = False
low_battery_reported = False
ac_power_restore_reported = False

if float(voltage) > 25:
    ac_power = True
    battery_power = False
    low_battery = False
elif 24 < float(voltage) < 25:
    ac_power = False
    battery_power = True
    low_battery = False
elif float(voltage) < 24:
    ac_power = False
    battery_power = True
    low_battery = True

event_codes = []

while True:
    json_loaded = False
    while not json_loaded:
        try:
            # get system voltage & temperature
            # Open the JSON file in read mode
            with open(json_filename) as f:
                # Load the JSON data from the file
                data = json.load(f)
                voltage = data["gsc_hwmon-isa-0000"]["vdd_vin"]["in1_input"]
                json_loaded = True
                break

        except Exception as e:
            print("Exception occurred:", e)

        time.sleep(5)

    # AC Loss
    if (
        float(voltage) < 25 and ac_power is True and ac_power_loss_reported is False
    ) or (ac_power is False and ac_power_loss_reported is False):
        ac_power = False
        battery_power = True
        event_codes.append("F5")
        ac_power_loss_reported = True
    # Low Battery
    if float(voltage) < 24 and battery_power and low_battery_reported is False:
        low_battery = True
        event_codes.append("F7")
        low_battery_reported = True
    # AC restored
    if float(voltage) > 25 and ac_power is False and ac_power_restore_reported is False:
        ac_power = True
        battery_power = False
        low_battery = False
        event_codes.append("F6")
        ac_power_restore_reported = True
        ac_power_loss_reported = False
        low_battery_reported = False

    # send event packet if codes are present in the list
    if event_codes != []:
        for event in event_codes:
            print("sending event code " + event)
            send_edc_event_data(event)
            print("data packet sent")
            print("")
            time.sleep(1)

    time.sleep(int(delay))
    event_codes = []
