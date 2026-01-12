#!/usr/bin/env python3
"""
DTMF Collector - Collects DTMF tones from manage_modem and groups them into commands.

This script connects to manage_modem's TCP socket, subscribes to notifications,
and collects DTMF tones. If there's a gap of more than 3 seconds between tones,
the next tone starts a new command.
"""

import argparse
import json
import logging
import socket
import sys
import time
from typing import Optional

# Default connection settings
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5555
DTMF_TIMEOUT = 3.0  # seconds between tones to consider new command


class DTMFCollector:
    """Collects and processes DTMF tones from manage_modem."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: float = DTMF_TIMEOUT,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self.current_command = ""
        self.last_dtmf_time: Optional[float] = None
        self.connected = False

    def connect(self) -> bool:
        """Connect to manage_modem TCP server."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10.0)

            logging.info(f"Connecting to manage_modem at {self.host}:{self.port}")
            self.sock.connect((self.host, self.port))
            logging.info("Connected to manage_modem")

            self.connected = True
            return True
        except ConnectionRefusedError:
            logging.error(
                f"Could not connect to manage_modem at {self.host}:{self.port}"
            )
            logging.error("Make sure manage_modem.py is running")
            return False
        except socket.timeout:
            logging.error("Connection timed out")
            return False
        except Exception as e:
            logging.error(f"Error connecting: {e}")
            return False

    def subscribe_notifications(self) -> bool:
        """Subscribe to incoming call and DTMF notifications."""
        if not self.sock:
            logging.error("Not connected")
            return False

        try:
            # Send subscribe_notifications command
            request = {
                "command": "subscribe_notifications",
                "request_id": f"dtmf-collector-{time.time()}",
            }

            message = json.dumps(request) + "\n"
            self.sock.sendall(message.encode())
            logging.info("Sent subscription request")

            # Wait for response
            data = self.sock.recv(4096)
            if not data:
                logging.error("Connection closed by server")
                return False

            response = json.loads(data.decode().strip())
            status = response.get("status")

            if status == "success":
                logging.info("Successfully subscribed to notifications")
                return True
            else:
                logging.error(f"Subscription failed: {response.get('message')}")
                return False

        except Exception as e:
            logging.error(f"Error subscribing: {e}")
            return False

    def process_dtmf(self, digit: str) -> None:
        """Process a DTMF digit and handle command grouping."""
        current_time = time.time()

        # Check if this is the start of a new command
        if self.last_dtmf_time is None:
            # First DTMF digit ever
            logging.info("Started collecting DTMF command")
            self.current_command = digit
        elif (current_time - self.last_dtmf_time) > self.timeout:
            # Timeout occurred - complete previous command and start new one
            if self.current_command:
                self.handle_command(self.current_command)

            logging.info("Started new DTMF command (timeout)")
            self.current_command = digit
        else:
            # Continue building current command
            self.current_command += digit

        self.last_dtmf_time = current_time
        logging.info(f"DTMF digit: {digit}, Current command: {self.current_command}")

    def handle_command(self, command: str) -> None:
        """
        Handle a completed DTMF command.

        Override this method to implement custom command processing.
        """
        logging.info("=" * 60)
        logging.info(f"DTMF COMMAND COMPLETE: {command}")
        logging.info("=" * 60)

        # Example command processing - extend this as needed
        if command == "1":
            logging.info("Command: Option 1")
        elif command == "2":
            logging.info("Command: Option 2")
        elif command.startswith("*"):
            logging.info(f"Command: Star code {command}")
        elif command.startswith("#"):
            logging.info(f"Command: Pound code {command}")
        else:
            logging.info(f"Command: Unknown - {command}")

    def check_timeout(self) -> None:
        """Check if current command has timed out and should be processed."""
        if self.last_dtmf_time is None or not self.current_command:
            return

        current_time = time.time()
        if (current_time - self.last_dtmf_time) > self.timeout:
            # Command has timed out - process it
            self.handle_command(self.current_command)
            self.current_command = ""
            self.last_dtmf_time = None

    def listen(self) -> None:
        """Listen for notifications from manage_modem."""
        if not self.sock:
            logging.error("Not connected")
            return

        logging.info("Listening for DTMF notifications...")
        logging.info(f"DTMF timeout: {self.timeout} seconds")

        # Set a shorter timeout to allow checking for command timeouts
        self.sock.settimeout(0.5)

        buffer = ""

        try:
            while True:
                try:
                    # Check if current command has timed out
                    self.check_timeout()

                    # Try to receive data
                    data = self.sock.recv(4096)
                    if not data:
                        logging.warning("Connection closed by server")
                        break

                    # Add to buffer and process complete lines
                    buffer += data.decode()

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()

                        if not line:
                            continue

                        try:
                            notification = json.loads(line)
                            self.handle_notification(notification)
                        except json.JSONDecodeError as e:
                            logging.error(f"Failed to parse notification: {e}")
                            logging.error(f"Raw data: {line}")

                except socket.timeout:
                    # This is normal - continue checking for timeouts
                    continue

        except KeyboardInterrupt:
            logging.info("Interrupted by user")
        except Exception as e:
            logging.error(f"Error in listen loop: {e}", exc_info=True)
        finally:
            # Process any remaining command
            if self.current_command:
                self.handle_command(self.current_command)

    def handle_notification(self, notification: dict) -> None:
        """Handle a notification from manage_modem."""
        notif_type = notification.get("type")
        timestamp = notification.get("timestamp")

        if notif_type == "dtmf_received":
            digit = notification.get("digit")
            logging.debug(f"[{timestamp}] DTMF received: {digit}")
            self.process_dtmf(digit)

        elif notif_type == "incoming_call":
            caller = notification.get("caller_number")
            logging.info(f"[{timestamp}] Incoming call from: {caller}")

        elif notif_type == "call_ended":
            reason = notification.get("reason")
            logging.info(f"[{timestamp}] Call ended: {reason}")

            # Process any pending command when call ends
            if self.current_command:
                self.handle_command(self.current_command)
                self.current_command = ""
                self.last_dtmf_time = None

        else:
            logging.debug(f"[{timestamp}] Unknown notification type: {notif_type}")

    def disconnect(self) -> None:
        """Disconnect from manage_modem."""
        if self.sock:
            try:
                self.sock.close()
                logging.info("Disconnected from manage_modem")
            except Exception as e:
                logging.error(f"Error disconnecting: {e}")
            finally:
                self.sock = None
                self.connected = False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DTMF Collector - Collect and process DTMF tones from manage_modem"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=DEFAULT_HOST,
        help=f"TCP server host (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"TCP server port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DTMF_TIMEOUT,
        help=f"Timeout between DTMF tones in seconds (default: {DTMF_TIMEOUT})",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Log file path (default: console only)",
    )

    args = parser.parse_args()

    # Setup logging
    handlers = [logging.StreamHandler(sys.stdout)]
    if args.log_file:
        handlers.append(logging.FileHandler(args.log_file))

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s",
        datefmt="%m-%d %H:%M:%S",
        handlers=handlers,
    )

    logging.info("=" * 60)
    logging.info("DTMF Collector Starting")
    logging.info(f"Server: {args.host}:{args.port}")
    logging.info(f"DTMF Timeout: {args.timeout} seconds")
    logging.info("=" * 60)

    # Create collector and connect
    collector = DTMFCollector(args.host, args.port, args.timeout)

    try:
        if not collector.connect():
            sys.exit(1)

        if not collector.subscribe_notifications():
            sys.exit(1)

        collector.listen()

    except KeyboardInterrupt:
        logging.info("Interrupted by user (Ctrl+C)")
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
    finally:
        collector.disconnect()
        logging.info("DTMF Collector stopped")


if __name__ == "__main__":
    main()
