import argparse
import logging
import time
from typing import Tuple

import serial

# Import shared modem utilities
from modem_utils import (
    check_network_status,
    configure_modem_tcp,
    get_modem_info,
    get_software_package_version,
    sbc_cmd_with_timeout,
    sbc_connect,
    sbc_disconnect,
)

# Timeout constants
DEFAULT_RESPONSE_TIMEOUT = 30  # seconds
SOCKET_CONNECT_TIMEOUT = 30  # seconds for socket connection


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
        # AT#SCFG=<socketId>,<CID>,<pktSz>,<maxTo>,<connTo>,<txTo>
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


if __name__ == "__main__":
    # Set up logging to syslog with milliseconds in timestamp

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s.%(msecs)03d %(levelname)-8s [TCP] %(message)s",
        datefmt="%m-%d %H:%M:%S",
        filename="/mnt/data/calls.log",
        filemode="a+",
    )

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d:%(levelname)-8s [TCP] %(message)s", datefmt="%H:%M:%S"
    )
    formatter.default_msec_format = "%s.%03d"
    console.setFormatter(formatter)
    logging.getLogger("").addHandler(console)

    parser = argparse.ArgumentParser(
        description="Send INFO TCP packet via modem to EDC server"
    )

    parser.add_argument(
        "-e",
        "--ecode",
        type=str,
        help="The elevator error code to include in the packet",
        default="01",
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
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    logging.info("=" * 60)
    logging.info("Retrieving modem information for TCP packet...")

    serial_connection = serial.Serial()
    # Use the second file handle to the modem for the TCP configuration
    # and sending of the packet. The first handle is used for call placement
    # and in the case of the second elevator, the first handle is busy in a call.
    if sbc_connect(serial_connection, port="/dev/ttyUSB3"):
        configure_modem_tcp(serial_connection, verbose=args.verbose)

        iccid, imei, imsi = get_modem_info(serial_connection, verbose=args.verbose)

        # Gather the various data fields from the configuration file for
        # CID: 5822460189
        # AC: C12345
        # TSPV: should come from the modem : 25.21.260-P0F.261803
        # MDL: Q01
        # APN comes from the modem
        #
        CID = "5822460189"
        AC = "C12345"
        MDL = "Q01"
        APN = "broadband"
        UTM = "02EBA09E"  # Should come from the modem.
        bat_voltage = "1305"  # Should come from the latest reading of the system.

        TSPV = get_software_package_version(serial_connection, verbose=args.verbose)

        # Build the event data packet
        event_data = (
            f"START CID={CID}|AC={AC}|EC={args.ecode}|MDL={MDL}|"
            f"APP=03020089|CRC=BEEF|"
            f"BOOT=03010007|TSPV={TSPV}|CCI={iccid}|"
            f"IMSI={imsi}|IMEI={imei}|"
            f"NET=4G|APN={APN}|IMS=1|SS=067|RSRP=098|RSRQ=011|"
            f"TMP1=+020|TMP2=+020|"
            f"BAT={bat_voltage}|ZLST=01|STM=0450946E|UTM={UTM}|RST=0|PIN=1|THW=1.10 END"
        )

        logging.info(f"Event data being sent: {event_data}")
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

        sbc_disconnect(serial_connection)
