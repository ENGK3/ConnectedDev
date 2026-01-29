#!/usr/bin/env python3
"""
Monitor baresip via TCP socket interface and handle incoming calls using Modem Manager.

This script connects to baresip's TCP control interface to monitor call events.
When an incoming call is established, it uses the modem_manager_client to place
an outgoing call for audio routing. This version coordinates with the centralized
modem manager instead of calling place_call.py directly.
"""

import argparse
import json
import logging
import re
import socket
import subprocess
import sys
import threading
import time

from dotenv import dotenv_values

# Import modem manager client
from modem_manager_client import ModemManagerClient

# Baresip settings
BARESIP_CMD = "/usr/bin/baresip"
BARESIP_HOST = "localhost"
BARESIP_PORT = 4444  # Default baresip control port

# Modem Manager settings
MODEM_MANAGER_HOST = "localhost"
MODEM_MANAGER_PORT = 5555

# Event types from baresip JSON events
EVENT_CALL_ESTABLISHED = "CALL_ESTABLISHED"
EVENT_CALL_CLOSED = "CALL_CLOSED"
EVENT_CALL_INCOMING = "CALL_INCOMING"
EVENT_CALL_RINGING = "CALL_RINGING"


def send_baresip_command(sock, command, call_id=None, params=None):
    """Send a command to baresip via TCP socket using JSON netstring format

    Baresip expects commands in JSON netstring format:
    <length>:{"command":"<cmd>","id":"<call_id>"},

    Args:
        sock: Socket connection to baresip
        command: Command string to send to baresip (e.g., "hangup", "accept", "dtmf")
        call_id: Optional call ID for commands that target specific calls
        params: Optional parameters for the command (e.g., DTMF digit)

    Returns:
        True if command was sent successfully, False otherwise
    """
    try:
        # Build JSON command object
        cmd_obj = {"command": command}

        # Add call ID if provided
        if call_id:
            cmd_obj["id"] = call_id

        # Add params if provided
        if params:
            cmd_obj["params"] = params

        # Convert to JSON string
        json_cmd = json.dumps(cmd_obj)

        # Format as netstring: <length>:<json>,
        netstring = f"{len(json_cmd)}:{json_cmd},"

        sock.sendall(netstring.encode("utf-8"))
        logging.info(
            f"Sent command to baresip: {json_cmd} (netstring: {repr(netstring)})"
        )
        return True
    except Exception as e:
        logging.error(f"Failed to send command to baresip: {e}")
        return False


def parse_baresip_event(data):
    """Parse baresip JSON event format

    Baresip sends events in format: <length>:<json_data>,
    For example: 269:{"event":true,"type":"CALL_ESTABLISHED",...},

    Args:
        data: String containing one or more baresip events

    Returns:
        Tuple of (list of parsed JSON event dictionaries, remaining unparsed data)
    """
    events = []
    remaining = data

    while remaining:
        # Look for the pattern <number>:{...},
        match = re.match(r"(\d+):", remaining)
        if not match:
            # No more complete events, return what we have
            break

        event_length = int(match.group(1))
        start_pos = len(match.group(0))  # Position after the length prefix

        # Check if we have enough data for the complete event
        if len(remaining) < start_pos + event_length:
            # Incomplete event, return what we've parsed so far
            break

        # Extract the JSON event (length includes everything up to the comma)
        event_data = remaining[start_pos : start_pos + event_length]

        # Remove trailing comma if present
        if event_data.endswith(","):
            event_data = event_data[:-1]

        try:
            event = json.loads(event_data)
            events.append(event)
            logging.debug(f"Parsed event: {event.get('type', 'UNKNOWN')} - {event}")
        except json.JSONDecodeError as e:
            logging.warning(f"Failed to parse JSON event: {e}")
            logging.debug(f"Raw event data: {event_data}")

        # Move to next event
        remaining = remaining[start_pos + event_length :]
        # Skip the comma separator if present
        if remaining.startswith(","):
            remaining = remaining[1:]

    return events, remaining


def connect_to_baresip(host, port, max_retries=10, retry_delay=2):
    """Establish TCP connection to baresip control interface

    Args:
        host: Hostname or IP address of baresip
        port: TCP port number
        max_retries: Maximum number of connection attempts
        retry_delay: Delay in seconds between retry attempts

    Returns:
        Socket object if successful, None otherwise
    """
    for attempt in range(1, max_retries + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)  # 10 second timeout
            sock.connect((host, port))
            logging.info(f"Connected to baresip at {host}:{port}")
            return sock
        except Exception as e:
            logging.warning(f"Connection attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                logging.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logging.error(
                    f"Failed to connect to baresip after {max_retries} attempts"
                )
                return None


def start_baresip(verbose=False):
    """Start baresip as a subprocess

    Args:
        verbose: If True, start baresip with -v flag for verbose output

    Returns:
        Subprocess object if successful, None otherwise
    """
    try:
        cmd = [BARESIP_CMD]
        if verbose:
            cmd.append("-v")
            logging.info(f"Starting baresip in verbose mode: {' '.join(cmd)}")
        else:
            logging.info(f"Starting baresip: {BARESIP_CMD}")

        # Start baresip in the background
        baresip_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
        )

        # Give baresip time to start and initialize TCP interface
        logging.info("Waiting for baresip to initialize...")
        time.sleep(3)

        # Check if process is still running
        if baresip_proc.poll() is not None:
            logging.error("Baresip process terminated unexpectedly during startup")
            return None

        logging.info("Baresip started successfully")
        return baresip_proc

    except FileNotFoundError:
        logging.error(f"Baresip executable not found: {BARESIP_CMD}")
        return None
    except Exception as e:
        logging.error(f"Failed to start baresip: {e}")
        return None


def monitor_baresip_output(proc, stop_event=None, log_file=None):
    """Monitor baresip stdout/stderr in background thread

    Args:
        proc: Baresip subprocess
        stop_event: Threading event to signal when to stop
        log_file: Optional file path to write baresip output to
    """
    file_handle = None
    try:
        if log_file:
            file_handle = open(log_file, "a")
            logging.info(f"Logging baresip output to {log_file}")

        for line in iter(proc.stdout.readline, ""):
            if stop_event and stop_event.is_set():
                break
            if line:
                line = line.strip()
                # Log baresip output at debug level
                if line:
                    logging.debug(f"[BARESIP OUTPUT] {line}")
                    if file_handle:
                        file_handle.write(f"{line}\n")
                        file_handle.flush()
    except Exception as e:
        logging.debug(f"Baresip output monitor stopped: {e}")
    finally:
        if file_handle:
            file_handle.close()


def monitor_modem_notifications(
    modem_manager_host,
    modem_manager_port,
    stop_event,
    incoming_call_callback,
    call_ended_callback=None,
    dtmf_callback=None,
):
    """Monitor modem manager for incoming cellular call notifications.

    Args:
        modem_manager_host: Modem manager host
        modem_manager_port: Modem manager port
        stop_event: Event to signal when to stop
        incoming_call_callback: Function to call when incoming call received
        call_ended_callback: Optional function to call when call ends
        dtmf_callback: Optional function to call when DTMF digit received
    """
    while not stop_event.is_set():
        try:
            # Connect to modem manager
            client = ModemManagerClient(
                modem_manager_host, modem_manager_port, timeout=10.0
            )
            if not client.connect():
                logging.error("Failed to connect to modem manager for notifications")
                time.sleep(5)
                continue

            # Subscribe to notifications
            subscribe_request = {
                "command": "subscribe_notifications",
                "params": {},
                "request_id": f"subscribe-{time.time()}",
            }

            if not client.socket:
                logging.error("No socket connection")
                time.sleep(5)
                continue

            client.socket.sendall((json.dumps(subscribe_request) + "\n").encode())

            # Read subscription response
            response = json.loads(client.socket.recv(4096).decode().strip())
            if response.get("status") != "success":
                logging.error(f"Failed to subscribe: {response.get('message')}")
                client.disconnect()
                time.sleep(5)
                continue

            logging.info("Subscribed to modem manager notifications")

            # Listen for notifications
            while not stop_event.is_set():
                try:
                    if not client.socket:
                        break
                    data = client.socket.recv(4096)
                    if not data:
                        logging.warning("Modem manager notification connection closed")
                        break

                    notification = json.loads(data.decode().strip())

                    if notification.get("type") == "incoming_call":
                        caller_number = notification.get("caller_number")
                        logging.info(
                            f"Received incoming cellular call notification: "
                            f"{caller_number}"
                        )
                        incoming_call_callback(caller_number)

                    elif notification.get("type") == "call_ended":
                        reason = notification.get("reason", "unknown")
                        logging.info(f"Received call ended notification: {reason}")
                        if call_ended_callback:
                            call_ended_callback(reason)

                    elif notification.get("type") == "dtmf_received":
                        digit = notification.get("digit")
                        logging.info(f"Received DTMF notification: {digit}")
                        if dtmf_callback:
                            dtmf_callback(digit)

                except socket.timeout:
                    continue
                except json.JSONDecodeError as e:
                    logging.error(f"Invalid notification JSON: {e}")
                except Exception as e:
                    logging.error(f"Error receiving notification: {e}")
                    break

            client.disconnect()

        except Exception as e:
            logging.error(f"Error in notification monitor: {e}")
            time.sleep(5)


def monitor_baresip_socket(
    sock,
    phone_numbers,
    skip_rerouting=False,
    stop_event=None,
    modem_manager_host=MODEM_MANAGER_HOST,
    modem_manager_port=MODEM_MANAGER_PORT,
):
    """Monitor baresip TCP socket and handle incoming calls using Modem Manager

    Args:
        sock: Socket connection to baresip
        phone_numbers: List of phone numbers to dial for audio routing (tries in order)
        skip_rerouting: If True, skip audio re-routing
        stop_event: Threading event to signal when to stop monitoring
        modem_manager_host: Modem manager server host
        modem_manager_port: Modem manager server port
    """
    call_in_progress = False
    buffer = ""
    current_call_id = None  # Track the current call ID

    def handle_incoming_cellular_call(caller_number):
        """Handle incoming cellular call - make baresip join conference as admin."""
        nonlocal call_in_progress, current_call_id, sock

        if call_in_progress:
            logging.warning(
                f"Cannot handle incoming cellular call from {caller_number} - "
                "VOIP call already in progress"
            )
            return

        logging.info(
            f"Incoming cellular call from {caller_number}, "
            "joining conference as admin..."
        )

        # Make baresip dial extension 9877 to join as admin
        try:
            # Create a fake call ID for tracking
            current_call_id = f"cellular-{time.time()}"
            call_in_progress = True

            # Baresip dial command format:
            # {"command": "dial", "params": "sip:extension@host"}
            sip_uri = "sip:9877@192.168.80.10"

            logging.info(f"Dialing baresip to: {sip_uri}")

            # Build proper dial command with params field
            cmd_obj = {"command": "dial", "params": sip_uri}
            json_cmd = json.dumps(cmd_obj)
            netstring = f"{len(json_cmd)}:{json_cmd},"

            # Send to baresip socket (not modem_manager!)
            data_to_send = netstring.encode("utf-8")
            logging.debug(
                f"Sending to baresip socket (fileno={sock.fileno()}): "
                f"{netstring.strip()}"
            )
            sock.sendall(data_to_send)
            logging.info(
                f"Successfully sent dial command to baresip "
                f"({len(data_to_send)} bytes): {sip_uri}"
            )

        except Exception as e:
            logging.error(f"Error handling incoming cellular call: {e}", exc_info=True)
            call_in_progress = False
            current_call_id = None

    def handle_dtmf_received(digit):
        """Handle DTMF digit received from cellular modem - forward to baresip."""
        nonlocal call_in_progress, current_call_id, sock

        if not call_in_progress or not current_call_id:
            logging.debug(
                f"Received DTMF digit {digit} but no call in progress, ignoring"
            )
            return

        logging.info(
            f"DTMF received from cellular: {digit}, "
            f"forwarding to baresip call {current_call_id}"
        )

        try:
            # Send DTMF to baresip
            ## 3. Send DTMF tones in bash this works like
            # send_cmd '{"command":"sndcode","params":"*5101","token":"dtmf1"}'
            cmd_obj = {"command": "sndcode"}
            cmd_obj["params"] = f"{digit}"
            cmd_obj["token"] = "send_dtmf"

            json_cmd = json.dumps(cmd_obj)
            netstring = f"{len(json_cmd)}:{json_cmd},"

            sock.sendall(netstring.encode("utf-8"))
            logging.info(
                f"Successfully sent DTMF {digit} to baresip (netstring: {netstring})"
            )
        except Exception as e:
            logging.error(f"Error forwarding DTMF to baresip: {e}", exc_info=True)

    def handle_cellular_call_ended(reason):
        """Handle cellular call ended - hangup baresip call."""
        nonlocal call_in_progress, current_call_id, sock

        if not call_in_progress:
            logging.debug(
                f"Received call ended notification but no call in progress: {reason}"
            )
            return

        logging.info(
            f"Cellular call ended ({reason}), hanging up baresip conference call..."
        )

        try:
            # Send hangup command to baresip
            if current_call_id:
                # Use the send_baresip_command helper
                success = send_baresip_command(sock, "hangup", current_call_id)
                if success:
                    logging.info(f"Sent hangup command for call {current_call_id}")
                else:
                    logging.error(
                        f"Failed to send hangup command for call {current_call_id}"
                    )

            # Reset state
            call_in_progress = False
            current_call_id = None

        except Exception as e:
            logging.error(f"Error handling cellular call ended: {e}", exc_info=True)
            call_in_progress = False
            current_call_id = None

    try:
        # Start notification monitor in background thread
        notification_thread = threading.Thread(
            target=monitor_modem_notifications,
            args=(
                modem_manager_host,
                modem_manager_port,
                stop_event,
                handle_incoming_cellular_call,
                handle_cellular_call_ended,
                handle_dtmf_received,
            ),
            daemon=True,
        )
        notification_thread.start()
        logging.info("Started modem notification monitor thread")

        while True:
            if stop_event and stop_event.is_set():
                logging.info("Stop event detected. Exiting monitor loop.")
                break

            try:
                # Receive data from socket
                data = sock.recv(4096)
                if not data:
                    logging.warning("Connection to baresip closed by remote host")
                    break

                # Decode and append to buffer
                buffer += data.decode("utf-8", errors="ignore")

                # Parse any complete events in the buffer
                events, buffer = parse_baresip_event(buffer)

                for event in events:
                    event_type = event.get("type", "UNKNOWN")

                    # Log the event
                    if event_type in [
                        EVENT_CALL_ESTABLISHED,
                        EVENT_CALL_CLOSED,
                        EVENT_CALL_INCOMING,
                        "CALL_OUTGOING",  # Add outgoing call event
                        "CALL_RINGING",  # Add ringing event
                    ]:
                        logging.info(
                            f"[BARESIP EVENT] {event_type}: "
                            f"{event.get('peeruri', 'N/A')} "
                            f"({event.get('peerdisplayname', 'N/A')})"
                        )
                        logging.info(
                            f"[BARESIP EVENT JSON] {json.dumps(event, indent=2)}"
                        )
                    elif event_type == "CALL_RTCP":
                        logging.debug(
                            f"[BARESIP EVENT JSON] {json.dumps(event, indent=2)}"
                        )
                    else:
                        # Log ALL events at INFO level temporarily for debugging
                        logging.info(
                            f"[BARESIP EVENT] {event_type}: {json.dumps(event)}"
                        )

                    # Check for call established
                    if event_type == EVENT_CALL_ESTABLISHED:
                        if call_in_progress:
                            logging.warning(
                                "CALL_ESTABLISHED received but call already in "
                                "progress. Ignoring."
                            )
                            continue

                        # Store the call ID for later use
                        current_call_id = event.get("id")

                        logging.info(
                            f"Call established (ID: {current_call_id}). "
                            f"Routing audio call via Modem Manager..."
                        )
                        call_in_progress = True

                        # Use modem manager client to place call
                        try:
                            client = ModemManagerClient(
                                modem_manager_host, modem_manager_port, timeout=35.0
                            )
                            if not client.connect():
                                logging.error(
                                    "Failed to connect to modem manager. "
                                    "Terminating baresip call."
                                )
                                send_baresip_command(sock, "hangup", current_call_id)
                                call_in_progress = False
                                current_call_id = None
                                continue

                            # Try each phone number until one succeeds
                            call_success = False

                            for number in phone_numbers:
                                logging.info(
                                    f"Requesting modem manager to place call"
                                    f" to {number}"
                                )
                                response = client.place_call(number, skip_rerouting)

                                logging.info(
                                    f"Modem manager response: {response.get('status')}"
                                    f" - {response.get('message')}"
                                )

                                # Handle response based on status
                                if response.get("status") == "error":
                                    # Modem is busy or error occurred
                                    logging.warning(
                                        f"Call placement to {number} failed: "
                                        f"{response.get('message')}"
                                    )
                                    # Try next number if available
                                    if number != phone_numbers[-1]:
                                        logging.info(
                                            "Waiting 2.5 seconds before trying next"
                                            " number..."
                                        )
                                        time.sleep(2.5)
                                        continue
                                    else:
                                        # Last number failed, give up
                                        logging.error("All call attempts failed")
                                        # Terminate baresip call since we can't
                                        # route audio
                                        send_baresip_command(
                                            sock, "hangup", current_call_id
                                        )
                                        call_in_progress = False
                                        current_call_id = None
                                        client.disconnect()
                                        break

                                # Wait for final response if pending or success
                                if response.get("status") == "pending":
                                    logging.info(
                                        "Call placement pending, waiting for"
                                        " completion..."
                                    )
                                    # The response will come asynchronously
                                    if client.socket:
                                        final_response = json.loads(
                                            client.socket.recv(4096).decode().strip()
                                        )
                                        status = final_response.get("status")
                                        msg = final_response.get("message")
                                        logging.info(
                                            f"Final response: {status} - {msg}"
                                        )

                                        if final_response.get("status") == "success":
                                            logging.info(
                                                "Audio routing call completed "
                                                "successfully"
                                            )
                                            call_success = True
                                            break
                                        else:
                                            logging.warning(
                                                f"Audio routing call to {number} "
                                                f"failed: "
                                                f"{final_response.get('message')}"
                                            )

                                elif response.get("status") == "success":
                                    logging.info(
                                        f"Audio routing call to {number} completed"
                                        " successfully"
                                    )
                                    call_success = True
                                    break  # Success, exit the retry loop

                            # If no call succeeded after trying all numbers
                            if not call_success:
                                logging.error(
                                    "Failed to establish call with any"
                                    " configured number"
                                )
                                send_baresip_command(sock, "hangup", current_call_id)
                                call_in_progress = False
                                current_call_id = None
                                client.disconnect()
                                continue

                            # Disconnect the call placement client
                            client.disconnect()

                            logging.info(
                                "Both calls are now active. "
                                "Monitoring for call termination..."
                            )

                            # Start monitoring modem call status in background
                            def monitor_modem_call(
                                modem_host,
                                modem_port,
                                sock_ref,
                                call_id_ref,
                            ):
                                """Monitor modem call and hang up baresip"""
                                monitor_client = None
                                try:
                                    # Create new client for monitoring
                                    monitor_client = ModemManagerClient(
                                        modem_host, modem_port, timeout=5.0
                                    )
                                    if not monitor_client.connect():
                                        logging.error(
                                            "Monitor thread: Failed to connect"
                                        )
                                        return

                                    logging.info(
                                        "Monitor thread started, polling every 2s"
                                    )

                                    while True:
                                        time.sleep(2)  # Poll every 2 seconds

                                        # Check modem status
                                        try:
                                            status_response = (
                                                monitor_client.get_status()
                                            )
                                            call_active = status_response.get(
                                                "data", {}
                                            ).get("call_active", False)

                                            logging.debug(
                                                f"Monitor poll: "
                                                f"call_active={call_active}"
                                            )

                                            if not call_active:
                                                logging.info(
                                                    "Modem call ended, "
                                                    "terminating baresip call"
                                                )
                                                send_baresip_command(
                                                    sock_ref, "hangup", call_id_ref
                                                )
                                                break
                                        except Exception as e:
                                            logging.error(
                                                f"Error checking modem status: {e}",
                                                exc_info=True,
                                            )
                                            break

                                    if monitor_client:
                                        monitor_client.disconnect()
                                        logging.info("Monitor thread disconnected")
                                except Exception as e:
                                    logging.error(
                                        f"Error in modem call monitor: {e}",
                                        exc_info=True,
                                    )
                                finally:
                                    if monitor_client:
                                        try:
                                            monitor_client.disconnect()
                                        except Exception:
                                            pass

                            # Start monitoring thread with captured values
                            monitor_thread = threading.Thread(
                                target=monitor_modem_call,
                                args=(
                                    modem_manager_host,
                                    modem_manager_port,
                                    sock,
                                    current_call_id,
                                ),
                                daemon=True,
                            )
                            monitor_thread.start()

                        except Exception as e:
                            logging.error(
                                f"Error communicating with modem manager: {e}",
                                exc_info=True,
                            )
                            # On error, clean up
                            send_baresip_command(sock, "hangup", current_call_id)
                            call_in_progress = False
                            current_call_id = None

                    # Check for call closed/terminated
                    elif event_type == EVENT_CALL_CLOSED:
                        closed_call_id = event.get("id")
                        logging.info(
                            f"Call closed event received (ID: {closed_call_id})"
                        )

                        if call_in_progress:
                            logging.info(
                                "VOIP call closed while modem call in progress. "
                                "Hanging up modem call..."
                            )

                            # Tell modem manager to hang up
                            try:
                                hangup_client = ModemManagerClient(
                                    modem_manager_host, modem_manager_port, timeout=5.0
                                )
                                if hangup_client.connect():
                                    hangup_response = hangup_client.hangup()
                                    logging.info(
                                        f"Modem hangup response: "
                                        f"{hangup_response.get('status')}"
                                    )
                                    hangup_client.disconnect()
                            except Exception as e:
                                logging.error(f"Error hanging up modem call: {e}")

                            call_in_progress = False
                            current_call_id = None

                        logging.info(
                            "Call terminated. Waiting for next incoming call..."
                        )

            except socket.timeout:
                # Timeout is normal, just continue
                continue
            except Exception as e:
                logging.error(f"Error reading from socket: {e}")
                break

    except Exception as e:
        logging.error(f"Exception in monitor loop: {e}")


def main():
    """Main function to parse arguments and start monitoring"""
    parser = argparse.ArgumentParser(
        description="Monitor Baresip and route audio calls via Modem Manager"
    )
    parser.add_argument(
        "-n",
        "--number",
        default=None,
        help="Phone number to dial (overrides config file)",
    )
    parser.add_argument(
        "-r",
        "--skip-rerouting",
        action="store_true",
        help="Skip audio re-routing",
    )
    parser.add_argument(
        "--modem-host",
        default=MODEM_MANAGER_HOST,
        help=f"Modem manager host (default: {MODEM_MANAGER_HOST})",
    )
    parser.add_argument(
        "--modem-port",
        type=int,
        default=MODEM_MANAGER_PORT,
        help=f"Modem manager port (default: {MODEM_MANAGER_PORT})",
    )
    parser.add_argument(
        "--log-baresip",
        action="store_true",
        default=False,
        help="Start baresip in verbose mode and log output to baresip.log",
    )
    args = parser.parse_args()

    # Load phone numbers from config file
    phone_numbers = []
    if args.number:
        # Command line overrides config file
        phone_numbers.append(args.number)
        logging.info("Using phone number from command line")
    else:
        # Load from config file
        config = dotenv_values("/mnt/data/K3_config_settings")
        phone_numbers.append(config.get("FIRST_NUMBER", "9723507770"))
        phone_numbers.append(config.get("SECOND_NUMBER", "9727459072"))
        phone_numbers.append(config.get("THIRD_NUMBER", "9723507770"))
        logging.info("Using phone numbers from config file")

    logging.info("Starting Baresip call monitor (using Modem Manager)")
    logging.info(f"Will dial numbers: {', '.join(phone_numbers)}")
    logging.info(f"Modem Manager: {args.modem_host}:{args.modem_port}")
    if args.skip_rerouting:
        logging.info("Audio re-routing will be skipped")
    logging.info("Press Ctrl+C to exit.")

    stop_event = threading.Event()
    sock = None
    baresip_proc = None
    output_thread = None

    try:
        # Start baresip
        baresip_proc = start_baresip(verbose=args.log_baresip)
        if not baresip_proc:
            logging.error("Failed to start baresip. Exiting.")
            sys.exit(1)

        # Start background thread to monitor baresip output
        log_file = "/mnt/data/baresip.log" if args.log_baresip else None
        output_thread = threading.Thread(
            target=monitor_baresip_output,
            args=(baresip_proc, stop_event, log_file),
            daemon=True,
        )
        output_thread.start()

        # Connect to baresip TCP interface
        sock = connect_to_baresip(BARESIP_HOST, BARESIP_PORT)
        if not sock:
            logging.error("Failed to connect to baresip TCP interface. Exiting.")
            sys.exit(1)

        # Start monitoring in main thread
        monitor_baresip_socket(
            sock,
            phone_numbers,
            args.skip_rerouting,
            stop_event,
            args.modem_host,
            args.modem_port,
        )

    except KeyboardInterrupt:
        logging.info("Ctrl+C detected. Shutting down...")
        stop_event.set()

    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)

    finally:
        # Clean up socket connection
        if sock:
            try:
                sock.close()
                logging.info("Closed connection to baresip.")
            except Exception as e:
                logging.warning(f"Error closing socket: {e}")

        # Terminate baresip process
        if baresip_proc:
            try:
                logging.info("Terminating baresip process...")
                if baresip_proc.stdin:
                    baresip_proc.stdin.close()
                baresip_proc.terminate()
                try:
                    baresip_proc.wait(timeout=5)
                    logging.info("Baresip process terminated gracefully.")
                except subprocess.TimeoutExpired:
                    logging.warning("Baresip did not terminate, killing it...")
                    baresip_proc.kill()
                    baresip_proc.wait()
            except Exception as e:
                logging.warning(f"Error terminating baresip: {e}")

        logging.info("Shutdown complete.")


if __name__ == "__main__":
    # Set up logging to file and console with milliseconds in timestamp
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(levelname)-8s [VOIP] %(message)s",
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
