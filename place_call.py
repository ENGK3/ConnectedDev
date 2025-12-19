import argparse
import json
import logging
import logging.handlers
import re
import socket
import subprocess
import sys
import uuid
from pathlib import Path

# TCP server settings (must match manage_modem.py)
DEFAULT_TCP_HOST = "127.0.0.1"
DEFAULT_TCP_PORT = 5555


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


def place_call_via_tcp(
    number: str,
    host: str = DEFAULT_TCP_HOST,
    port: int = DEFAULT_TCP_PORT,
) -> bool:
    """
    Place a call using the manage_modem.py TCP interface.
    Audio routing is always enabled.

    Args:
        number: Phone number to dial
        host: TCP server host
        port: TCP server port

    Returns:
        True if call was successfully connected, False otherwise
    """
    try:
        # Connect to manage_modem TCP server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(60.0)  # 60 second timeout

        logging.info(f"Connecting to modem manager at {host}:{port}")
        sock.connect((host, port))
        logging.info("Connected to modem manager")

        # Create place_call command
        request_id = str(uuid.uuid4())
        command = {
            "command": "place_call",
            "params": {
                "number": number,
                "no_audio_routing": False,  # Always enable audio routing
            },
            "request_id": request_id,
        }

        # Send command
        logging.info(f"Sending place_call command for {number}")
        sock.sendall((json.dumps(command) + "\n").encode())

        # Wait for responses
        call_connected = False

        while True:
            # Receive response
            data = sock.recv(4096)
            if not data:
                logging.warning("Connection closed by server")
                break

            # Parse response
            try:
                response_text = data.decode().strip()
                response = json.loads(response_text)

                status = response.get("status")
                message = response.get("message")
                response_request_id = response.get("request_id")

                # Verify this is our response
                if response_request_id != request_id:
                    logging.warning(
                        f"Received response for different request: "
                        f"{response_request_id}"
                    )
                    continue

                logging.info(f"Response: status={status}, message={message}")

                if status == "pending":
                    # Initial response - call is being placed
                    logging.info("Call placement initiated, waiting for completion...")

                elif status == "success":
                    # Call succeeded
                    data_obj = response.get("data", {})
                    call_connected = data_obj.get("call_connected", False)

                    if call_connected:
                        logging.info("Call connected successfully")
                        # Call is active - wait for it to end
                        logging.info("Call is active, waiting for termination...")
                    else:
                        logging.warning("Success response but call not connected")
                        break

                elif status == "error":
                    # Call failed
                    logging.error(f"Call failed: {message}")
                    break

            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON response: {e}")
                logging.error(f"Raw data: {data}")
                break

        sock.close()
        return call_connected

    except socket.timeout:
        logging.error("Connection to modem manager timed out")
        return False
    except ConnectionRefusedError:
        logging.error(f"Could not connect to modem manager at {host}:{port}")
        logging.error("Make sure manage_modem.py is running")
        return False
    except Exception as e:
        logging.error(f"Error placing call via TCP: {e}", exc_info=True)
        return False


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

    parser = argparse.ArgumentParser(
        description="Place call via manage_modem.py TCP interface"
    )
    parser.add_argument(
        "-n", "--number", type=str, help="Phone number to dial", default="9723507770"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=DEFAULT_TCP_HOST,
        help=f"TCP server host (default: {DEFAULT_TCP_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_TCP_PORT,
        help=f"TCP server port (default: {DEFAULT_TCP_PORT})",
    )

    args = parser.parse_args()

    logging.info(f"Ready to dial number: {args.number}")
    logging.info("Audio routing will be enabled for this call")
    call_success = place_call_via_tcp(
        args.number,
        host=args.host,
        port=args.port,
    )

    if call_success:
        logging.info("Call completed successfully")
        Path("/tmp/setup").touch()
        sys.exit(0)
    else:
        logging.warning("Call failed or timed out")
        sys.exit(1)
