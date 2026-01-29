import argparse
import logging
import logging.handlers
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import dotenv_values

# Import modem manager client
from modem_manager_client import ModemManagerClient

# Import shared dial code parsing utilities
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "common"))
from dial_code_utils import parse_special_dial_code

# Call timeout constant (seconds to wait for call to connect)
CALL_TIMEOUT_SECONDS = 20


def send_edc_packet(edc_code=None):
    """Send EDC packet by calling send_EDC_info.py script.

    Args:
        edc_code: EDC code to use ("DC" for diagnostic, None for default "01")
    """
    # Use "DC" for diagnostic or "01" as default
    code = edc_code if edc_code else "01"
    logging.info(f"Sending EDC packet with code: {code}")

    try:
        # Call send_EDC_info.py script
        result = subprocess.run(
            ["python3", "/mnt/data/send_EDC_info.py", "-e", code],
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout for EDC packet sending
        )

        if result.returncode == 0:
            logging.info(f"EDC packet sent successfully (code: {code})")
            if result.stdout:
                logging.debug(f"EDC output: {result.stdout}")
        else:
            logging.error(
                f"Failed to send EDC packet (code: {code}), "
                f"return code: {result.returncode}"
            )
            if result.stderr:
                logging.error(f"EDC error: {result.stderr}")

    except subprocess.TimeoutExpired:
        logging.error("EDC packet sending timed out after 60 seconds")


def place_call_with_client(
    number: str,
    verbose: bool = True,
    no_audio_routing: bool = False,
    modem_manager_host: str = "localhost",
    modem_manager_port: int = 5555,
) -> bool:
    """
    Place a call using the modem manager client interface.

    Args:
        number: Phone number to dial
        verbose: Enable verbose logging
        no_audio_routing: Disable audio routing (establish call only)
        modem_manager_host: Modem manager server host
        modem_manager_port: Modem manager server port

    Returns:
        True if call was successfully established, False otherwise
    """
    try:
        # Connect to modem manager
        client = ModemManagerClient(
            modem_manager_host, modem_manager_port, timeout=CALL_TIMEOUT_SECONDS + 10
        )

        if not client.connect():
            logging.error("Failed to connect to modem manager")
            return False

        try:
            logging.info(f"Placing call to {number} via modem manager...")

            # Request call placement
            response = client.place_call(number, no_audio_routing)

            if response.get("status") == "error":
                logging.error(f"Call placement failed: {response.get('message')}")
                return False

            if response.get("status") == "pending":
                logging.info(f"Call initiated: {response.get('message')}")

            # Poll status to wait for call to connect
            start_time = time.time()
            call_connected = False

            while time.time() - start_time < CALL_TIMEOUT_SECONDS:
                status_response = client.get_status()

                if status_response.get("status") == "success":
                    status_data = status_response.get("data", {})

                    if status_data.get("call_connected"):
                        call_connected = True
                        logging.info(
                            f"Call connected successfully to "
                            f"{status_data.get('current_number')}"
                        )
                        break

                    # Check if call failed (modem went back to IDLE without connecting)
                    if status_data.get("state") == "IDLE" and not status_data.get(
                        "call_active"
                    ):
                        logging.warning(
                            "Call setup failed - modem returned to IDLE state"
                        )
                        break

                # Wait a bit before next status check
                time.sleep(0.5)

            if not call_connected:
                if time.time() - start_time >= CALL_TIMEOUT_SECONDS:
                    logging.warning(
                        f"Call connection timeout after {CALL_TIMEOUT_SECONDS} seconds"
                    )
                    # Send hangup to ensure modem returns to IDLE state
                    try:
                        logging.info("Sending hangup command to clean up modem state")
                        client.hangup()
                        time.sleep(0.5)
                    except Exception as e:
                        logging.warning(f"Failed to send hangup after timeout: {e}")
                return False

            # Call is connected - wait for user to hang up or call to end
            # Monitor status until call ends
            logging.info("Call is active. Monitoring call status...")

            while True:
                status_response = client.get_status()

                if status_response.get("status") == "success":
                    status_data = status_response.get("data", {})

                    # Check if call ended
                    if (
                        not status_data.get("call_active")
                        and status_data.get("state") == "IDLE"
                    ):
                        logging.info("Call has ended")
                        break

                # Wait before next status check
                time.sleep(1)

            return True

        finally:
            client.disconnect()

    except Exception as e:
        logging.error(f"Error placing call: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # Set up logging to file and console with milliseconds in timestamp
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s.%(msecs)03d %(levelname)-8s [PC] %(message)s",
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

    parser = argparse.ArgumentParser(
        description="Place calls via Modem Manager interface"
    )
    parser.add_argument(
        "-n", "--number", type=str, help="Phone number to dial", default=None
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "-r",
        "--no-audio-routing",
        action="store_true",
        help="Disable audio re-routing (establish call only)",
    )
    parser.add_argument(
        "--modem-host",
        type=str,
        default="localhost",
        help="Modem manager server host (default: localhost)",
    )
    parser.add_argument(
        "--modem-port",
        type=int,
        default=5555,
        help="Modem manager server port (default: 5555)",
    )

    args = parser.parse_args()

    # Load phone numbers from config file
    config = dotenv_values("/mnt/data/K3_config_settings")

    phone_numbers = []

    # If number specified on command line, use it
    if args.number:
        phone_numbers.append(args.number)
    else:
        # Load from config file
        phone_numbers.append(config.get("FIRST_NUMBER", "9723507770"))
        phone_numbers.append(config.get("SECOND_NUMBER", "9727459072"))
        phone_numbers.append(config.get("THIRD_NUMBER", "9723507770"))

    call_success = False

    # Try each number until one succeeds
    for number in phone_numbers:
        logging.info(f"Attempting to dial number: {number}")

        # Parse dial code prefix to determine EDC behavior
        actual_number, send_edc, edc_code = parse_special_dial_code(number)

        if send_edc:
            if edc_code == "DC":
                logging.info("Sending EDC packet with 'DC' code (*54 prefix)")
            else:
                logging.info(
                    "Sending EDC packet with normal code (*55 prefix or default)"
                )
            send_edc_packet(edc_code)
        else:
            logging.info("EDC packet sending disabled for this call (*50 prefix)")

        call_success = place_call_with_client(
            number,
            verbose=args.verbose,
            no_audio_routing=args.no_audio_routing,
            modem_manager_host=args.modem_host,
            modem_manager_port=args.modem_port,
        )

        if call_success:
            logging.info(f"Call to {number} completed successfully")
            break
        else:
            logging.warning(f"Call to {number} failed or timed out")
            # Small delay before trying next number
            if number != phone_numbers[-1]:  # Don't delay after last number
                logging.info("Waiting 2.5 seconds before trying next number...")
                time.sleep(2.5)

    if not call_success:
        logging.error("All call attempts failed")

    # Touch file to indicate completion
    Path("/tmp/setup").touch()

    logging.info("place_call.py exiting")
