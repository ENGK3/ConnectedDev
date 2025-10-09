#!/usr/bin/env python3
"""
EDC_packet.py - TCP packet transmission using Telit LE910C1 modem

This module provides functions to configure the Telit LE910C1 modem for TCP
communication and send/receive data packets over TCP connections.
"""

import serial
import time
import logging
from typing import Tuple

# Timeout constants
DEFAULT_RESPONSE_TIMEOUT = 30  # seconds
AT_COMMAND_TIMEOUT = 5  # seconds for AT command responses
SOCKET_CONNECT_TIMEOUT = 30  # seconds for socket connection

# --- Network check utility ---
def check_network_status(serial_connection: serial.Serial, verbose: bool = False) -> None:
    """
    Check and log network registration and signal quality before sending data.
    Sends AT+CREG?, AT+CGREG?, and AT+CSQ to the modem and logs the results.
    """
    try:
        creg = sbc_cmd("AT+CREG?\r", serial_connection, verbose=verbose)
        cgreg = sbc_cmd("AT+CGREG?\r", serial_connection, verbose=verbose)
        csq = sbc_cmd("AT+CSQ\r", serial_connection, verbose=verbose)
        logging.info(f"Network registration (AT+CREG?): {creg.strip()}")
        logging.info(f"GPRS registration (AT+CGREG?): {cgreg.strip()}")
        logging.info(f"Signal quality (AT+CSQ): {csq.strip()}")
    except Exception as e:
        logging.error(f"Error checking network status: {e}")


def sbc_cmd(cmd: str, serial_connection: serial.Serial,
            timeout: float = AT_COMMAND_TIMEOUT,
            verbose: bool = False) -> str:
    """
    Send an AT command to the LE910C1 modem and return the response.

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

    serial_connection.write(cmd.encode())

    # Read echo (if echo is enabled)
    response_lines = []
    start_time = time.time()

    while (time.time() - start_time) < timeout:
        if serial_connection.in_waiting > 0:
            line = serial_connection.readline().decode('utf-8', errors='ignore').strip()
            if line and line != cmd.strip():
                response_lines.append(line)
                if verbose:
                    logging.debug(f"Response line: {line}")
                # Check for common response terminators
                if line in ['OK', 'ERROR', 'CONNECT'] or line.startswith('+CME ERROR') or line.startswith('+CMS ERROR'):
                    break
        time.sleep(0.05)

    response = '\n'.join(response_lines)

    if verbose:
        logging.info(f"Full response: {response}")

    return response


def get_modem_info(serial_connection: serial.Serial,
                   verbose: bool = False) -> Tuple[str, str, str]:
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
        response = sbc_cmd("AT#CCID\r", serial_connection, verbose=verbose)
        if "#CCID:" in response:
            # Parse: #CCID: 89012345678901234567
            for line in response.split('\n'):
                if "#CCID:" in line:
                    iccid = line.split(':')[1].strip()
                    break
        else:
            # Try alternative command
            response = sbc_cmd("AT+ICCID\r", serial_connection, verbose=verbose)
            if "+ICCID:" in response:
                for line in response.split('\n'):
                    if "+ICCID:" in line:
                        iccid = line.split(':')[1].strip()
                        break

        if verbose and iccid:
            logging.info(f"ICCID: {iccid}")

        # Get IMEI - Device identifier
        # AT command: AT+CGSN or AT#CGSN
        # Response format: <imei> followed by OK
        response = sbc_cmd("AT+CGSN\r", serial_connection, verbose=verbose)
        # IMEI is typically 15 digits and appears before OK
        for line in response.split('\n'):
            line = line.strip()
            # IMEI is numeric and 15 digits
            if line.isdigit() and len(line) == 15:
                imei = line
                break
            # Sometimes it has additional info, try to extract just the number
            elif line and line[0].isdigit() and 'OK' not in line:
                # Extract just the numeric part
                numeric_part = ''.join(filter(str.isdigit, line))
                if len(numeric_part) == 15:
                    imei = numeric_part
                    break

        if verbose and imei:
            logging.info(f"IMEI: {imei}")

        # Get IMSI - Subscriber identifier
        # AT command: AT+CIMI
        # Response format: <imsi> followed by OK
        response = sbc_cmd("AT+CIMI\r", serial_connection, verbose=verbose)
        # IMSI is typically 14-15 digits and appears before OK
        for line in response.split('\n'):
            line = line.strip()
            # IMSI is numeric and 14-15 digits
            if line.isdigit() and len(line) >= 14 and len(line) <= 15:
                imsi = line
                break
            # Sometimes it has additional info, try to extract just the number
            elif line and line[0].isdigit() and 'OK' not in line:
                # Extract just the numeric part
                numeric_part = ''.join(filter(str.isdigit, line))
                if len(numeric_part) >= 14 and len(numeric_part) <= 15:
                    imsi = numeric_part
                    break

        if verbose and imsi:
            logging.info(f"IMSI: {imsi}")

        if verbose:
            logging.info(f"Modem info retrieved - ICCID: {iccid}, IMEI: {imei}, IMSI: {imsi}")

    except Exception as e:
        logging.error(f"Error retrieving modem information: {str(e)}")

    return (iccid, imei, imsi)


def configure_modem_tcp(serial_connection: serial.Serial,
                        context_id: int = 1,
                        verbose: bool = False) -> Tuple[int, str]:
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
        response = sbc_cmd("ATE0\r", serial_connection, verbose=verbose)

        # Check if modem is responsive
        response = sbc_cmd("AT\r", serial_connection, verbose=verbose)
        if "OK" not in response:
            return (1, "Modem not responding to AT commands")

        response = sbc_cmd("AT+CMEE=2\r", serial_connection, verbose=verbose)
        if "OK" not in response:
            return (1, "Modem not responding to CMEE commands")

        # Check network registration
        response = sbc_cmd("AT+CEREG?\r", serial_connection, verbose=verbose)
        if "+CEREG:" in response:
            # Parse registration status
            # Response format: +CEREG: <n>,<stat>[,...]
            # stat: 1=registered home, 5=registered roaming
            parts = response.split(',')
            if len(parts) >= 2:
                stat = parts[1].strip().split('\n')[0]
                if stat not in ['1', '5']:
                    return (2, f"Modem not registered on network (stat={stat})")
        else:
            return (2, "Could not query network registration status")

        # Check if context is already active
        response = sbc_cmd(f"AT#SGACT?\r", serial_connection, verbose=verbose)
        context_active = False
        if f"#SGACT: {context_id},1" in response:
            context_active = True
            logging.info(f"Context {context_id} is already active")

        # Activate context if not already active
        if not context_active:

            # Don't fool with the APN settings. Most carriers auto-configure.
            # Define PDP context (if not already defined)
            # Most carriers auto-configure, but we'll set a generic APN
            # response = sbc_cmd(f'AT+CGDCONT={context_id},"IPV4V6","nxtgenphone"\r',
            #                  serial_connection, verbose=verbose)
            # if "OK" not in response:
            #     logging.warning("Could not set PDP context definition (may already be set)")

            # Activate PDP context
            logging.info(f"Activating PDP context {context_id}...")
            response = sbc_cmd(f"AT#SGACT={context_id},1\r",
                             serial_connection,
                             timeout=60,  # Context activation can take longer
                             verbose=verbose)

            if "OK" not in response and "#SGACT:" not in response:
                return (3, f"Failed to activate PDP context: {response}")

        # Configure socket parameters
        # Set packet size to 1500 bytes (typical MTU)
        response = sbc_cmd("AT#SCFG=1,1,1500,90,600,50\r",
                          serial_connection, verbose=verbose)

        # Extended configuration - TCP parameters
        # AT#SCFGEXT=<socketId>,<srMode>,<recvDataMode>,<keepalive>,<listenAutoRsp>,<sendDataMode>
        # srMode=2: Enable all socket ring unsolicited messages (CRITICAL for command mode)
        # This enables #SRING notifications when data arrives
        response = sbc_cmd("AT#SCFGEXT=1,2,0,30,0,0\r",
                          serial_connection, verbose=verbose)

        # Enable unsolicited socket event reporting
        # AT#E2SLRI=<enable>: Enable Socket Listen Ring Indicator
        # This ensures we get #SRING URCs when data arrives
        response = sbc_cmd("AT#E2SLRI=1\r",
                          serial_connection, verbose=verbose)
        if "OK" not in response:
            logging.warning("Could not enable E2SLRI (may not be supported on this firmware)")

        logging.info("Modem TCP configuration completed successfully")
        return (0, "")

    except serial.SerialException as e:
        return (10, f"Serial communication error: {str(e)}")
    except Exception as e:
        return (11, f"Unexpected error during modem configuration: {str(e)}")


def send_tcp_packet(hostname: str,
                    port: int,
                    data: str,
                    serial_connection: serial.Serial,
                    timeout: float = DEFAULT_RESPONSE_TIMEOUT,
                    verbose: bool = False) -> Tuple[int, str]:
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
        # Using context 1, packet size 1500, max timeout 90s, connect timeout 600s, tx timeout 50s
        response = sbc_cmd(f"AT#SCFG={socket_id},1,1500,90,600,50\r",
                          serial_connection, verbose=verbose)
        if "OK" not in response:
            logging.error(f"Socket configuration failed: {response}")
            return (20, "")

        # Step 3: Open socket connection in COMMAND MODE
        # AT#SD=<socketId>,<protocol>,<port>,<IPaddr>,<closureType>,<localPort>,<connMode>
        # connMode=1 means command mode (requires AT#SSEND to send data)
        # connMode=0 means data mode (can write data directly after CONNECT)
        logging.info(f"Opening TCP connection to {hostname}:{port} in command mode...")
        response = sbc_cmd(f'AT#SD={socket_id},0,{port},"{hostname}",0,0,1\r',
                          serial_connection,
                          timeout=SOCKET_CONNECT_TIMEOUT,
                          verbose=verbose)

        # Check for OK response when starting in command mode
        if "OK" not in response:
            logging.error(f"Socket connection failed: {response}")
            # Try to close socket if it was partially opened
            sbc_cmd(f"AT#SH={socket_id}\r", serial_connection, verbose=verbose)
            return (21, "")

        logging.info("TCP connection established in command mode")

        # Step 4: Send data using AT#SSEND (command mode)
        logging.info(f"Sending data: {data[:50]}..." if len(data) > 50 else f"Sending data: {data}")

        # Calculate data length
        data_length = len(data)

        # Use AT#SSENDEXT for sending data in command mode
        # AT#SSENDEXT=<socketId>,<bytesToSend>
        response = sbc_cmd(f"AT#SSENDEXT={socket_id},{data_length}\r",
                          serial_connection,
                          timeout=5,
                          verbose=verbose)

        # After receiving the prompt (usually ">"), send the actual data
        if ">" in response or "SSENDEXT:" in response:
            # Send the actual data
            serial_connection.write(data.encode())

            # Wait for OK response
            start_time = time.time()
            send_response = ""
            while (time.time() - start_time) < 10:  # 10 second timeout for send
                if serial_connection.in_waiting > 0:
                    line = serial_connection.readline().decode('utf-8', errors='ignore').strip()
                    send_response += line + "\n"
                    if "OK" in line or "ERROR" in line:
                        break
                time.sleep(0.05)

            if verbose:
                logging.info(f"Send response: {send_response}")

            if "OK" not in send_response:
                logging.error(f"Failed to send data: {send_response}")
                sbc_cmd(f"AT#SH={socket_id}\r", serial_connection, verbose=verbose)
                return (22, "")
        else:
            logging.error(f"Did not receive prompt for AT#SSENDEXT: {response}")
            sbc_cmd(f"AT#SH={socket_id}\r", serial_connection, verbose=verbose)
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
                line = serial_connection.readline().decode('utf-8', errors='ignore').strip()
                if verbose:
                    logging.debug(f"Received: {line}")

                # Check for #SRING: <socketId>,<dataLen>[,<data>] or SRING: <socketId>,<dataLen>[,<data>]
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
            sring_parts = parts.split(',', 2)  # Split into at most 3 parts

            if len(sring_parts) >= 3:
                # Data is included in the SRING notification
                data_len = int(sring_parts[1].strip())
                received_data = sring_parts[2].strip()
                logging.info(f"Data retrieved from #SRING notification: '{received_data}' ({data_len} bytes)")
            elif len(sring_parts) >= 2:
                # Data not included, need to retrieve with AT#SRECV
                data_len = int(sring_parts[1].strip())
                logging.info(f"#SRING indicates {data_len} bytes available, retrieving with AT#SRECV...")

                response = sbc_cmd(f"AT#SRECV={socket_id},1500\r",
                                  serial_connection,
                                  timeout=5,
                                  verbose=verbose)

                if "#SRECV:" in response:
                    # Parse response: #SRECV: <socketId>,<datalen>
                    # Followed by the actual data
                    lines = response.split('\n')
                    for i, line in enumerate(lines):
                        if line.startswith("#SRECV:"):
                            # Extract data length
                            recv_parts = line.split(',')
                            if len(recv_parts) >= 2:
                                try:
                                    recv_len = int(recv_parts[1].strip())
                                    if recv_len > 0 and i + 1 < len(lines):
                                        # Next line(s) contain the data
                                        received_data = '\n'.join(lines[i+1:])
                                        # Trim to expected length
                                        received_data = received_data[:recv_len]
                                        logging.info(f"Retrieved {recv_len} bytes of data via AT#SRECV")
                                except ValueError:
                                    pass
                            break
        else:
            logging.warning("No #SRING notification received within timeout period")

        # Step 6: Close socket
        logging.info("Closing socket...")
        response = sbc_cmd(f"AT#SH={socket_id}\r",
                          serial_connection,
                          verbose=verbose)

        if received_data:
            logging.info(f"Received response: {received_data[:100]}..." if len(received_data) > 100 else f"Received response: {received_data}")
            return (0, received_data)
        else:
            logging.warning("No response received within timeout period")
            return (23, "")

    except serial.SerialException as e:
        logging.error(f"Serial communication error: {str(e)}")
        # Try to close socket on error
        try:
            sbc_cmd(f"AT#SH={socket_id}\r", serial_connection, verbose=False)
        except:
            pass
        return (24, "")

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        # Try to close socket on error
        try:
            sbc_cmd(f"AT#SH={socket_id}\r", serial_connection, verbose=False)
        except:
            pass
        return (24, "")


def main():
    """
    Example usage and testing of the TCP packet functions.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
        datefmt='%H:%M:%S'
    )

    # Example: Connect to modem and send a simple HTTP request
    modem_port = "/dev/ttyUSB2"
    modem = serial.Serial()
    modem.port = modem_port
    modem.baudrate = 115200
    modem.timeout = 1

    try:
        logging.info(f"Opening modem connection on {modem_port}...")
        modem.open()

        # Get modem information first
        logging.info("=" * 60)
        logging.info("Retrieving modem information...")
        iccid, imei, imsi = get_modem_info(modem, verbose=True)
        logging.info("=" * 60)
        logging.info(f"ICCID: {iccid}")
        logging.info(f"IMEI:  {imei}")
        logging.info(f"IMSI:  {imsi}")
        logging.info("=" * 60)

        # Example TCP packet send
        hostname = "m90events.devkingsiii.com"
        port = 10083
        event_data = f"START CID=5822460189|AC=C12345|EC=01|MDL=Q01|APP=03020089|CRC = BEEF|BOOT = 03010007|TSPV=25.21.260-P0F.261803|CCI={iccid}|IMSI={imsi}|IMEI={imei}|NET=4G|APN=broadband|IMS=1|SS=067|RSRP=098|RSRQ=011|TMP1=+020|TMP2=+020|BAT=1305|ZLST=01|STM=0450946E|UTM=02EBA09E|RST=0|PIN=1|THW=1.10 END"

        logging.info(f"Sending Event request to {hostname}:{port}")
        error_code, response = send_tcp_packet(
            hostname=hostname,
            port=port,
            data=event_data,
            serial_connection=modem,
            timeout=30,
            verbose=True
        )

        if error_code == 0:
            logging.info("SUCCESS!")
            logging.info(f"Response:\n{response}")
        else:
            logging.error(f"FAILED with error code: {error_code}")

    except Exception as e:
        logging.error(f"Error: {e}")

    finally:
        if modem.is_open:
            modem.close()
            logging.info("Modem connection closed")


if __name__ == "__main__":
    main()
