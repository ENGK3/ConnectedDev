import csv
import sys

import serial

# Add the parent directory to sys.path
sys.path.append("/mnt/data")

# Now you can import modules from the parent directory
from modem_utils import get_modem_info, sbc_connect

serial_connection = serial.Serial()
if sbc_connect(serial_connection, port="/dev/ttyUSB3"):
    modem_data = get_modem_info(serial_connection)

    # iccid,
    # imei,
    # imsi,
    # rsrq,
    # rsrp,
    # modem_temp,
    # network,
    # ims_reg,
    # signal_quality,
    # facility_lock,
    # APN

    # Get RSRQ value from LUT
    with open("/mnt/data/RSRQ_LUT.csv", newline="") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row[0] == str(modem_data[3]):
                rsrq = row[1]

    # Get RSRP value from LUT
    with open("/mnt/data/RSRP_LUT.csv", newline="") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row[0] == str(modem_data[4]):
                rsrp = row[1]

    # Get RSSI value from LUT
    with open("/mnt/data/RSSI_LUT.csv", newline="") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row[0] == str(modem_data[8]):
                signal_quality = row[1]

    print(f"export iccid='{modem_data[0]}'")
    print(f"export imei='{modem_data[1]}'")
    print(f"export imsi='{modem_data[2]}'")
    print(f"export rsrq='{rsrq}'")
    print(f"export rsrp='{rsrp}'")
    print(f"export modem_temp='{modem_data[5]}'")
    print(f"export network='{modem_data[6]}'")
    print(f"export ims_reg='{modem_data[7]}'")
    print(f"export signal_quality='{signal_quality}'")
    print(f"export facility_lock='{modem_data[9]}'")
    print(f"export apn='{modem_data[10]}'")
