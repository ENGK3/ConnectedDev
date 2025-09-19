import serial
import time
import argparse
import subprocess
import signal
import os
import logging
from pathlib import Path
import logging.handlers

def sbc_cmd(cmd: str, serial_connection: serial.Serial, verbose: bool) -> str:
    """
    Send a command to the SBC and return the response.
    """
    if verbose:
        logging.info(f"Sending command: {cmd.strip()}")
    serial_connection.write(cmd.encode())
    response = serial_connection.readline()
    response = serial_connection.readline()  # Read the response

    if verbose:
        logging.info(f"Response: {response.decode().strip()}")
    return response.decode().strip()

def start_audio_bridge():
    """
    Start the two audio bridge shell commands as background processes.
    Returns a tuple of their PIDs (pid1, pid2).
    """
    # First pipeline:
    # arecord -D hw:CARD=LE910C1NF,0 -r 16000 -f S16_LE -c 1 |
    # sox -t raw -r 16000 -e signed -b 16 -c 1 - -r 48000 -t wav - |
    # aplay -D hw:CARD=SGTL5000Card,0 -r 48000

    arecord1 = ["arecord", "-D", "hw:CARD=LE910C1NF,0", "-r", "16000", "-f", "S16_LE", "-c", "1"]
    sox1 = [
        "sox", "-t", "raw", "-r", "16000", "-e", "signed", "-b", "16", "-c", "1", "-", "-r", "48000", "-t", "wav", "-"
    ]
    aplay1 = ["aplay", "-D", "hw:CARD=SGTL5000Card,0", "-r", "48000"]

    # Second pipeline:
    # arecord -D hw:CARD=SGTL5000Card,0 -r 48000 -f S16_LE -c 1 |
    # sox -t raw -r 48000 -e signed -b 16 -c 1 - -r 16000 -t wav - |
    # aplay -D hw:CARD=LE910C1NF,0 -r 16000 -c 2

    arecord2 = ["arecord", "-D", "hw:CARD=SGTL5000Card,0", "-r", "48000", "-f", "S16_LE", "-c", "1"]
    sox2 = [
        "sox", "-t", "raw", "-r", "48000", "-e", "signed", "-b", "16", "-c", "1", "-", "-r", "16000", "-t", "wav", "-"
    ]
    aplay2 = ["aplay", "-D", "hw:CARD=LE910C1NF,0", "-r", "16000", "-c", "2"]

    # Start first pipeline
    p1_arecord = subprocess.Popen(arecord1, stdout=subprocess.PIPE)
    p1_sox = subprocess.Popen(sox1, stdin=p1_arecord.stdout, stdout=subprocess.PIPE)
    p1_aplay = subprocess.Popen(aplay1, stdin=p1_sox.stdout)

    # Start second pipeline
    p2_arecord = subprocess.Popen(arecord2, stdout=subprocess.PIPE)
    p2_sox = subprocess.Popen(sox2, stdin=p2_arecord.stdout, stdout=subprocess.PIPE)
    p2_aplay = subprocess.Popen(aplay2, stdin=p2_sox.stdout)

    # Return the PIDs of the aplay and sox processes for both pipelines
    # Order: (p1_aplay, p1_sox, p2_aplay, p2_sox)
    return (p1_aplay.pid, p1_sox.pid, p2_aplay.pid, p2_sox.pid)

def terminate_pids(pid_list):
    """
    Terminate the processes with the given list of PIDs.
    """
    for pid in pid_list:
        try:
            # Send SIGTERM first
            os.kill(pid, signal.SIGTERM)
        except Exception as e:
            logging.error(f"Failed to terminate PID {pid}: {e}")

def sbc_config_call(serial_connection: serial.Serial, verbose: bool):

    at_cmd_set = [
        "ATE1\r",
        "AT#DVI=0\r",
        "AT#PCMRXG=1000\r",
        "AT#DIALMODE=1\r",
        "AT#DTMF=1\r",
        "AT+CLIP=1\r",
        "AT+CMEE=2\r",
        "AT#AUSBC=1\r",
        "AT+CEREG=2\r",
        "AT+CLVL=0\r",
        "AT+CMER=2,0,0,2\r",
        "AT#ADSPC=6\r",
        "AT+CIND=0,0,1,0,1,1,1,1,0,1,0\r"
    ]

    for cmd in at_cmd_set:
        sbc_cmd(cmd, serial_connection, verbose)


def sbc_place_call(number: str, modem: serial.Serial, verbose: bool = True) -> bool:
    sbc_config_call(modem, verbose)
    sbc_cmd(f"ATD{number};\r", modem, verbose)  # Place the call
    audio_pids = None
    start_time = time.time()
    timeout = 30  # 30 second timeout
    call_connected = False

    while True:
        # Check for timeout
        if (time.time() - start_time > timeout) and call_connected is False:
            logging.warning("Call connection timeout after 30 seconds")
            break

        response = modem.readline().decode().strip()
        logging.info(f"Waiting for call response: {response}")
        if "+CIEV: call,1" in response:
            logging.info("Call connected successfully.")
            audio_pids = start_audio_bridge()
            logging.info(f"Audio bridge started with PIDs: {audio_pids}")
            call_connected = True

        elif "+CIEV: call,0" in response:
            logging.info("Call setup Terminated.")
            break  # Exit the loop but don't return yet

        elif "NO CARRIER" in response:
            logging.info("Call terminated")
            break  # Exit the loop but don't return yet
        time.sleep(0.5)  # Avoid busy waiting

    sbc_cmd("AT+CHUP\r", modem, verbose)
    if audio_pids:
        terminate_pids(audio_pids)
        logging.info("Audio bridge terminated.")
    return call_connected  # Return the connection status after loop exits


def sbc_connect(serial_connection: serial.Serial):
    serial_connection.port = "/dev/ttyUSB2"
    serial_connection.baudrate = 115200
    serial_connection.timeout = 30
    serial_connection.xonxoff = False
    print(f"Connecting to SBC on port {serial_connection.port} with baud rate {serial_connection.baudrate}")
    try:
        print(serial_connection.is_open)
        serial_connection.open()
        serial_connection.write(b"ATE0\r")
        response = serial_connection.readline()
        response = serial_connection.readline()
        print(f"SBC connected successfully?: {response.decode().strip()}")
        print(serial_connection.is_open)


    except Exception as e:
        logging.error(f"Failed to connect to SBC: {e}")
    return serial_connection.is_open

def start_reg_again(serial_connection: serial.Serial):
    logging.info("Starting registration process again")
    sbc_cmd("AT+COPS=2\r", serial_connection, verbose=True)
    sbc_cmd("AT+COPS=0\r", serial_connection, verbose=True)


def check_registration(serial_connection: serial.Serial):
    response =  sbc_cmd("AT+CEREG?\r", serial_connection, verbose=True)
    if response.startswith("+CEREG:"):
        parts = response.split(",")
        if len(parts) > 1:
            stat = parts[1].strip()
            if stat in ["1", "5"]:
                logging.info(f"Modem registered: stat={stat}")
                return True
            else:
                logging.info(f"Modem not registered yet: stat={stat}")
                start_reg_again(serial_connection)

    return False

def sbc_disconnect(serial_connection: serial.Serial):
    serial_connection.close()
    logging.info(f"Disconnected from SBC on port {serial_connection.port}")


if __name__ == "__main__":
    # Set up logging to syslog with milliseconds in timestamp

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M:%S',
                        filename="/mnt/data/calls.log",
                        filemode='a+')

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s.%(msecs)03d:%(levelname)-8s %(message)s', datefmt='%H:%M:%S')
    formatter.default_msec_format = '%s.%03d'
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


    parser = argparse.ArgumentParser(description="Serial SBC dialer")
    parser.add_argument("-n", "--number", type=str, help="Phone number to dial",
                        default="9723507770")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    serial_connection = serial.Serial()
    if sbc_connect(serial_connection):
        logging.info(f"Ready to dial number: {args.number}")
        call_success = sbc_place_call(args.number, serial_connection, verbose=args.verbose)
        if call_success:
            logging.info("Call completed successfully")
        else:
            logging.warning("Call failed or timed out")

    Path('/tmp/setup').touch()

    sbc_disconnect(serial_connection)

