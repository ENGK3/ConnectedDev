#!/usr/bin/env python3
"""
EDC Callback Script - Initiates callback to primary phone number.

This script is invoked from the Asterisk dialplan when an admin
enters the #25 DTMF sequence. It:
1. Ensures any existing call is hung up
2. Reads the FIRST_NUMBER from config
3. Strips any *5x prefix
4. Initiates a callback with error code EC=CB
5. Adds extension 200 to conference bridge via ARI
"""

import asyncio
import json
import logging
import os
import socket
import subprocess
import sys
import time
import uuid

import aiohttp
from dotenv import dotenv_values

# Configuration
DEFAULT_CONFIG_FILE = "/mnt/data/K3_config_settings"
MANAGE_MODEM_HOST = "127.0.0.1"
MANAGE_MODEM_PORT = 5555
SOCKET_TIMEOUT = 10.0

# ARI Configuration
ARI_HOST = "127.0.0.1"
ARI_PORT = 8088
ARI_USER = "at_user"
ARI_PASSWORD = "asterisk"
ARI_APP_NAME = "conf_monitor"
CONFERENCE_NAME = "elevator_conference"
ADMIN_EXT_MASTER = "200"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)-8s [EDC_CALLBACK] %(message)s",
    datefmt="%m-%d %H:%M:%S",
)


def ensure_call_hung_up() -> bool:
    """
    Check current call status and hang up if a call is active.
    Wait for modem to return to IDLE state.
    Maintains persistent connection to avoid repeated connect/disconnect cycles.

    Returns:
        True if no call is active (or was successfully hung up)
    """
    max_wait = 30  # Maximum seconds to wait for IDLE state
    start_time = time.time()

    try:
        # Open persistent connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(SOCKET_TIMEOUT)
        sock.connect((MANAGE_MODEM_HOST, MANAGE_MODEM_PORT))
        logging.info("Connected to manage_modem server")

        try:
            while time.time() - start_time < max_wait:
                # Send status command
                status_request = {
                    "command": "status",
                    "params": {},
                    "request_id": str(uuid.uuid4()),
                }
                request_json = json.dumps(status_request) + "\n"
                sock.sendall(request_json.encode("utf-8"))
                logging.info("Sent command: status")

                # Receive response
                response_data = sock.recv(4096).decode("utf-8")
                status_response = json.loads(response_data.strip())
                logging.info(f"Received response: {status_response}")

                if status_response.get("status") != "success":
                    logging.error("Failed to get modem status")
                    return False

                data = status_response.get("data", {})
                state = data.get("state")
                logging.info(f"Current modem state: {state}")

                # If idle, we're good
                if state in ["IDLE", None]:
                    logging.info("Modem is in IDLE state")
                    return True

                # If call is active, hang it up
                if state == "CALL_ACTIVE":
                    logging.info("Hanging up active call")
                    hangup_request = {
                        "command": "hangup",
                        "params": {},
                        "request_id": str(uuid.uuid4()),
                    }
                    request_json = json.dumps(hangup_request) + "\n"
                    sock.sendall(request_json.encode("utf-8"))

                    # Receive hangup response
                    response_data = sock.recv(4096).decode("utf-8")
                    hangup_response = json.loads(response_data.strip())
                    logging.info(f"Received response: {hangup_response}")

                    if hangup_response.get("status") != "success":
                        logging.error("Failed to hang up call")
                        return False

                # If call is ending or placing, wait for it to finish
                if state in ["CALL_ENDING", "PLACING_CALL", "ANSWERING_CALL"]:
                    logging.info(f"Waiting for modem to finish {state}...")
                    time.sleep(1)
                    continue

                # Unknown state - wait a bit
                logging.warning(f"Unknown state: {state}, waiting...")
                time.sleep(1)

            # Timeout waiting for IDLE
            logging.error(
                f"Timeout waiting for modem to reach IDLE state after {max_wait}s"
            )
            return False

        finally:
            # Always close the socket
            sock.close()
            logging.info("Disconnected from manage_modem server")

    except Exception as e:
        logging.error(f"Error ensuring call hung up: {e}")
        return False


def read_first_number(config_file: str) -> str:
    """
    Read FIRST_NUMBER from config file.

    Args:
        config_file: Path to K3_config_settings file

    Returns:
        Phone number (empty string if not found)
    """
    try:
        if not os.path.exists(config_file):
            logging.error(f"Config file not found: {config_file}")
            return ""

        config = dotenv_values(config_file)
        first_number = config.get("FIRST_NUMBER", "")

        if not first_number:
            logging.warning("FIRST_NUMBER not found in config")
            return ""

        logging.info(f"Read FIRST_NUMBER from config: {first_number}")
        return first_number

    except Exception as e:
        logging.error(f"Error reading config file: {e}")
        return ""


def strip_dial_code_prefix(number: str) -> str:
    """
    Strip *5x prefix from number if present.

    Args:
        number: Phone number (may include *5x prefix)

    Returns:
        Phone number with prefix stripped
    """
    if not number:
        return number

    # Check for *5x prefix (where x is a digit)
    if number.startswith("*5") and len(number) > 2 and number[2].isdigit():
        stripped = number[3:]
        logging.info(f"Stripped prefix: {number} -> {stripped}")
        return stripped

    return number


def send_edc_packet(edc_code: str = "CB") -> bool:
    """
    Send EDC packet by calling send_EDC_info.py script.

    Args:
        edc_code: EDC code to use (default "CB" for callback)

    Returns:
        True if packet sent successfully
    """
    logging.info(f"Sending EDC packet with code: {edc_code}")

    try:
        # Call send_EDC_info.py script
        result = subprocess.run(
            ["python3", "/mnt/data/send_EDC_info.py", "-e", edc_code],
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout for EDC packet sending
        )

        if result.returncode == 0:
            logging.info(f"EDC packet sent successfully (code: {edc_code})")
            if result.stdout:
                logging.debug(f"EDC output: {result.stdout}")
            return True
        else:
            logging.error(
                f"Failed to send EDC packet (code: {edc_code}), "
                f"return code: {result.returncode}"
            )
            if result.stderr:
                logging.error(f"EDC error: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logging.error("EDC packet sending timed out after 60 seconds")
        return False
    except Exception as e:
        logging.error(f"Error sending EDC packet: {e}")
        return False


async def originate_call_to_extension_ari(extension_number: str) -> str | None:
    """
    Originate a call to a specific extension via ARI and wait for StasisStart.

    Args:
        extension_number: Extension to call (e.g., "200")

    Returns:
        Channel ID if successful, None otherwise
    """
    endpoint = f"PJSIP/{extension_number}"
    base_url = f"http://{ARI_HOST}:{ARI_PORT}/ari"
    ws_url = f"ws://{ARI_HOST}:{ARI_PORT}/ari/events"
    auth = aiohttp.BasicAuth(ARI_USER, ARI_PASSWORD)

    originate_data = {
        "endpoint": endpoint,
        "app": ARI_APP_NAME,
        "appArgs": f"conf,{CONFERENCE_NAME}",
        "callerId": f"{extension_number}",
        "timeout": 30,
    }

    channel_id = None
    asyncio.Event()

    try:
        async with aiohttp.ClientSession(auth=auth) as session:
            # Connect to WebSocket to receive StasisStart event
            ws_params = {"app": ARI_APP_NAME, "subscribeAll": "false"}
            ws = await session.ws_connect(ws_url, params=ws_params, heartbeat=30)
            logging.info("Connected to ARI WebSocket for event monitoring")

            # Originate the call
            url = f"{base_url}/channels"
            async with session.post(url, json=originate_data) as resp:
                logging.info(f"Originating ARI call to {endpoint}...")
                if resp.status == 200:
                    channel_data = await resp.json()
                    channel_id = channel_data["id"]
                    logging.info(
                        f"Successfully originated ARI call to {endpoint}, "
                        f"channel: {channel_id}"
                    )
                else:
                    error_text = await resp.text()
                    logging.error(
                        f"Failed to originate ARI call: {resp.status} - {error_text}"
                    )
                    await ws.close()
                    return None

            # Wait for StasisStart event
            logging.info(f"Waiting for StasisStart event for channel {channel_id}...")
            timeout_seconds = 10
            start_time = asyncio.get_event_loop().time()

            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    event = msg.json()
                    event_type = event.get("type")

                    if event_type == "StasisStart":
                        event_channel_id = event.get("channel", {}).get("id")
                        if event_channel_id == channel_id:
                            logging.info(
                                f"Received StasisStart for channel {channel_id}"
                            )
                            await ws.close()
                            return channel_id

                # Check timeout
                if asyncio.get_event_loop().time() - start_time > timeout_seconds:
                    logging.error(
                        f"Timeout waiting for StasisStart after {timeout_seconds}s"
                    )
                    await ws.close()
                    return None

            await ws.close()
            return None

    except Exception as e:
        logging.error(f"Error originating ARI call: {e}")
        return None


async def add_to_conference_ari(channel_id: str) -> bool:
    """
    Add a channel to the ConfBridge conference as admin via ARI.

    Args:
        channel_id: Channel ID to add to conference

    Returns:
        True if successful
    """
    base_url = f"http://{ARI_HOST}:{ARI_PORT}/ari"
    auth = aiohttp.BasicAuth(ARI_USER, ARI_PASSWORD)

    try:
        async with aiohttp.ClientSession(auth=auth) as session:
            # Answer the channel first
            answer_url = f"{base_url}/channels/{channel_id}/answer"
            async with session.post(answer_url) as resp:
                if resp.status == 204:
                    logging.info(f"Channel {channel_id} answered via ARI")
                else:
                    logging.warning(f"Failed to answer channel via ARI: {resp.status}")

            # Wait a moment for channel to stabilize
            await asyncio.sleep(0.5)

            # Set channel variables for ConfBridge
            var_url = f"{base_url}/channels/{channel_id}/variable"

            # Set the conference name as a channel variable
            async with session.post(
                var_url,
                params={
                    "variable": "CONFBRIDGE_CONFERENCE",
                    "value": CONFERENCE_NAME,
                },
            ) as resp:
                if resp.status == 204:
                    logging.info("Set CONFBRIDGE_CONFERENCE variable via ARI")

            # Set admin profile
            async with session.post(
                var_url,
                params={
                    "variable": "CONFBRIDGE_USER_PROFILE",
                    "value": "default_admin",
                },
            ) as resp:
                if resp.status == 204:
                    logging.info("Set ConfBridge admin profile via ARI")

            # Exit Stasis and continue to dialplan extension that runs ConfBridge
            continue_url = f"{base_url}/channels/{channel_id}/continue"
            continue_data = {
                "context": "from-internal",
                "extension": "confbridge_admin_join",
                "priority": 1,
            }

            async with session.post(continue_url, json=continue_data) as resp:
                if resp.status == 204:
                    logging.info(
                        f"Successfully sent extension {ADMIN_EXT_MASTER} to join "
                        f"conference {CONFERENCE_NAME} as admin via ARI"
                    )
                    return True
                else:
                    error_text = await resp.text()
                    logging.error(
                        f"Failed to continue to dialplan via ARI: {resp.status} - "
                        f"{error_text}"
                    )
                    return False

    except Exception as e:
        logging.error(f"Error adding to conference via ARI: {e}")
        return False


async def add_admin_to_conference() -> bool:
    """
    Originate call to extension 200 and add to conference as admin.

    Returns:
        True if successful
    """
    logging.info(f"Adding extension {ADMIN_EXT_MASTER} to conference via ARI")

    # Originate call to extension 200 and wait for StasisStart
    channel_id = await originate_call_to_extension_ari(ADMIN_EXT_MASTER)
    if not channel_id:
        logging.error(f"Failed to originate call to extension {ADMIN_EXT_MASTER}")
        return False

    # Channel is now in Stasis, ready to be manipulated
    # Add to conference
    success = await add_to_conference_ari(channel_id)
    if not success:
        logging.error(f"Failed to add extension {ADMIN_EXT_MASTER} to conference")
        return False

    logging.info(f"Successfully added extension {ADMIN_EXT_MASTER} to conference")
    return True


def main():
    """Main entry point."""
    logging.info("=" * 60)
    logging.info("EDC Callback Script Starting")
    logging.info("=" * 60)

    # # Step 1: Ensure any existing calls are hung up

    # This is what I would like to do. HOWEVER,
    # There is some issue with the lock for the modem
    # getting stuck for about 20 seconds.
    # Making this a waste of time - compounding the issue.
    #
    # logging.info("Step 1: Checking for active calls")
    # if not ensure_call_hung_up():
    #     logging.error("Failed to ensure call is hung up")
    #     sys.exit(1)

    # This is the work around to avoid the contention, and wait for the
    # system to settle after the hangup sent from the Asterisk server.

    time_to_wait_for_hangup = 25
    logging.info(
        f"Step 1: Waiting {time_to_wait_for_hangup} seconds for "
        "call to finish hanging up"
    )
    time.sleep(time_to_wait_for_hangup)
    logging.info("Step 1: Done waiting ")

    # Step 2: Read FIRST_NUMBER from config
    logging.info("Step 2: Reading FIRST_NUMBER from config")
    first_number = read_first_number(DEFAULT_CONFIG_FILE)
    if not first_number:
        logging.error("FIRST_NUMBER not found in config")
        sys.exit(1)

    # Step 3: Strip *5x prefix if present
    logging.info("Step 3: Stripping dial code prefix")
    number = strip_dial_code_prefix(first_number)
    if not number:
        logging.error("No valid phone number after stripping prefix")
        sys.exit(1)

    # Step 4: Send EDC packet with EC=CB
    logging.info("Step 4: Sending EDC packet with error code CB")
    if not send_edc_packet("CB"):
        logging.error("Failed to send EDC packet")
        sys.exit(1)

    # Step 5: Add extension 200 to conference via ARI
    logging.info(
        "Step 5: Adding extension 200 to conference via "
        "ARI. This causes the dial back to happen"
    )
    try:
        success = asyncio.run(add_admin_to_conference())
        if not success:
            logging.error("Failed to add admin to conference")
            sys.exit(1)
    except Exception as e:
        logging.error(f"Error adding admin to conference: {e}")
        sys.exit(1)

    logging.info("=" * 60)
    logging.info("EDC Callback Script Completed Successfully")
    logging.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
