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

def get_audio_routing_cmd(phone_number, skip_rerouting=False):
    """Construct the audio routing command with the given phone number

    Args:
        phone_number: Phone number to dial
        skip_rerouting: If True, adds -r flag to skip audio re-routing
    """
    cmd = ["/usr/bin/python3", "/mnt/data/place_call.py", "-n", phone_number, "-v"]
    if skip_rerouting:
        cmd.append("-r")
    return cmd

def monitor_baresip_output(proc, phone_number, skip_rerouting=False):
    for line in iter(proc.stdout.readline, ''):
        decoded_line = line.strip()
        logging.info(f"[BARESIP] {decoded_line}")

        if CALL_ESTABLISHED_REGEX.search(decoded_line):
            logging.info("Call established. Routing audio call...")
            audio_cmd = get_audio_routing_cmd(phone_number, skip_rerouting)
            audio_proc = subprocess.Popen(audio_cmd)

            # Wait for place_call.py to complete
            logging.info("Waiting for place_call.py to complete...")
            audio_proc.wait()
            logging.info("place_call.py completed. Terminating baresip...")

            # Terminate baresip by closing stdin and then terminating the process
            # Baresip doesn't have a "quit" command, so we need to terminate it properly
            try:
                proc.stdin.close()
                logging.info("Closed stdin to baresip.")
                # Give it a moment to cleanly shutdown
                proc.wait(timeout=2)
                logging.info("Baresip terminated gracefully.")
            except Exception as e:
                logging.warning(f"Baresip did not terminate gracefully: {e}. Sending SIGTERM...")
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                    logging.info("Baresip terminated via SIGTERM.")
                except Exception:
                    logging.warning("Baresip did not respond to SIGTERM. Sending SIGKILL...")
                    proc.kill()
                    logging.info("Baresip killed.")
            break

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Monitor Baresip and route audio calls')
    parser.add_argument('-n', '--number', default='9723507770',
                        help='Phone number to dial (default: 9723507770)')
    parser.add_argument('-r', '--skip-rerouting', action='store_true',
                        help='Skip audio re-routing (pass -r to place_call.py)')
    args = parser.parse_args()

    logging.info(f"Starting Baresip... Will dial number: {args.number}")
    baresip_proc = subprocess.Popen(
        [BARESIP_CMD],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
        text=True
    )

    monitor_thread = threading.Thread(target=monitor_baresip_output, args=(baresip_proc, args.number, args.skip_rerouting))
    monitor_thread.start()

    try:
        while baresip_proc.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Ctrl+C detected. Terminating baresip for clean shutdown...")
        try:
            baresip_proc.stdin.close()
            logging.info("Closed stdin to baresip. Waiting for baresip to exit...")
            baresip_proc.wait(timeout=5)
            logging.info("Baresip exited gracefully.")
        except Exception as e:
            logging.warning(f"Error during clean shutdown: {e}. Forcing termination...")
            baresip_proc.terminate()
            try:
                baresip_proc.wait(timeout=3)
            except Exception:
                baresip_proc.kill()
        finally:
            monitor_thread.join(timeout=5)
            logging.info("Shutdown complete.")

if __name__ == "__main__":
    # Set up logging to file and console with milliseconds in timestamp
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

    main()
