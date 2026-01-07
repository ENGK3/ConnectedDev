"""
Shared utilities for Telit LE910C1 modem communication.

This module provides common functions for AT command communication,
network registration checking, and modem configuration that can be
used across multiple scripts.
"""

import logging
import time
from typing import Tuple

import serial

# Timeout constants
AT_COMMAND_TIMEOUT = 5  # seconds for AT command responses

MAX_NO_DATA_ITERATIONS = 10  # Maximum iterations with no data before giving up early


def sbc_cmd(cmd: str, serial_connection: serial.Serial, verbose: bool) -> str:
    """
    Send a command to the SBC and return the response.
    Handles unsolicited responses that may come between echo and OK.

    Args:
        cmd: AT command string to send (should include \\r termination)
        serial_connection: Open serial connection to the modem
        verbose: Enable verbose logging

    Returns:
        Response string from the modem
    """
    if verbose:
        logging.info(f"Sending command: {cmd.strip()}")
    serial_connection.write(cmd.encode())

    # Read echo
    serial_connection.readline()

    # Keep reading until we get OK or ERROR
    response = ""
    while True:
        line = serial_connection.readline().decode().strip()
        if not line:
            break
        if (
            line in ["OK", "ERROR"]
            or line.startswith("ERROR")
            or line.startswith("+CME ERROR")
        ):
            response = line
            break
        # Print unsolicited messages like +CIEV: as they arrive
        if line.startswith("+CIEV:"):
            logging.info(f"[CIEV] {line}")
            continue
        # This might be a real response (like +CEREG:, +CPIN:, etc.)
        response = line

    if verbose:
        logging.info(f"Response: {response}")
    return response


def sbc_cmd_with_timeout(
    cmd: str,
    serial_connection: serial.Serial,
    timeout: float = AT_COMMAND_TIMEOUT,
    verbose: bool = False,
) -> str:
    """
    Send an AT command to the LE910C1 modem and return the response with timeout.
    This version is used for TCP/data operations that need precise timeout control.

    Args:
        cmd: AT command string to send (should include \\r termination)
        serial_connection: Open serial connection to the modem
        timeout: Timeout in seconds for waiting for response
        verbose: Enable verbose logging

    Returns:
        Response string from the modem
    """
    if verbose:
        logging.info(f"Sending command: {cmd.strip()}")

    # Clear any pending data in buffers
    serial_connection.reset_input_buffer()

    # Save original timeout and set a shorter one for responsive reading
    original_timeout = serial_connection.timeout
    serial_connection.timeout = 0.1  # Short timeout for readline

    try:
        serial_connection.write(cmd.encode())

        # Read echo (if echo is enabled)
        response_lines = []
        start_time = time.time()
        no_data_count = 0

        while (time.time() - start_time) < timeout:
            if serial_connection.in_waiting > 0:
                no_data_count = 0  # Reset counter when we receive data
                line = (
                    serial_connection.readline()
                    .decode("utf-8", errors="ignore")
                    .strip()
                )
                if line and line != cmd.strip():
                    response_lines.append(line)
                    if verbose:
                        logging.debug(f"Response line: {line}")
                    # Check for common response terminators
                    # Include '>' for data send prompts
                    if (
                        line in ["OK", "ERROR", "CONNECT", ">"]
                        or line.startswith("+CME ERROR")
                        or line.startswith("+CMS ERROR")
                    ):
                        break
            else:
                no_data_count += 1
                # If we already have response lines and there's been no data for a
                # while, break early
                if response_lines and no_data_count > MAX_NO_DATA_ITERATIONS:
                    if verbose:
                        logging.debug(
                            f"No more data after {no_data_count} iterations, breaking"
                            " early"
                        )
                    break
            time.sleep(0.05)

        response = "\n".join(response_lines)

        if verbose:
            logging.info(f"Full response: {response}")

        return response

    finally:
        # Restore original timeout
        serial_connection.timeout = original_timeout


def check_registration(serial_connection: serial.Serial, verbose: bool = False) -> bool:
    """
    Check if the modem is registered on the network.

    Args:
        serial_connection: Open serial connection to the modem
        verbose: Enable verbose logging

    Returns:
        True if registered (stat=1 or stat=5), False otherwise
    """
    response = sbc_cmd("AT+CEREG?\r", serial_connection, verbose=verbose)
    if response.startswith("+CEREG:"):
        parts = response.split(",")
        if len(parts) > 1:
            stat = parts[1].strip()
            if stat in ["1", "5"]:
                logging.info(f"Modem registered: stat={stat}")
                return True
            else:
                logging.info(f"Modem not registered yet: stat={stat}")
                if verbose:
                    start_reg_again(serial_connection)
    return False


def start_reg_again(serial_connection: serial.Serial, verbose: bool = False) -> None:
    """
    Restart the network registration process.

    Args:
        serial_connection: Open serial connection to the modem
        verbose: Enable verbose logging
    """
    logging.info("Starting registration process again")
    sbc_cmd("AT+COPS=2\r", serial_connection, verbose=verbose)
    sbc_cmd("AT+COPS=0\r", serial_connection, verbose=verbose)


def sbc_connect(
    serial_connection: serial.Serial,
    port: str = "/dev/ttyUSB2",
    baudrate: int = 115200,
    timeout: int = 30,
) -> bool:
    """
    Connect to the SBC modem via serial port.

    Args:
        serial_connection: Serial connection object (should be closed)
        port: Serial port device path
        baudrate: Serial communication baud rate
        timeout: Serial read timeout in seconds

    Returns:
        True if connection successful, False otherwise
    """
    serial_connection.port = port
    serial_connection.baudrate = baudrate
    serial_connection.timeout = timeout
    serial_connection.xonxoff = False
    logging.info(
        f"Connecting to SBC on port {serial_connection.port} "
        f"with baud rate {serial_connection.baudrate}"
    )
    try:
        serial_connection.open()
        serial_connection.write(b"ATE0\r")
        response = serial_connection.readline()
        response = serial_connection.readline()
        logging.info(f"SBC connected successfully?: {response.decode().strip()}")
        return serial_connection.is_open
    except Exception as e:
        logging.error(f"Failed to connect to SBC: {e}")
        return False


def sbc_disconnect(serial_connection: serial.Serial) -> None:
    """
    Disconnect from the SBC modem.

    Args:
        serial_connection: Open serial connection to close
    """
    if serial_connection.is_open:
        serial_connection.close()
        logging.info(f"Disconnected from SBC on port {serial_connection.port}")


def check_network_status(
    serial_connection: serial.Serial, verbose: bool = False
) -> None:
    """
    Check and log network registration and signal quality before sending data.
    Sends AT+CREG?, AT+CEREG?, and AT+CSQ to the modem and logs the results.

    Args:
        serial_connection: Open serial connection to the modem
        verbose: Enable verbose logging
    """
    try:
        creg = sbc_cmd_with_timeout("AT+CREG?\r", serial_connection, verbose=False)
        cereg = sbc_cmd_with_timeout("AT+CEREG?\r", serial_connection, verbose=False)
        csq = sbc_cmd_with_timeout("AT+CSQ\r", serial_connection, verbose=False)
        logging.info(f"Network registration (AT+CREG?): {creg.strip()}")
        logging.info(f"EPS Network registration (AT+CEREG?): {cereg.strip()}")
        logging.info(f"Signal quality (AT+CSQ): {csq.strip()}")
    except Exception as e:
        logging.error(f"Error checking network status: {e}")


def get_modem_info(
    serial_connection: serial.Serial, verbose: bool = False
) -> Tuple[str, str, str, str, str, str, str, str, str, str, str]:
    """
    Retrieve modem identification information from the Telit LE910C1.

    This function queries the modem for:
    - ICCID (Integrated Circuit Card Identifier) - SIM card serial number
    - IMEI (International Mobile Equipment Identity) - Device identifier
    - IMSI (International Mobile Subscriber Identity) - Subscriber identifier

    Args:
        serial_connection: Open serial connection to the modem
        verbose: Enable verbose logging

    Returns:
        Tuple of (ICCID, IMEI, IMSI)
        Returns empty strings for any values that could not be retrieved
    """
    apn = ""
    facility_lock = ""
    signal_quality = ""
    ims_reg = ""
    network = ""
    temp = ""
    rsrq = ""
    rsrp = ""
    iccid = ""
    imei = ""
    imsi = ""

    try:
        # Get wireless APN
        # AT command: AT+CGDCONT?
        # Response format:  +CGDCONT: <cid>,<PDP_type>,<APN>,<PDP_addr>,<d_comp>,
        #                             <h_comp>,<IPv4AddrAlloc>,<Emergency_ind>
        response = sbc_cmd_with_timeout(
            "AT+CGDCONT?\r", serial_connection, verbose=False
        )
        if "+CGDCONT:" in response:
            for line in response.split("\n"):
                if "+CGDCONT: 1" in line:
                    apn = line.split(",")[2].replace('"', "")
                    break

        if verbose and facility_lock:
            logging.info("=" * 60)
            logging.info(f"FACILITY_LOCK: {facility_lock}")

        # Get facility lock status
        # AT command: AT+CLCK = "SC", 2
        # Response format:  +CLCK: <facility_lock>
        response = sbc_cmd_with_timeout(
            'AT+CLCK = "SC", 2\r', serial_connection, verbose=False
        )
        if "+CLCK:" in response:
            for line in response.split("\n"):
                if "+CLCK:" in line:
                    facility_lock = line.split(":")[1].strip()
                    break

        if verbose and facility_lock:
            logging.info("=" * 60)
            logging.info(f"FACILITY_LOCK: {facility_lock}")

        # Get signal quality
        # AT command: AT+CSQ
        # Response format:  +CSQ: <signal_quality>, <sq>
        response = sbc_cmd_with_timeout("AT+CSQ\r", serial_connection, verbose=False)
        if "+CSQ:" in response:
            for line in response.split("\n"):
                if "+CSQ:" in line:
                    signal_quality = line.split(",")[0].strip().split(":")[1].strip()
                    break

        if verbose and signal_quality:
            logging.info("=" * 60)
            logging.info(f"SIGNAL_QUALITY: {signal_quality}")

        # Get IMS registration status
        # AT command: AT+CIREG?
        # Response format: +CIREG: <mode>, <ims_reg>
        response = sbc_cmd_with_timeout("AT+CIREG?\r", serial_connection, verbose=False)
        if "+CIREG:" in response:
            for line in response.split("\n"):
                if "+CIREG:" in line:
                    ims_reg = line.split(",")[1].strip()
                    break

        if verbose and ims_reg:
            logging.info("=" * 60)
            logging.info(f"IMS_REGISTRATION: {ims_reg}")

        # Get current network technology (2G, 3G, 4G)
        # AT command: AT+COPS?
        # Response format: +COPS: <mode>, <format>, <oper>, <network>
        response = sbc_cmd_with_timeout("AT+COPS?\r", serial_connection, verbose=False)
        if "+COPS:" in response:
            for line in response.split("\n"):
                if "+COPS:" in line:
                    network = line.split(",")[3].strip()
                    break

        if verbose and network:
            logging.info("=" * 60)
            logging.info(f"NETWORK: {network}")

        # Get Telit temperature in celsius
        # AT command: AT#TEMPMON=1
        # Response format: #TEMPMEAS: <range>, <temp>
        response = sbc_cmd_with_timeout(
            "AT#TEMPMON=1\r", serial_connection, verbose=False
        )
        if "#TEMPMEAS:" in response:
            for line in response.split("\n"):
                if "#TEMPMEAS:" in line:
                    temp = line.split(",")[1].strip()
                    break

        if verbose and temp:
            logging.info("=" * 60)
            logging.info(f"TEMP: {temp}")

        # Get signal quality stats
        # AT command: AT+CESQ
        # Response format: #CESQ: 99, 99, 255, 255, <rsrq>, <rsrp>
        response = sbc_cmd_with_timeout("AT+CESQ\r", serial_connection, verbose=False)
        if "+CESQ:" in response:
            for line in response.split("\n"):
                if "+CESQ:" in line:
                    rsrq = line.split(",")[4].strip()
                    rsrp = line.split(",")[5].strip()
                    break

        if verbose and rsrq:
            logging.info("=" * 60)
            logging.info(f"RSRQ: {rsrq}")

        if verbose and rsrp:
            logging.info("=" * 60)
            logging.info(f"RSRP: {rsrp}")

        # Get ICCID - SIM card serial number
        # AT command: AT+ICCID or AT#CCID
        # Response format: #CCID: <iccid> or +ICCID: <iccid>
        response = sbc_cmd_with_timeout("AT#CCID\r", serial_connection, verbose=False)
        if "#CCID:" in response:
            # Parse: #CCID: 89012345678901234567
            for line in response.split("\n"):
                if "#CCID:" in line:
                    iccid = line.split(":")[1].strip()
                    break
        else:
            # Try alternative command
            response = sbc_cmd_with_timeout(
                "AT+ICCID\r", serial_connection, verbose=False
            )
            if "+ICCID:" in response:
                for line in response.split("\n"):
                    if "+ICCID:" in line:
                        iccid = line.split(":")[1].strip()
                        break

        if verbose and iccid:
            logging.info("=" * 60)
            logging.info(f"ICCID: {iccid}")

        # Get IMEI - Device identifier
        # AT command: AT+CGSN or AT#CGSN
        # Response format: <imei> followed by OK
        response = sbc_cmd_with_timeout("AT+CGSN\r", serial_connection, verbose=False)
        # IMEI is typically 15 digits and appears before OK
        for line in response.split("\n"):
            line = line.strip()
            # IMEI is numeric and 15 digits
            if line.isdigit() and len(line) == 15:
                imei = line
                break
            # Sometimes it has additional info, try to extract just the number
            elif line and line[0].isdigit() and "OK" not in line:
                # Extract just the numeric part
                numeric_part = "".join(filter(str.isdigit, line))
                if len(numeric_part) == 15:
                    imei = numeric_part
                    break

        if verbose and imei:
            logging.info(f"IMEI: {imei}")

        # Get IMSI - Subscriber identifier
        # AT command: AT+CIMI
        # Response format: <imsi> followed by OK
        response = sbc_cmd_with_timeout("AT+CIMI\r", serial_connection, verbose=False)
        # IMSI is typically 14-15 digits and appears before OK
        for line in response.split("\n"):
            line = line.strip()
            # IMSI is numeric and 14-15 digits
            if line.isdigit() and len(line) >= 14 and len(line) <= 15:
                imsi = line
                break
            # Sometimes it has additional info, try to extract just the number
            elif line and line[0].isdigit() and "OK" not in line:
                # Extract just the numeric part
                numeric_part = "".join(filter(str.isdigit, line))
                if len(numeric_part) >= 14 and len(numeric_part) <= 15:
                    imsi = numeric_part
                    break

        if verbose and imsi:
            logging.info(f"IMSI: {imsi}")

        if verbose:
            logging.info("=" * 60)

    except Exception as e:
        logging.error(f"Error retrieving modem information: {str(e)}")

    return (
        iccid,
        imei,
        imsi,
        rsrq,
        rsrp,
        temp,
        network,
        ims_reg,
        signal_quality,
        facility_lock,
        apn,
    )


def get_software_package_version(
    serial_connection: serial.Serial, verbose: bool = False
) -> str:
    """
    Retrieve the Telit Software Package Version from the modem.

    This function queries the modem using AT#SWPKGV command and returns
    the first line of the response which contains:
    <Telit Software Package Version>-<Production Parameters Version>

    Args:
        serial_connection: Open serial connection to the modem
        verbose: Enable verbose logging

    Returns:
        Software package version string (e.g., "25.21.661-P0C17")
        Returns empty string if the version could not be retrieved
    """
    version = ""

    try:
        # Get Software Package Version
        # AT command: AT#SWPKGV
        # Response format: <version>-<params> followed by OK
        response = sbc_cmd_with_timeout(
            "AT#SWPKGV\r", serial_connection, verbose=verbose
        )

        # The first line of the response contains the version information
        for line in response.split("\n"):
            line = line.strip()
            # Skip empty lines and OK/ERROR responses
            if (
                line
                and line not in ["OK", "ERROR"]
                and not line.startswith("+CME ERROR")
            ):
                version = line
                break

        if verbose and version:
            logging.info(f"Software Package Version: {version}")

    except Exception as e:
        logging.error(f"Error retrieving software package version: {str(e)}")

    return version


def configure_modem_tcp(
    serial_connection: serial.Serial, context_id: int = 1, verbose: bool = False
) -> Tuple[int, str]:
    """
    Configure the Telit LE910C1 modem for TCP communication.

    This function:
    - Checks network registration
    - Configures PDP context
    - Activates the data connection

    Args:
        serial_connection: Open serial connection to the modem
        context_id: PDP context ID to use (default: 1)
        verbose: Enable verbose logging

    Returns:
        Tuple of (error_code, error_message)
        - (0, "") on success
        - (non-zero, error_description) on failure
    """
    try:
        # Disable echo for cleaner parsing
        response = sbc_cmd_with_timeout("ATE0\r", serial_connection, verbose=verbose)

        # Check if modem is responsive
        response = sbc_cmd_with_timeout("AT\r", serial_connection, verbose=verbose)
        if "OK" not in response:
            return (1, "Modem not responding to AT commands")

        response = sbc_cmd_with_timeout(
            "AT+CMEE=2\r", serial_connection, verbose=verbose
        )
        if "OK" not in response:
            return (1, "Modem not responding to CMEE commands")

        # Check network registration
        response = sbc_cmd_with_timeout(
            "AT+CEREG?\r", serial_connection, verbose=verbose
        )
        if "+CEREG:" in response:
            # Parse registration status
            # Response format: +CEREG: <n>,<stat>[,...]
            # stat: 1=registered home, 5=registered roaming
            parts = response.split(",")
            if len(parts) >= 2:
                stat = parts[1].strip().split("\n")[0]
                if stat not in ["1", "5"]:
                    return (2, f"Modem not registered on network (stat={stat})")
        else:
            return (2, "Could not query network registration status")

        # Check if context is already active
        response = sbc_cmd_with_timeout(
            "AT#SGACT?\r", serial_connection, verbose=verbose
        )
        context_active = False
        if f"#SGACT: {context_id},1" in response:
            context_active = True
            logging.info(f"Context {context_id} is already active")

        # Activate context if not already active
        if not context_active:
            # Activate PDP context
            logging.info(f"Activating PDP context {context_id}...")
            response = sbc_cmd_with_timeout(
                f"AT#SGACT={context_id},1\r",
                serial_connection,
                timeout=60,  # Context activation can take longer
                verbose=verbose,
            )

            if "OK" not in response and "#SGACT:" not in response:
                return (3, f"Failed to activate PDP context: {response}")

        # Configure socket parameters
        # Set packet size to 1500 bytes (typical MTU)
        response = sbc_cmd_with_timeout(
            "AT#SCFG=1,1,1500,90,600,50\r", serial_connection, verbose=verbose
        )

        # Extended configuration - TCP parameters
        # AT#SCFGEXT=<socketId>,<srMode>,<recvDataMode>,<keepalive>,<listenAutoRsp>,
        # <sendDataMode> srMode=2: Enable all socket ring unsolicited messages
        # (CRITICAL for command mode)
        # This enables #SRING notifications when data arrives
        response = sbc_cmd_with_timeout(
            "AT#SCFGEXT=1,2,0,30,0,0\r", serial_connection, verbose=verbose
        )

        # Enable unsolicited socket event reporting
        # AT#E2SLRI=<enable>: Enable Socket Listen Ring Indicator
        # This ensures we get #SRING URCs when data arrives
        response = sbc_cmd_with_timeout(
            "AT#E2SLRI=1\r", serial_connection, verbose=verbose
        )
        if "OK" not in response:
            logging.warning(
                "Could not enable E2SLRI (may not be supported on this firmware)"
            )

        logging.info("Modem TCP configuration completed successfully")
        return (0, "")

    except serial.SerialException as e:
        return (10, f"Serial communication error: {str(e)}")
    except Exception as e:
        return (11, f"Unexpected error during modem configuration: {str(e)}")
