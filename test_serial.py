import serial
import time
import argparse
import subprocess
import signal
import os

def sbc_cmd(cmd: str, serial_connection: serial.Serial, verbose: bool) -> str:
    """
    Send a command to the SBC and return the response.
    """
    if verbose:
        print(f"Sending command: {cmd.strip()}")
    serial_connection.write(cmd.encode())
    
    #response = serial_connection.read(serial_connection.in_waiting or 1)
    response = serial_connection.readline()
    response = serial_connection.readline()  # Read the response
    if verbose:
        print(f"Response: {response.decode().strip()}")
    return response.decode().strip()

def start_audio_bridge():
    """
    Start the two audio bridge shell commands as background processes.
    Returns a tuple of their PIDs (pid1, pid2).
    """
    cmd1 = ["arecord", "-D", "hw:CARD=LE910C1NF,0", "-f", "S16_LE", "-r", "16000"]
    cmd2 = ["arecord", "-D", "hw:sgtl5000audio,0",  "-f", "S16_LE", "-r", "16000"]
    aplay1 = ["aplay", "-D", "hw:sgtl5000audio,0", "-f", "S16_LE", "-r", "16000"]
    aplay2 = ["aplay", "-D", "hw:CARD=LE910C1NF,0",  "-f", "S16_LE", "-r", "16000"]

    # Start first pipeline
    p1_arecord = subprocess.Popen(cmd1, stdout=subprocess.PIPE)
    p1_aplay = subprocess.Popen(aplay1, stdin=p1_arecord.stdout)
    # Start second pipeline
    p2_arecord = subprocess.Popen(cmd2, stdout=subprocess.PIPE)
    p2_aplay = subprocess.Popen(aplay2, stdin=p2_arecord.stdout)

    # Return the PIDs of the aplay processes (since arecord will exit if aplay is killed)
    return (p1_aplay.pid, p2_aplay.pid)
    # return (p1_aplay.pid)

def terminate_pids(pid_list):
    """
    Terminate the processes with the given list of PIDs.
    """
    for pid in pid_list:
        try:
            # Send SIGTERM first
            os.kill(pid, signal.SIGTERM)
        except Exception as e:
            print(f"Failed to terminate PID {pid}: {e}")

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
        "AT#ADSPC=6\r",
        "AT+CLVL=0\r",
        "AT+CIND=0,0,1,0,1,1,1,1,0,1,0\r"
    ]

    for cmd in at_cmd_set:
        sbc_cmd(cmd, serial_connection, verbose)


def sbc_place_call(number: str, modem: serial.Serial, verbose: bool = True):

    sbc_config_call(modem, verbose)

    sbc_cmd(f"ATD{number};\r", modem, verbose)  # Place the call

    # now wait for connection and check for errors

    # When the following are seen on the serial port.
    # "+CIEV: callsetup,3" and "+CIEV: callsetup,0"
    # the call got connected. 

    # When the "NO CARRIER" is seen the call has been Terminated

    audio_pids = None
    while True:
        response = modem.readline().decode().strip()
        print(f"Waiting for call response: {response}")
        
        if "+CIEV: call,1" in response:
            print("Call connected successfully.")
            #sbc_cmd("AT#ADSPC=6\r", modem)  # Connect the audio.
            # Start audio bridge here
            audio_pids = start_audio_bridge()
            print(f"Audio bridge started with PIDs: {audio_pids}")
        elif "+CIEV: call,0" in response:
            print("Call setup Terminated.")
            sbc_cmd("AT#ADSPC=0\r", modem, verbose)  # Connect the audio
            sbc_cmd("AT+CHUP\r", modem, verbose)
            # Terminate audio bridge if running
            if audio_pids:
                terminate_pids(audio_pids)
                print("Audio bridge terminated.")
        elif "NO CARRIER" in response:
            print("Call terminated")
            sbc_cmd("AT+CHUP\r", modem, verbose)
            # Terminate audio bridge if running
            if audio_pids:
                terminate_pids(audio_pids)
                print("Audio bridge terminated.")
            break
        time.sleep(0.5)  # Avoid busy waiting


def sbc_connect(serial_connection: serial.Serial):
    serial_connection.port = "/dev/ttyUSB2"
    serial_connection.baudrate = 115200
    serial_connection.timeout = 30
    serial_connection.xonxoff = False
    print(f"Connecting to SBC on port {serial_connection.port} with baud rate {serial_connection.baudrate}")
    try:
        print(serial_connection.is_open)
        serial_connection.open()
        serial_connection.write(b"ATE0\r")
        response = serial_connection.readline()
        response = serial_connection.readline()
        print(f"SBC connected successfully?: {response.decode().strip()}")  
        print(serial_connection.is_open)
        

    except Exception as e:
        print(f"Failed to connect to SBC: {e}")

    return serial_connection.is_open


def sbc_disconnect(serial_connection: serial.Serial):
    serial_connection.close()
    print(f"Disconnected from SBC on port {serial_connection.port}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serial SBC dialer")
    parser.add_argument("-n", "--number", type=str, help="Phone number to dial",
                        default="9723256826")
    parser.add_argument("-v", "--verbose", type=bool, default=False, help="Enable verbose output")
    args = parser.parse_args()

    serial_connection = serial.Serial()
    if sbc_connect(serial_connection):

        print(f"Ready to dial number: {args.number}")
        # Add dial logic here if needed, e.g.:
        # serial_connection.write(f'ATD{args.number};\r'.encode())
        # response = serial_connection.readline()
        # print(f"Dial response: {response.decode().strip()}")
        sbc_place_call(args.number, serial_connection, verbose=args.verbose)

    sbc_disconnect(serial_connection)