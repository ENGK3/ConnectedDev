import argparse
import logging
import re
import subprocess
import threading
import time

# Path to baresip binary
BARESIP_CMD = "/usr/bin/baresip"
BARESIP_FIFO_PATH = "/tmp/baresip_fifo"

# Regex to detect call established and call closed
CALL_ESTABLISHED_REGEX = re.compile(r".*call established.*", re.IGNORECASE)
CALL_CLOSED_REGEX = re.compile(r".*terminate call.*", re.IGNORECASE)

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


def send_baresip_command(command):
    """Send a command to baresip via its FIFO interface

    Args:
        command: Command string to send to baresip
    """
    try:
        with open(BARESIP_FIFO_PATH, "w") as fifo:
            fifo.write(f"{command}\n")
            fifo.flush()
            logging.info(f"Sent command to baresip: {command}")
    except Exception as e:
        logging.error(f"Failed to send command to baresip: {e}")


def monitor_baresip_output(proc, phone_number, skip_rerouting=False, stop_event=None):
    """Monitor baresip output and handle incoming calls

    Args:
        proc: Baresip subprocess
        phone_number: Phone number to dial for audio routing
        skip_rerouting: If True, skip audio re-routing
        stop_event: Threading event to signal when to stop monitoring
    """
    call_in_progress = False
    audio_proc = None

    for line in iter(proc.stdout.readline, ""):
        if stop_event and stop_event.is_set():
            logging.info("Stop event detected. Exiting monitor loop.")
            break

        decoded_line = line.strip()
        logging.info(f"[BARESIP] {decoded_line}")

        if CALL_ESTABLISHED_REGEX.search(decoded_line):
            logging.info("Call established. Routing audio call...")
            call_in_progress = True
            audio_cmd = get_audio_routing_cmd(phone_number, skip_rerouting)
            audio_proc = subprocess.Popen(audio_cmd)

            # Wait for place_call.py to complete
            logging.info("Waiting for place_call.py to complete...")
            audio_proc.wait()
            logging.info("place_call.py completed.")

            # Terminate the baresip call now that place_call.py is done
            logging.info("Terminating baresip call...")
            send_baresip_command("/hangup")
            time.sleep(1)  # Give some time for the hangup to process

            call_in_progress = False
            audio_proc = None

            logging.info("Ready for next incoming call...")

        elif CALL_CLOSED_REGEX.search(decoded_line):
            if call_in_progress:
                logging.info("Call closed detected while call was in progress.")
                # Terminate audio routing if still running
                if audio_proc and audio_proc.poll() is None:
                    logging.info("Terminating audio routing process...")
                    audio_proc.terminate()
                    try:
                        audio_proc.wait(timeout=3)
                    except Exception:
                        audio_proc.kill()
                call_in_progress = False
                audio_proc = None
            logging.info("Waiting for next incoming call...")


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Monitor Baresip and route audio calls"
    )
    parser.add_argument(
        "-n",
        "--number",
        default="9723507770",
        help="Phone number to dial (default: 9723507770)",
    )
    parser.add_argument(
        "-r",
        "--skip-rerouting",
        action="store_true",
        help="Skip audio re-routing (pass -r to place_call.py)",
    )
    args = parser.parse_args()

    stop_event = threading.Event()

    logging.info(
        f"Starting Baresip in continuous mode... Will dial number: {args.number}"
    )
    logging.info("Press Ctrl+C to exit.")

    baresip_proc = subprocess.Popen(
        [BARESIP_CMD],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
        text=True,
    )

    monitor_thread = threading.Thread(
        target=monitor_baresip_output,
        args=(baresip_proc, args.number, args.skip_rerouting, stop_event),
    )
    monitor_thread.start()

    try:
        # Keep running until interrupted
        while baresip_proc.poll() is None and not stop_event.is_set():
            time.sleep(1)

        # If baresip died unexpectedly, log it
        if baresip_proc.poll() is not None and not stop_event.is_set():
            logging.error("Baresip process terminated unexpectedly.")

    except KeyboardInterrupt:
        logging.info("Ctrl+C detected. Terminating baresip for clean shutdown...")
        stop_event.set()

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
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s",
        datefmt="%m-%d %H:%M:%S",
        filename="/mnt/data/calls.log",
        filemode="a+",
    )

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d:%(levelname)-8s %(message)s", datefmt="%H:%M:%S"
    )
    formatter.default_msec_format = "%s.%03d"
    console.setFormatter(formatter)
    logging.getLogger("").addHandler(console)

    main()
