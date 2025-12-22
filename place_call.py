import argparse
import json
import logging
import logging.handlers
import socket
import sys
import uuid
from pathlib import Path

# TCP server settings (must match manage_modem.py)
DEFAULT_TCP_HOST = "127.0.0.1"
DEFAULT_TCP_PORT = 5555


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
