import subprocess
import threading
import re
import time
import logging
import argparse
from pathlib import Path

# Path to baresip binary
BARESIP_CMD = "/usr/bin/baresip"

# Regex to detect call established
CALL_ESTABLISHED_REGEX = re.compile(r".*call established.*", re.IGNORECASE)

# Command to route audio (example using pactl or custom script)
# AUDIO_ROUTING_CMD will be constructed in main() with the phone number

def get_audio_routing_cmd(phone_number):
    """Construct the audio routing command with the given phone number"""
    return ["/usr/bin/python3", "/mnt/data/place_call.py", "-n", phone_number, "-v"]

def monitor_baresip_output(proc, phone_number):
    for line in iter(proc.stdout.readline, ''):
        decoded_line = line.strip()
        logging.info(f"[BARESIP] {decoded_line}")

        if CALL_ESTABLISHED_REGEX.search(decoded_line):
            logging.info("Call established. Routing audio call...")
            audio_cmd = get_audio_routing_cmd(phone_number)
            audio_proc = subprocess.Popen(audio_cmd)

            # Wait for place_call.py to complete
            logging.info("Waiting for place_call.py to complete...")
            audio_proc.wait()
            logging.info("place_call.py completed. Sending quit command to baresip...")

            # Send quit command to baresip to terminate the SIP call
            proc.stdin.write("quit\n")
            proc.stdin.flush()
            logging.info("Quit command sent to baresip.")
            break

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Monitor Baresip and route audio calls')
    parser.add_argument('-n', '--number', default='9723507770',
                        help='Phone number to dial (default: 9723507770)')
    args = parser.parse_args()

    logging.info(f"Starting Baresip... Will dial number: {args.number}")
    baresip_proc = subprocess.Popen(
        [BARESIP_CMD],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
        text=True
    )

    monitor_thread = threading.Thread(target=monitor_baresip_output, args=(baresip_proc, args.number))
    monitor_thread.start()

    try:
        while baresip_proc.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Terminating Baresip...")
        baresip_proc.terminate()
        monitor_thread.join()

if __name__ == "__main__":
    # Set up logging to file and console with milliseconds in timestamp
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M:%S',
                        filename="/mnt/data/voip_calls.log",
                        filemode='a+')

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s.%(msecs)03d:%(levelname)-8s %(message)s', datefmt='%H:%M:%S')
    formatter.default_msec_format = '%s.%03d'
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    main()
