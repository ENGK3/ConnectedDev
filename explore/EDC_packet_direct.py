#!/usr/bin/env python3
"""
EDC_packet_direct.py - Direct TCP packet transmission (no modem AT commands)

This script mimics the main() logic of EDC_packet.py, but sends the packet using a
standard TCP socket instead of using the Telit LE910C1 modem AT command interface.
"""

import logging
import socket


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    # Example: Set up host, port, and event data
    hostname = "m90events.devkingsiii.com"
    port = 10083
    # These would normally be retrieved from the modem, but we'll use placeholders
    iccid = "89010303300044214949"
    imei = "352176536546312"
    imsi = "310030004421494"
    event_data = (
        f"START CID=5822460189|AC=C12345|EC=01|MDL=Q01|APP=03020089|CRC = "
        f"BEEF|BOOT = 03010007|TSPV=25.21.260-P0F.261803|CCI={iccid}|IMSI={imsi}|"
        f"IMEI={imei}|NET=4G|APN=broadband|IMS=1|SS=067|RSRP=098|RSRQ=011|TMP1=+020|"
        f"TMP2=+020|BAT=1305|ZLST=01|STM=0450946E|UTM=02EBA09E|RST=0|PIN=1|THW=1.10 END"
    )

    logging.info(f"Connecting to {hostname}:{port} via direct TCP socket...")
    try:
        with socket.create_connection((hostname, port), timeout=10) as sock:
            logging.info(f"Sending event data: {event_data}")
            sock.sendall(event_data.encode())
            sock.settimeout(10)
            try:
                response = sock.recv(4096)
                if response:
                    logging.info(
                        f"Received response: {response.decode(errors='ignore')}"
                    )
                else:
                    logging.warning("No response received from server.")
            except socket.timeout:
                logging.warning("Timed out waiting for response from server.")
    except Exception as e:
        logging.error(f"Socket error: {e}")


if __name__ == "__main__":
    main()
