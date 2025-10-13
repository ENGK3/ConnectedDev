import argparse
import logging
import logging.handlers
import re
import subprocess
import time
from pathlib import Path
from typing import Tuple

import serial

# Timeout constants
DEFAULT_RESPONSE_TIMEOUT = 30  # seconds
AT_COMMAND_TIMEOUT = 5  # seconds for AT command responses
SOCKET_CONNECT_TIMEOUT = 30  # seconds for socket connection


def sbc_cmd(cmd: str, serial_connection: serial.Serial, verbose: bool) -> str:
    """
    Send a command to the SBC and return the response.
    Handles unsolicited responses that may come between echo and OK.
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
        cmd: AT command string to send (should include \r termination)
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
        max_no_data_iterations = (
            10  # Maximum iterations with no data before giving up early
        )

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
                if response_lines and no_data_count > max_no_data_iterations:
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


def check_network_status(
    serial_connection: serial.Serial, verbose: bool = False
) -> None:
    """
    Check and log network registration and signal quality before sending data.
    Sends AT+CREG?, AT+CGREG?, and AT+CSQ to the modem and logs the results.
    """
    try:
        creg = sbc_cmd_with_timeout("AT+CREG?\r", serial_connection, verbose=False)
        cgreg = sbc_cmd_with_timeout("AT+CGREG?\r", serial_connection, verbose=False)
        csq = sbc_cmd_with_timeout("AT+CSQ\r", serial_connection, verbose=False)
        logging.info(f"Network registration (AT+CREG?): {creg.strip()}")
        logging.info(f"GPRS registration (AT+CGREG?): {cgreg.strip()}")
        logging.info(f"Signal quality (AT+CSQ): {csq.strip()}")
    except Exception as e:
        logging.error(f"Error checking network status: {e}")


def get_modem_info(
    serial_connection: serial.Serial, verbose: bool = False
) -> Tuple[str, str, str]:
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
    iccid = ""
    imei = ""
    imsi = ""

    try:
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

    return (iccid, imei, imsi)


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


def send_tcp_packet(
    hostname: str,
    port: int,
    data: str,
    serial_connection: serial.Serial,
    timeout: float = DEFAULT_RESPONSE_TIMEOUT,
    verbose: bool = False,
) -> Tuple[int, str]:
    """
    Send a TCP packet to a server using the Telit LE910C1 modem and wait for response.

    This function:
    - Configures the modem for TCP (if needed)
    - Opens a TCP socket to the specified host:port
    - Sends the data string
    - Waits for a response with timeout
    - Closes the socket

    Args:
        hostname: Server hostname or IP address
        port: Server TCP port number
        data: String data to send
        serial_connection: Open serial connection to the modem (/dev/ttyUSB2 typically)
        timeout: Timeout in seconds to wait for response (default: 30)
        verbose: Enable verbose logging

    Returns:
        Tuple of (error_code, response_string)
        - (0, response_data) on success
        - (non-zero, "") on error

    Error codes:
        0: Success
        1-11: Modem configuration errors (see configure_modem_tcp)
        20: Socket configuration error
        21: Socket connection error
        22: Socket send error
        23: Socket receive timeout
        24: Socket receive error
        25: Socket close error
    """
    socket_id = 1  # Use socket ID 1

    try:
        # Check network registration and signal quality before sending data
        check_network_status(serial_connection, verbose=verbose)
        # Step 1: Configure modem for TCP
        logging.info("Configuring modem for TCP communication...")
        error_code, error_msg = configure_modem_tcp(serial_connection, verbose=verbose)
        if error_code != 0:
            logging.error(f"Modem configuration failed: {error_msg}")
            return (error_code, "")

        # Step 2: Configure socket
        logging.info(f"Configuring socket {socket_id} for TCP...")
        # AT#SCFG=<socketId>,<cid>,<pktSz>,<maxTo>,<connTo>,<txTo>
        # Using context 1, packet size 1500, max timeout 90s,
        # connect timeout 600s, tx timeout 50s
        response = sbc_cmd_with_timeout(
            f"AT#SCFG={socket_id},1,1500,90,600,50\r",
            serial_connection,
            verbose=verbose,
        )
        if "OK" not in response:
            logging.error(f"Socket configuration failed: {response}")
            return (20, "")

        # Step 3: Open socket connection in COMMAND MODE
        # AT#SD=<socketId>,<protocol>,<port>,<IPaddr>,<closureType>,<localPort>,
        # <connMode> connMode=1 means command mode (requires AT#SSEND to send data)
        # connMode=0 means data mode (can write data directly after CONNECT)
        logging.info(f"Opening TCP connection to {hostname}:{port} in command mode...")
        response = sbc_cmd_with_timeout(
            f'AT#SD={socket_id},0,{port},"{hostname}",0,0,1\r',
            serial_connection,
            timeout=SOCKET_CONNECT_TIMEOUT,
            verbose=verbose,
        )

        # Check for OK response when starting in command mode
        if "OK" not in response:
            logging.error(f"Socket connection failed: {response}")
            # Try to close socket if it was partially opened
            sbc_cmd_with_timeout(
                f"AT#SH={socket_id}\r", serial_connection, verbose=verbose
            )
            return (21, "")

        logging.info("TCP connection established in command mode")

        # Step 4: Send data using AT#SSEND (command mode)
        logging.info(
            f"Sending data: {data[:50]}..."
            if len(data) > 50
            else f"Sending data: {data}"
        )

        # Calculate data length
        data_length = len(data)

        # Use AT#SSENDEXT for sending data in command mode
        # AT#SSENDEXT=<socketId>,<bytesToSend>
        response = sbc_cmd_with_timeout(
            f"AT#SSENDEXT={socket_id},{data_length}\r",
            serial_connection,
            timeout=5,
            verbose=verbose,
        )

        # After receiving the prompt (usually ">"), send the actual data
        if ">" in response or "SSENDEXT:" in response:
            # Send the actual data
            serial_connection.write(data.encode())

            # Wait for OK response
            start_time = time.time()
            send_response = ""
            while (time.time() - start_time) < 10:  # 10 second timeout for send
                if serial_connection.in_waiting > 0:
                    line = (
                        serial_connection.readline()
                        .decode("utf-8", errors="ignore")
                        .strip()
                    )
                    send_response += line + "\n"
                    if "OK" in line or "ERROR" in line:
                        break
                time.sleep(0.05)

            if verbose:
                logging.info(f"Send response: {send_response}")

            if "OK" not in send_response:
                logging.error(f"Failed to send data: {send_response}")
                sbc_cmd_with_timeout(
                    f"AT#SH={socket_id}\r", serial_connection, verbose=verbose
                )
                return (22, "")
        else:
            logging.error(f"Did not receive prompt for AT#SSENDEXT: {response}")
            sbc_cmd_with_timeout(
                f"AT#SH={socket_id}\r", serial_connection, verbose=verbose
            )
            return (22, "")

        # Step 5: Read response with timeout
        logging.info(f"Waiting for response (timeout: {timeout}s)...")

        # In command mode, we need to wait for the #SRING URC (unsolicited result code)
        # which indicates data has arrived. The data may be included in the URC itself
        # for small responses, or we may need to use AT#SRECV to retrieve it.
        received_data = ""
        start_time = time.time()
        sring_line = ""

        # Wait for #SRING notification or timeout
        logging.info("Waiting for incoming data notification (#SRING)...")
        while (time.time() - start_time) < timeout:
            if serial_connection.in_waiting > 0:
                line = (
                    serial_connection.readline()
                    .decode("utf-8", errors="ignore")
                    .strip()
                )
                if verbose:
                    logging.debug(f"Received: {line}")

                # Check for #SRING: <socketId>,<dataLen>[,<data>] or
                # SRING: <socketId>,<dataLen>[,<data>]
                if line.startswith("#SRING:") or line.startswith("SRING:"):
                    sring_line = line
                    logging.info(f"Data arrival notification received: {line}")
                    break
            time.sleep(0.1)

        if sring_line:
            # Parse #SRING format: SRING: <socketId>,<dataLen>[,<data>]
            # or #SRING: <socketId>,<dataLen>[,<data>]
            # If data is small enough, it may be included directly in the URC

            # Remove the prefix
            if sring_line.startswith("#SRING:"):
                parts = sring_line[7:].strip()  # Remove "#SRING:"
            else:
                parts = sring_line[6:].strip()  # Remove "SRING:"

            # Split by comma
            sring_parts = parts.split(",", 2)  # Split into at most 3 parts

            if len(sring_parts) >= 3:
                # Data is included in the SRING notification
                data_len = int(sring_parts[1].strip())
                received_data = sring_parts[2].strip()
                logging.info(
                    f"Data retrieved from #SRING notification: '{received_data}' "
                    f"({data_len} bytes)"
                )
            elif len(sring_parts) >= 2:
                # Data not included, need to retrieve with AT#SRECV
                data_len = int(sring_parts[1].strip())
                logging.info(
                    f"#SRING indicates {data_len} bytes available, retrieving "
                    "with AT#SRECV..."
                )

                response = sbc_cmd_with_timeout(
                    f"AT#SRECV={socket_id},1500\r",
                    serial_connection,
                    timeout=5,
                    verbose=verbose,
                )

                if "#SRECV:" in response:
                    # Parse response: #SRECV: <socketId>,<datalen>
                    # Followed by the actual data
                    lines = response.split("\n")
                    for i, line in enumerate(lines):
                        if line.startswith("#SRECV:"):
                            # Extract data length
                            recv_parts = line.split(",")
                            if len(recv_parts) >= 2:
                                try:
                                    recv_len = int(recv_parts[1].strip())
                                    if recv_len > 0 and i + 1 < len(lines):
                                        # Next line(s) contain the data
                                        received_data = "\n".join(lines[i + 1 :])
                                        # Trim to expected length
                                        received_data = received_data[:recv_len]
                                        logging.info(
                                            f"Retrieved {recv_len} bytes of data "
                                            f"via AT#SRECV"
                                        )
                                except ValueError:
                                    pass
                            break
        else:
            logging.warning("No #SRING notification received within timeout period")

        # Step 6: Close socket
        logging.info("Closing socket...")
        response = sbc_cmd_with_timeout(
            f"AT#SH={socket_id}\r", serial_connection, verbose=verbose
        )

        if received_data:
            logging.info(
                f"Received response: {received_data[:100]}..."
                if len(received_data) > 100
                else f"Received response: {received_data}"
            )
            return (0, received_data)
        else:
            logging.warning("No response received within timeout period")
            return (23, "")

    except serial.SerialException as e:
        logging.error(f"Serial communication error: {str(e)}")
        # Try to close socket on error
        try:
            sbc_cmd_with_timeout(
                f"AT#SH={socket_id}\r", serial_connection, verbose=False
            )
        except Exception:
            pass
        return (24, "")

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        # Try to close socket on error
        try:
            sbc_cmd_with_timeout(
                f"AT#SH={socket_id}\r", serial_connection, verbose=False
            )
        except Exception:
            pass
        return (24, "")


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


def sbc_connect(serial_connection: serial.Serial):
    serial_connection.port = "/dev/ttyUSB2"
    serial_connection.baudrate = 115200
    serial_connection.timeout = 30
    serial_connection.xonxoff = False
    print(
        f"Connecting to SBC on port {serial_connection.port} "
        f"with baud rate {serial_connection.baudrate}"
    )
    try:
        print(serial_connection.is_open)
        serial_connection.open()
        serial_connection.write(b"ATE0\r")
        response = serial_connection.readline()
        response = serial_connection.readline()
        print(f"SBC connected successfully?: {response.decode().strip()}")
        print(serial_connection.is_open)

    except Exception as e:
        logging.error(f"Failed to connect to SBC: {e}")
    return serial_connection.is_open


def start_reg_again(serial_connection: serial.Serial):
    logging.info("Starting registration process again")
    sbc_cmd("AT+COPS=2\r", serial_connection, verbose=True)
    sbc_cmd("AT+COPS=0\r", serial_connection, verbose=True)


def check_registration(serial_connection: serial.Serial):
    response = sbc_cmd("AT+CEREG?\r", serial_connection, verbose=True)
    if response.startswith("+CEREG:"):
        parts = response.split(",")
        if len(parts) > 1:
            stat = parts[1].strip()
            if stat in ["1", "5"]:
                logging.info(f"Modem registered: stat={stat}")
                return True
            else:
                logging.info(f"Modem not registered yet: stat={stat}")
                start_reg_again(serial_connection)

    return False


def sbc_disconnect(serial_connection: serial.Serial):
    serial_connection.close()
    logging.info(f"Disconnected from SBC on port {serial_connection.port}")


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
        "-H",
        "--hostname",
        type=str,
        help="Server hostname for TCP packet",
        default="m90events.devkingsiii.com",
    )
    parser.add_argument(
        "-p", "--port", type=int, help="Server port for TCP packet", default=10083
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

            # Build the event data packet
            event_data = (
                f"START CID=5822460189|AC=C12345|EC=01|MDL=Q01|APP=03020089|CRC = BEEF|"
                f"BOOT = 03010007|TSPV=25.21.260-P0F.261803|CCI={iccid}|"
                f"IMSI={imsi}|IMEI={imei}|"
                f"NET=4G|APN=broadband|IMS=1|SS=067|RSRP=098|RSRQ=011|TMP1=+020|TMP2=+020|"
                f"BAT=1305|ZLST=01|STM=0450946E|UTM=02EBA09E|RST=0|PIN=1|THW=1.10 END"
            )

            logging.info(f"Sending TCP packet to {args.hostname}:{args.port}")
            error_code, response = send_tcp_packet(
                hostname=args.hostname,
                port=args.port,
                data=event_data,
                serial_connection=serial_connection,
                timeout=30,
                verbose=args.verbose,
            )

            if error_code == 0:
                logging.info("TCP packet sent successfully!")
                logging.info(f"Server response: {response}")
            else:
                logging.error(f"TCP packet send failed with error code: {error_code}")
                # Continue with call even if packet send fails
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
