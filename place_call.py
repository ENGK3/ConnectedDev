import argparse
import logging
import logging.handlers
import re
import subprocess
import time
from pathlib import Path

import serial

# Import shared modem utilities
from modem_utils import get_modem_info, sbc_cmd, sbc_connect, sbc_disconnect


def get_pactl_sources():
    try:
        # Run the pactl command and capture output
        result = subprocess.run(
            ["pactl", "list", "sources", "short"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("Error running pactl:", result.stderr)
            return []

        interface_numbers = []
        for line in result.stdout.strip().split("\n"):
            parts = line.split("\t")
            if len(parts) >= 2:
                source_name = parts[1]
                match = re.search(
                    r"output.usb-Android_LE910C1-NF_[\w]+-(\d{2})\.", source_name
                )
                if match:
                    interface_numbers.append(match.group(1))
        return interface_numbers

    except Exception as e:
        print("Exception occurred:", e)
        return []


def start_audio_bridge():
    """
    Start the audio bridge using PulseAudio loopback modules.
    Returns a tuple of the module IDs.
    """

    # Figure out the device number for the LE910C1-NF
    interface_number = get_pactl_sources()
    if not interface_number:
        logging.error("No LE910C1-NF audio interfaces found.")
        return (None, None)

    # Setup PulseAudio loopbacks for audio routing

    # LE910C1 → SGTL5000Card
    telit_to_sgtl_cmd = [
        "pactl",
        "load-module",
        "module-loopback",
        f"source=alsa_input.usb-Android_LE910C1-NF_0123456789ABCDEF-{interface_number[0]}.mono-fallback",
        "sink=alsa_output.platform-sound.stereo-fallback",
        "rate=48000",
        "latency_msec=80",
    ]

    # SGTL5000Card → LE910C1
    sgtl_to_telit_cmd = [
        "pactl",
        "load-module",
        "module-loopback",
        "source=alsa_input.platform-sound.stereo-fallback",
        f"sink=alsa_output.usb-Android_LE910C1-NF_0123456789ABCDEF-{interface_number[0]}.mono-fallback",
        "latency_msec=80",
    ]

    # try:
    #     # Start both loopbacks and get their module IDs
    telit_to_sgtl = subprocess.check_output(telit_to_sgtl_cmd).decode().strip()
    logging.info(f"Loopbacks loaded - LE910C1 → SGTL5000Card: {telit_to_sgtl}")

    sgtl_to_telit = subprocess.check_output(sgtl_to_telit_cmd).decode().strip()
    logging.info(f"Loopbacks loaded - SGTL5000Card → LE910C1: {sgtl_to_telit}")

    # except subprocess.CalledProcessError as e:
    #     logging.info(f"Command failed with return code {e.returncode}")
    #     logging.info(f"Command: {e.cmd}")
    #     logging.info(f"Output (if captured): {e.output}")

    return (telit_to_sgtl, sgtl_to_telit)


def terminate_pids(module_ids):
    """
    Unload the PulseAudio loopback modules with the given module IDs.
    """
    for module_id in module_ids:
        try:
            # Get the module list first
            result = subprocess.run(
                ["pactl", "list", "modules", "short"],
                capture_output=True,
                text=True,
                check=True,
            )

            # Check each line for our module ID and loopback
            module_exists = any(
                line.startswith(f"{module_id}\tmodule-loopback")
                for line in result.stdout.splitlines()
            )

            if module_exists:
                subprocess.run(["pactl", "unload-module", str(module_id)], check=True)
                logging.info(f"Unloaded PulseAudio loopback module {module_id}")
            else:
                logging.info(
                    f"Loopback module {module_id} not found or already unloaded"
                )
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to unload loopback module {module_id}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error with loopback module {module_id}: {e}")


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
        "AT+CMER=2,0,0,2\r",  # Enable unsolicited result codes
        "AT#ADSPC=6\r",
        "AT+CIND=0,0,1,0,1,1,1,1,0,1,1\r",
    ]

    for cmd in at_cmd_set:
        sbc_cmd(cmd, serial_connection, verbose)


def sbc_place_call(
    number: str,
    modem: serial.Serial,
    verbose: bool = True,
    no_audio_routing: bool = False,
) -> bool:
    sbc_config_call(modem, verbose)

    # Flush any pending data before dialing
    modem.reset_input_buffer()

    sbc_cmd(f"ATD{number};\r", modem, verbose)  # Place the call
    audio_pids = None
    start_time = time.time()
    timeout = 30  # 30 second timeout
    call_connected = False

    # Set a shorter timeout on the serial port so we can check for overall timeout
    original_timeout = modem.timeout
    modem.timeout = 0.5  # Short timeout for readline to allow timeout checking

    try:
        while True:
            # Check for timeout FIRST
            if (time.time() - start_time > timeout) and call_connected is False:
                logging.warning("Call connection timeout after 30 seconds")
                break

            response = modem.readline().decode().strip()

            # Log ALL responses to see what we're getting
            if response:  # Only log non-empty responses
                logging.info(f"Waiting for call response: {response}")

            if "+CIEV: call,1" in response:
                logging.info("Call connected successfully.")
                if not no_audio_routing:
                    audio_pids = start_audio_bridge()
                    logging.info(f"Audio bridge Module IDs: {audio_pids}")
                else:
                    logging.info("Audio routing disabled - no audio bridge started")
                call_connected = True

            elif "+CIEV: call,0" in response:
                logging.info("Call setup Terminated.")
                break  # Exit the loop but don't return yet

            elif "NO CARRIER" in response:
                logging.info("Call terminated")
                break  # Exit the loop but don't return yet

    finally:
        # Restore original timeout
        modem.timeout = original_timeout

    sbc_cmd("AT+CHUP\r", modem, verbose)
    if audio_pids and not no_audio_routing:
        terminate_pids(audio_pids)
        logging.info("Audio bridge terminated.")
    return call_connected  # Return the connection status after loop exits


if __name__ == "__main__":
    # Set up logging to syslog with milliseconds in timestamp

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

    parser = argparse.ArgumentParser(description="Serial SBC dialer")
    parser.add_argument(
        "-n", "--number", type=str, help="Phone number to dial", default="9723507770"
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
        "-s",
        "--skip-packet",
        action="store_true",
        help="Skip sending TCP packet before call",
    )
    args = parser.parse_args()

    serial_connection = serial.Serial()
    if sbc_connect(serial_connection):
        # Send TCP packet before making the call (unless skipped)
        if not args.skip_packet:
            logging.info("=" * 60)
            logging.info("Retrieving modem information for TCP packet...")
            iccid, imei, imsi = get_modem_info(serial_connection, verbose=args.verbose)

            # logging.info(f"Sending TCP packet to {args.hostname}:{args.port}")
            # error_code, response = send_tcp_packet(
            #     hostname=args.hostname,
            #     port=args.port,
            #     data=event_data,
            #     serial_connection=serial_connection,
            #     timeout=30,
            #     verbose=args.verbose,
            # )

            # if error_code == 0:
            #     logging.info("TCP packet sent successfully!")
            #     logging.info(f"Server response: {response}")
            # else:
            #     logging.error(f"TCP packet send failed with error code: {error_code}")
            #     # Continue with call even if packet send fails
        else:
            logging.info("Skipping TCP packet send (--skip-packet flag set)")

        logging.info(f"Ready to dial number: {args.number}")
        call_success = sbc_place_call(
            args.number,
            serial_connection,
            verbose=args.verbose,
            no_audio_routing=args.no_audio_routing,
        )
        if call_success:
            logging.info("Call completed successfully")
        else:
            logging.warning("Call failed or timed out")

    Path("/tmp/setup").touch()

    sbc_disconnect(serial_connection)
