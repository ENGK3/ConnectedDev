#!/usr/bin/env python3
"""
Monitor baresip via TCP socket interface and handle incoming calls.

This script connects to baresip's TCP control interface to monitor call events.
When an incoming call is established, it launches place_call.py to handle
the audio routing. After place_call.py completes, the incoming call is terminated.
"""

import socket
import subprocess
import threading
import re
import time
import logging
import argparse
import sys
import json
from pathlib import Path

# Baresip TCP control interface settings
BARESIP_HOST = "localhost"
BARESIP_PORT = 4444  # Default baresip control port

# Event types from baresip JSON events
EVENT_CALL_ESTABLISHED = "CALL_ESTABLISHED"
EVENT_CALL_CLOSED = "CALL_CLOSED"
EVENT_CALL_INCOMING = "CALL_INCOMING"
EVENT_CALL_RINGING = "CALL_RINGING"


def get_audio_routing_cmd(phone_number, skip_rerouting=False):
    """Construct the audio routing command with the given phone number

    Args:
        phone_number: Phone number to dial
        skip_rerouting: If True, adds -r flag to skip audio re-routing

    Returns:
        List of command arguments for subprocess
    """
    cmd = ["/usr/bin/python3", "/mnt/data/place_call.py", "-n", phone_number, "-v"]
    if skip_rerouting:
        cmd.append("-r")
    return cmd


def send_baresip_command(sock, command, call_id=None):
    """Send a command to baresip via TCP socket using JSON netstring format

    Baresip expects commands in JSON netstring format:
    <length>:{"command":"<cmd>","id":"<call_id>"},

    Args:
        sock: Socket connection to baresip
        command: Command string to send to baresip (e.g., "hangup", "accept")
        call_id: Optional call ID for commands that target specific calls

    Returns:
        True if command was sent successfully, False otherwise
    """
    try:
        # Build JSON command object
        cmd_obj = {
            "command": command
        }

        # Add call ID if provided
        if call_id:
            cmd_obj["id"] = call_id

        # Convert to JSON string
        json_cmd = json.dumps(cmd_obj)

        # Format as netstring: <length>:<json>,
        netstring = f"{len(json_cmd)}:{json_cmd},"

        sock.sendall(netstring.encode('utf-8'))
        logging.info(f"Sent command to baresip: {json_cmd} (netstring: {repr(netstring)})")
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
        match = re.match(r'(\d+):', remaining)
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
        event_data = remaining[start_pos:start_pos + event_length]

        # Remove trailing comma if present
        if event_data.endswith(','):
            event_data = event_data[:-1]

        try:
            event = json.loads(event_data)
            events.append(event)
            logging.debug(f"Parsed event: {event.get('type', 'UNKNOWN')} - {event}")
        except json.JSONDecodeError as e:
            logging.warning(f"Failed to parse JSON event: {e}")
            logging.debug(f"Raw event data: {event_data}")

        # Move to next event
        remaining = remaining[start_pos + event_length:]
        # Skip the comma separator if present
        if remaining.startswith(','):
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
                logging.error(f"Failed to connect to baresip after {max_retries} attempts")
                return None


def monitor_baresip_socket(sock, phone_number, skip_rerouting=False, stop_event=None):
    """Monitor baresip TCP socket and handle incoming calls

    Args:
        sock: Socket connection to baresip
        phone_number: Phone number to dial for audio routing
        skip_rerouting: If True, skip audio re-routing
        stop_event: Threading event to signal when to stop monitoring
    """
    call_in_progress = False
    audio_proc = None
    buffer = ""
    current_call_id = None  # Track the current call ID

    try:
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
                buffer += data.decode('utf-8', errors='ignore')

                # Parse any complete events in the buffer
                # Events are in format: <length>:{JSON},
                # We need to process them as they arrive
                events, buffer = parse_baresip_event(buffer)

                for event in events:
                    event_type = event.get('type', 'UNKNOWN')

                    # Log the event at INFO level for important events, DEBUG for others
                    if event_type in [EVENT_CALL_ESTABLISHED, EVENT_CALL_CLOSED, EVENT_CALL_INCOMING]:
                        logging.info(f"[BARESIP EVENT] {event_type}: {event.get('peeruri', 'N/A')} "
                                   f"({event.get('peerdisplayname', 'N/A')})")
                        # Print full JSON event for call state changes
                        logging.info(f"[BARESIP EVENT JSON] {json.dumps(event, indent=2)}")
                    else:
                        logging.debug(f"[BARESIP EVENT] {event_type}")

                    # Check for call established
                    if event_type == EVENT_CALL_ESTABLISHED:
                        if call_in_progress:
                            logging.warning("CALL_ESTABLISHED received but call already in progress. Ignoring.")
                            continue

                        # Store the call ID for later use
                        current_call_id = event.get('id')
                        logging.info(f"Call established (ID: {current_call_id}). Routing audio call...")
                        call_in_progress = True

                        # Launch place_call.py
                        audio_cmd = get_audio_routing_cmd(phone_number, skip_rerouting)
                        logging.info(f"Executing: {' '.join(audio_cmd)}")
                        audio_proc = subprocess.Popen(
                            audio_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )

                        # Wait for place_call.py to complete
                        logging.info("Waiting for place_call.py to complete...")
                        returncode = audio_proc.wait()

                        # Capture and log stdout and stderr
                        stdout_output = ""
                        stderr_output = ""
                        if audio_proc.stdout:
                            stdout_output = audio_proc.stdout.read()
                        if audio_proc.stderr:
                            stderr_output = audio_proc.stderr.read()

                        if returncode == 0:
                            logging.info("place_call.py completed successfully.")
                            if stdout_output:
                                logging.info(f"place_call.py stdout:\n{stdout_output}")
                        else:
                            logging.warning(f"place_call.py exited with code {returncode}")
                            if stdout_output:
                                logging.warning(f"place_call.py stdout:\n{stdout_output}")
                            if stderr_output:
                                logging.error(f"place_call.py stderr:\n{stderr_output}")

                        # Terminate the baresip call now that place_call.py is done
                        logging.info(f"Terminating baresip call (ID: {current_call_id})...")
                        # Send hangup command with call ID
                        send_baresip_command(sock, "hangup", current_call_id)
                        time.sleep(1)  # Give some time for the hangup to process

                        call_in_progress = False
                        audio_proc = None
                        current_call_id = None

                        logging.info("Ready for next incoming call...")

                    # Check for call closed/terminated
                    elif event_type == EVENT_CALL_CLOSED:
                        closed_call_id = event.get('id')
                        logging.info(f"Call closed event received (ID: {closed_call_id})")

                        if call_in_progress:
                            logging.info("Call closed detected while call was in progress.")
                            # Terminate audio routing if still running
                            if audio_proc and audio_proc.poll() is None:
                                logging.info("Terminating audio routing process...")
                                audio_proc.terminate()
                                try:
                                    audio_proc.wait(timeout=3)
                                except subprocess.TimeoutExpired:
                                    logging.warning("Audio process did not terminate, killing it...")
                                    audio_proc.kill()
                            call_in_progress = False
                            audio_proc = None
                            current_call_id = None
                        logging.info("Call terminated. Waiting for next incoming call...")

            except socket.timeout:
                # Timeout is normal, just continue
                continue
            except Exception as e:
                logging.error(f"Error reading from socket: {e}")
                break

    except Exception as e:
        logging.error(f"Exception in monitor loop: {e}")
    finally:
        # Clean up any running audio process
        if audio_proc and audio_proc.poll() is None:
            logging.info("Cleaning up audio routing process...")
            audio_proc.terminate()
            try:
                audio_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                audio_proc.kill()


def main():
    """Main function to parse arguments and start monitoring"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Monitor Baresip and route audio calls')
    parser.add_argument('-n', '--number', default='9723507770',
                        help='Phone number to dial (default: 9723507770)')
    parser.add_argument('-r', '--skip-rerouting', action='store_true',
                        help='Skip audio re-routing (pass -r to place_call.py)')
    parser.add_argument('--host', default=BARESIP_HOST,
                        help=f'Baresip host (default: {BARESIP_HOST})')
    parser.add_argument('--port', type=int, default=BARESIP_PORT,
                        help=f'Baresip TCP port (default: {BARESIP_PORT})')
    args = parser.parse_args()

    logging.info(f"Starting Baresip TCP monitor on {args.host}:{args.port}")
    logging.info(f"Will dial number: {args.number}")
    if args.skip_rerouting:
        logging.info("Audio re-routing will be skipped (-r flag set)")
    logging.info("Press Ctrl+C to exit.")

    stop_event = threading.Event()
    sock = None

    try:
        # Connect to baresip
        sock = connect_to_baresip(args.host, args.port)
        if not sock:
            logging.error("Failed to connect to baresip. Exiting.")
            sys.exit(1)

        # Start monitoring in main thread
        monitor_baresip_socket(sock, args.number, args.skip_rerouting, stop_event)

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
