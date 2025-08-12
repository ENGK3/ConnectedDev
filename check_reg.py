import serial
import time
import sys

def check_modem_registration(port="/dev/ttyUSB2", baudrate=115200, timeout=30, max_wait=300):
    """
    Checks if the modem is registered on the network using AT+CEREG? command.
    Returns True if registered within max_wait seconds, else False.
    """
    time.sleep(5) 
    ser = serial.Serial()
    ser.port = port
    ser.baudrate = baudrate
    ser.timeout = timeout
    ser.xonxoff = False
    try:
        ser.open()
        ser.write(b"ATE0\r")
        ser.readline()
        ser.readline()
    except Exception as e:
        print(f"Failed to open serial port: {e}")
        return False

    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            ser.write(b"AT+CEREG?\r")
            response = ser.readline().decode(errors="ignore").strip()
            # Read until we get a line with +CEREG:
            while response and not response.startswith("+CEREG:"):
                response = ser.readline().decode(errors="ignore").strip()
            if response.startswith("+CEREG:"):
                # +CEREG: <n>,<stat>[,...]
                # stat: 1=registered (home), 5=registered (roaming)
                parts = response.split(",")
                if len(parts) > 1:
                    stat = parts[1].strip()
                    if stat in ["1", "5"]:
                        print(f"Modem registered: stat={stat}")
                        ser.close()
                        return True
                    else:
                        print(f"Modem not registered yet: stat={stat}")
            time.sleep(2)
            print(f"Waiting again {response}")
        except Exception as e:
            print(f"Error querying modem: {e}")
            time.sleep(5)
    ser.close()
    print("Registration timeout.")
    return False

if __name__ == "__main__":
    result = check_modem_registration()
    print(result)
    sys.exit(0 if result else 1)
