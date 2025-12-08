import logging
import sys

import serial

# Import shared modem utilities
from modem_utils import sbc_cmd_with_timeout, sbc_connect, sbc_disconnect

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)-8s [%(threadName)s] %(message)s",
    datefmt="%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("modemstate.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

at_cmd_set = [
    "AT#DVI?\r",
    "AT#PCMRXG?\r",
    "AT#DIALMODE?\r",
    "AT#DTMF?\r",
    "AT+CLIP?\r",
    "AT+CMEE?\r",
    "AT#AUSBC?\r",
    "AT+CEREG?\r",
    "AT+CLVL?\r",
    "AT+CMER?\r",
    "AT#ADSPC?\r",
    "AT+CIND?\r",
    "AT+CMUT?\r",
    "AT#SPKMUT?\r",
]
# Connect to modem
serial_connection = serial.Serial()
if not sbc_connect(serial_connection, port="/dev/ttyUSB3"):
    print("Failed to connect to modem")
    sys.exit(1)


for cmd in at_cmd_set:
    sbc_cmd_with_timeout(cmd, serial_connection, verbose=True)

sbc_disconnect(serial_connection)
