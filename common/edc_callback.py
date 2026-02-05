#!/usr/bin/env python3
"""
EDC Callback Script - Initiates callback to primary phone number.

This script is invoked from the Asterisk dialplan when an admin
enters the #25 DTMF sequence. It:
1. Ensures any existing call is hung up
2. Reads the FIRST_NUMBER from config
3. Strips any *5x prefix
4. Initiates a callback with error code EC=CB
5. Adds extension 201 to conference bridge via ARI
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
ADMIN_EXT_MASTER = "201"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)-8s [EDC_CALLBACK] %(message)s",
    datefmt="%m-%d %H:%M:%S",
)


def send_modem_command(command: str, params: dict = None) -> dict:
    """
    Send command to manage_modem TCP server.

    Args:
        command: Command name (e.g., "hangup", "place_call", "status")
        params: Optional parameters dictionary

    Returns:
        Response dictionary from server

    Raises:
        Exception: If communication fails
    """
    request = {
        "command": command,
        "params": params or {},
        "request_id": str(uuid.uuid4()),
    }

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(SOCKET_TIMEOUT)
            sock.connect((MANAGE_MODEM_HOST, MANAGE_MODEM_PORT))

            # Send request
            request_json = json.dumps(request) + "\n"
            sock.sendall(request_json.encode("utf-8"))
            logging.info(f"Sent command: {command}")

            # Receive response
            response_data = sock.recv(4096).decode("utf-8")
            response = json.loads(response_data.strip())
            logging.info(f"Received response: {response}")

            return response

    except Exception as e:
        logging.error(f"Failed to communicate with manage_modem: {e}")
        raise


def ensure_call_hung_up() -> bool:
    """
    Check current call status and hang up if a call is active.
    Wait for modem to return to IDLE state.

    Returns:
        True if no call is active (or was successfully hung up)
    """
    max_wait = 30  # Maximum seconds to wait for IDLE state (increased for slow hangups)
    start_time = time.time()

    try:
        while time.time() - start_time < max_wait:
            # Check status
            status_response = send_modem_command("status")
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
                hangup_response = send_modem_command("hangup")

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


def initiate_callback(number: str) -> bool:
    """
    Initiate callback (without EDC prefix in the dial string).

    Args:
        number: Phone number to call

    Returns:
        True if callback initiated successfully
    """
    try:
        logging.info(f"Initiating callback to: {number}")

        # Send place_call command (EDC packet already sent separately)
        response = send_modem_command(
            "place_call", params={"number": number, "no_audio_routing": True}
        )

        if response.get("status") in ["success", "pending"]:
            logging.info("Callback initiated successfully")
            return True
        else:
            logging.error(f"Failed to initiate callback: {response.get('message')}")
            return False

    except Exception as e:
        logging.error(f"Error initiating callback: {e}")
        return False


async def originate_call_to_extension_ari(extension_number: str) -> str:
    """
    Originate a call to a specific extension via ARI.

    Args:
        extension_number: Extension to call (e.g., "201")

    Returns:
        Channel ID if successful, None otherwise
    """
    endpoint = f"PJSIP/{extension_number}"
    base_url = f"http://{ARI_HOST}:{ARI_PORT}/ari"
    auth = aiohttp.BasicAuth(ARI_USER, ARI_PASSWORD)

    originate_data = {
        "endpoint": endpoint,
        "app": ARI_APP_NAME,
        "appArgs": f"conf,{CONFERENCE_NAME}",
        "callerId": f"{extension_number}",
        "timeout": 30,
    }

    try:
        async with aiohttp.ClientSession(auth=auth) as session:
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
                    return channel_id
                else:
                    error_text = await resp.text()
                    logging.error(
                        f"Failed to originate ARI call: {resp.status} - {error_text}"
                    )
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
    Originate call to extension 201 and add to conference as admin.

    Returns:
        True if successful
    """
    logging.info(f"Adding extension {ADMIN_EXT_MASTER} to conference via ARI")

    # Originate call to extension 201
    channel_id = await originate_call_to_extension_ari(ADMIN_EXT_MASTER)
    if not channel_id:
        logging.error(f"Failed to originate call to extension {ADMIN_EXT_MASTER}")
        return False

    # Wait a moment for channel to be ready
    await asyncio.sleep(1)

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

    # Step 1: Ensure any existing calls are hung up
    logging.info("Step 1: Checking for active calls")
    if not ensure_call_hung_up():
        logging.error("Failed to ensure call is hung up")
        sys.exit(1)

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

    # Step 5: Initiate callback
    logging.info("Step 5: Initiating callback")
    if not initiate_callback(number):
        logging.error("Failed to initiate callback")
        sys.exit(1)

    # Step 6: Add extension 201 to conference via ARI
    logging.info("Step 6: Adding extension 201 to conference via ARI")
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
