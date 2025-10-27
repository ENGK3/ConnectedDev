import argparse
import logging
import subprocess
import sys
import time

import serial


def sbc_cmd(cmd: str, serial_connection: serial.Serial, verbose: bool) -> str:
    """
    Send a command to the SBC and return the response.
    """
    if verbose:
        logging.debug(f"Sending command: {cmd.strip()}")
    serial_connection.write(cmd.encode())

    response = serial_connection.readline()
    response = serial_connection.readline()  # Read the response
    if verbose:
        logging.debug(f"Response: {response.decode().strip()}")
    return response.decode().strip()


def check_modem_registration(
    port="/dev/ttyUSB2", baudrate=115200, timeout=30, max_wait=300, verbose=True
) -> bool:
    """
    Checks if the modem is registered on the network using AT+CEREG? command.
    Returns True if registered within max_wait seconds, else False.
    """
    time.sleep(5)
    ser = serial.Serial()
    ser.port = port
    ser.baudrate = baudrate
    ser.timeout = timeout
    ser.xonxoff = False
    try:
        ser.open()

    except Exception as e:
        logging.error(f"Failed to open serial port: {e}")
        return False

    logging.info(f"Opened serial port: {port}")
    sbc_cmd("ATE0\r", ser, verbose)  # Disable echo
    sbc_cmd("AT+CMEE=2\r", ser, verbose)  # Enable verbose error messages
    sbc_cmd("AT+CEREG=2\r", ser, verbose)
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            logging.info("Querying modem registration status...")
            response = sbc_cmd("AT+CEREG?\r", ser, verbose)
            logging.info(f"Modem response: {response}")
            # Read until we get a line with +CEREG:
            while response and not response.startswith("+CEREG:"):
                response = sbc_cmd("AT+CEREG?\r", ser, verbose)
                logging.info(f"Modem response: {response}")
            if response.startswith("+CEREG:"):
                # +CEREG: <n>,<stat>[,...]
                # stat: 1=registered (home), 5=registered (roaming)
                parts = response.split(",")
                if len(parts) > 1:
                    stat = parts[1].strip()
                    if stat in ["1", "5"]:
                        logging.info(f"Modem registered: stat={stat}")
                        ser.close()
                        return True
                    else:
                        logging.info(f"Modem not registered yet: stat={stat}")
            time.sleep(2)
            logging.debug(f"Waiting again {response}")

        except Exception as e:
            logging.error(f"Error querying modem: {e}")
            time.sleep(5)
    ser.close()
    logging.warning("Registration timeout.")
    aplay1 = ["aplay", "-D", "hw:SGTL5000Card,0", "/mnt/data/sounds/ENU00456-48k.wav"]
    subprocess.Popen(aplay1, start_new_session=True)
    return False


if __name__ == "__main__":
    # Set up logging to syslog
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%m-%d %H:%M",
        filename="/mnt/data/calls.log",
        filemode="a+",
    )

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s:%(levelname)-8s %(message)s", datefmt="%H:%M:%S "
    )
    console.setFormatter(formatter)
    logging.getLogger("").addHandler(console)

    parser = argparse.ArgumentParser(description="Check modem registration")
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress console output (for shell scripts)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    args = parser.parse_args()

    # If quiet mode, remove console handler
    if args.quiet:
        logging.getLogger("").removeHandler(console)

    result = check_modem_registration(
        port="/dev/ttyUSB2",
        baudrate=115200,
        timeout=10,
        max_wait=30,
        verbose=args.verbose,
    )
    sys.exit(0 if result else 1)
