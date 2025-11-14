#!/usr/bin/env python3
"""
Modem Manager Client Library

Provides a Python client interface for communicating with the manage_modem.py
TCP server. This library simplifies sending commands and receiving responses.
"""

import json
import logging
import socket
import time
from typing import Any, Dict, Optional


class ModemManagerClient:
    """Client for communicating with Modem Manager TCP server."""

    def __init__(
        self, host: str = "localhost", port: int = 5555, timeout: float = 30.0
    ):
        """
        Initialize the client.

        Args:
            host: Server hostname or IP address
            port: Server TCP port
            timeout: Socket timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket = None

    def connect(self) -> bool:
        """
        Connect to the modem manager server.

        Returns:
            True if connected successfully, False otherwise
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            logging.info(f"Connected to modem manager at {self.host}:{self.port}")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to modem manager: {e}")
            self.socket = None
            return False

    def disconnect(self):
        """Disconnect from the server."""
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logging.warning(f"Error closing socket: {e}")
            finally:
                self.socket = None
                logging.info("Disconnected from modem manager")

    def _send_command(
        self, command: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a command to the server and receive response.

        Args:
            command: Command name (e.g., "place_call", "hangup", "status")
            params: Optional command parameters

        Returns:
            Response dictionary from server

        Raises:
            ConnectionError: If not connected or connection fails
            TimeoutError: If request times out
            ValueError: If response is invalid JSON
        """
        if not self.socket:
            raise ConnectionError("Not connected to modem manager")

        # Generate request ID
        request_id = f"{command}-{time.time()}"

        # Build request
        request = {
            "command": command,
            "params": params or {},
            "request_id": request_id,
        }

        try:
            # Send request
            message = json.dumps(request) + "\n"
            self.socket.sendall(message.encode())
            logging.debug(f"Sent command: {command} (request_id: {request_id})")

            # Receive response
            response_data = self.socket.recv(4096)
            if not response_data:
                raise ConnectionError("Connection closed by server")

            # Parse response
            response = json.loads(response_data.decode().strip())
            logging.debug(f"Received response: {response}")

            return response

        except socket.timeout as e:
            raise TimeoutError(
                f"Command '{command}' timed out after {self.timeout}s"
            ) from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}") from e
        except Exception as e:
            logging.error(f"Error sending command: {e}")
            raise

    def place_call(
        self, number: str, no_audio_routing: bool = False
    ) -> Dict[str, Any]:
        """
        Place an outgoing call.

        Args:
            number: Phone number to dial
            no_audio_routing: If True, skip audio routing setup

        Returns:
            Response dictionary with status and call information

        Example:
            >>> client = ModemManagerClient()
            >>> client.connect()
            >>> response = client.place_call("+19723507770")
            >>> print(response["status"])  # "pending" or "success"
        """
        params = {"number": number, "no_audio_routing": no_audio_routing}
        return self._send_command("place_call", params)

    def hangup(self) -> Dict[str, Any]:
        """
        Hang up the active call.

        Returns:
            Response dictionary with status

        Example:
            >>> client = ModemManagerClient()
            >>> client.connect()
            >>> response = client.hangup()
            >>> print(response["message"])
        """
        return self._send_command("hangup")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current modem status.

        Returns:
            Response dictionary with modem state and call information

        Example:
            >>> client = ModemManagerClient()
            >>> client.connect()
            >>> response = client.get_status()
            >>> print(response["data"]["state"])  # "IDLE", "CALL_ACTIVE", etc.
            >>> print(response["data"]["call_active"])  # True/False
        """
        return self._send_command("status")

    def shutdown(self) -> Dict[str, Any]:
        """
        Request server shutdown.

        Returns:
            Response dictionary confirming shutdown

        Example:
            >>> client = ModemManagerClient()
            >>> client.connect()
            >>> response = client.shutdown()
            >>> client.disconnect()
        """
        return self._send_command("shutdown")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


def send_command_simple(
    host: str, port: int, command: str, params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Simple one-shot command sender (creates new connection for each call).

    Args:
        host: Server hostname or IP
        port: Server port
        command: Command to send
        params: Optional command parameters

    Returns:
        Response dictionary

    Example:
        >>> response = send_command_simple("localhost", 5555, "status")
        >>> print(response["data"]["state"])
    """
    with ModemManagerClient(host, port) as client:
        return client._send_command(command, params)


# Convenience functions
def place_call_simple(
    number: str,
    no_audio_routing: bool = False,
    host: str = "localhost",
    port: int = 5555,
) -> Dict[str, Any]:
    """
    Simple function to place a call (one-shot connection).

    Args:
        number: Phone number to dial
        no_audio_routing: If True, skip audio routing setup
        host: Server hostname
        port: Server port

    Returns:
        Response dictionary
    """
    return send_command_simple(
        host,
        port,
        "place_call",
        {"number": number, "no_audio_routing": no_audio_routing},
    )


def get_status_simple(host: str = "localhost", port: int = 5555) -> Dict[str, Any]:
    """
    Simple function to get status (one-shot connection).

    Args:
        host: Server hostname
        port: Server port

    Returns:
        Response dictionary with status data
    """
    return send_command_simple(host, port, "status")


def hangup_simple(host: str = "localhost", port: int = 5555) -> Dict[str, Any]:
    """
    Simple function to hang up (one-shot connection).

    Args:
        host: Server hostname
        port: Server port

    Returns:
        Response dictionary
    """
    return send_command_simple(host, port, "hangup")


# CLI interface for testing
if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="Modem Manager Client - Send commands to modem manager server"
    )
    parser.add_argument(
        "--host", type=str, default="localhost", help="Server host (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=5555, help="Server port (default: 5555)"
    )
    parser.add_argument(
        "--timeout", type=float, default=30.0, help="Socket timeout in seconds"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # place_call command
    place_parser = subparsers.add_parser("place_call", help="Place an outgoing call")
    place_parser.add_argument("number", type=str, help="Phone number to dial")
    place_parser.add_argument(
        "-r",
        "--no-audio-routing",
        action="store_true",
        help="Skip audio routing setup",
    )

    # hangup command
    subparsers.add_parser("hangup", help="Hang up active call")

    # status command
    subparsers.add_parser("status", help="Get modem status")

    # shutdown command
    subparsers.add_parser("shutdown", help="Shutdown the server")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        client = ModemManagerClient(args.host, args.port, args.timeout)

        if not client.connect():
            logging.error("Failed to connect to server")
            sys.exit(1)

        # Execute command
        if args.command == "place_call":
            response = client.place_call(args.number, args.no_audio_routing)
        elif args.command == "hangup":
            response = client.hangup()
        elif args.command == "status":
            response = client.get_status()
        elif args.command == "shutdown":
            response = client.shutdown()
        else:
            logging.error(f"Unknown command: {args.command}")
            sys.exit(1)

        # Print response
        print("\n" + "=" * 60)
        print(f"Response Status: {response.get('status', 'UNKNOWN')}")
        print(f"Message: {response.get('message', '')}")
        if "data" in response:
            print("\nData:")
            print(json.dumps(response["data"], indent=2))
        print("=" * 60 + "\n")

        client.disconnect()

        # Exit with appropriate code
        sys.exit(0 if response.get("status") == "success" else 1)

    except KeyboardInterrupt:
        logging.info("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
