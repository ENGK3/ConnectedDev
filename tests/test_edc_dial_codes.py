"""
Unit tests for special dial code handling (*50, *54, *55 prefixes).

These tests verify that manage_modem correctly parses special dial codes
and strips the prefix before dialing:
1. *50 prefix is stripped and the actual number is dialed
2. *54 prefix is stripped and the actual number is dialed
3. *55 prefix is stripped and the actual number is dialed
4. Numbers without prefix are dialed as-is

Note: EDC packet sending is now handled externally and is not tested here.
"""

import logging
import os
import queue
import socket
import sys
import threading
import time

import pytest
import serial

# Add parent directory to path to import manage_modem
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "common")
)

from manage_modem import (
    DEFAULT_TCP_HOST,
    ModemStateMachine,
    ModemTCPServer,
    parse_special_dial_code,
)


class TestParseSpecialDialCode:
    """Test suite for the parse_special_dial_code function."""

    def test_parse_star50_prefix(self):
        """Test parsing *50 prefix - should disable EDC packet."""
        number = "*509723105316"
        actual_number, send_edc, edc_code = parse_special_dial_code(number)

        assert actual_number == "9723105316"
        assert send_edc is False
        assert edc_code is None

    def test_parse_star54_prefix(self):
        """Test parsing *54 prefix - should send EDC with 'DC' code."""
        number = "*548881237777"
        actual_number, send_edc, edc_code = parse_special_dial_code(number)

        assert actual_number == "8881237777"
        assert send_edc is True
        assert edc_code == "DC"

    def test_parse_star55_prefix(self):
        """Test parsing *55 prefix - should send EDC with normal code."""
        number = "*555551234567"
        actual_number, send_edc, edc_code = parse_special_dial_code(number)

        assert actual_number == "5551234567"
        assert send_edc is True
        assert edc_code is None

    def test_parse_normal_number(self):
        """Test parsing normal number - should send EDC by default."""
        number = "9723105316"
        actual_number, send_edc, edc_code = parse_special_dial_code(number)

        assert actual_number == "9723105316"
        assert send_edc is True
        assert edc_code is None

    def test_parse_plus_prefix_number(self):
        """Test parsing number with + prefix - should send EDC by default."""
        number = "+19723105316"
        actual_number, send_edc, edc_code = parse_special_dial_code(number)

        assert actual_number == "+19723105316"
        assert send_edc is True
        assert edc_code is None

    def test_parse_unrecognized_star_prefix(self):
        """Test parsing number starting with * but not a recognized special code."""
        number = "*679723105316"
        actual_number, send_edc, edc_code = parse_special_dial_code(number)

        # Should treat as normal number (no special handling)
        assert actual_number == "*679723105316"
        assert send_edc is True
        assert edc_code is None


class FakeSerial:
    """
    A thread-safe fake serial implementation for testing.
    """

    def __init__(self):
        self.port = "/dev/ttyFAKE"
        self.baudrate = 115200
        self.timeout = 0.1  # Fast timeout for tests
        self._is_open = True
        self.input_buffer = queue.Queue()
        self.output_buffer = []
        self.output_lock = threading.Lock()
        self.command_waiters = {}
        self.responses = {
            "AT": "OK",
            "ATE0": "OK",
            "ATE1": "OK",
            "AT+CMEE=2": "OK",
            "AT#DVI=0": "OK",
            "AT#PCMRXG=1000": "OK",
            "AT#DIALMODE=1": "OK",
            "AT#DTMF=1": "OK",
            "AT+CLIP=1": "OK",
            "AT#AUSBC=1": "OK",
            "AT+CEREG=2": "OK",
            "AT+CLVL=0": "OK",
            "AT+CMER=2,0,0,2": "OK",
            "AT#ADSPC=6": "OK",
            "AT+CIND=0,0,1,0,1,1,1,1,0,1,1": "OK",
            "AT+CHUP": "OK",
            "ATA": "OK",
        }

    @property
    def is_open(self):
        return self._is_open

    def open(self):
        self._is_open = True

    def close(self):
        self._is_open = False

    def write(self, data):
        if not self._is_open:
            raise serial.SerialException("Port not open")

        if isinstance(data, str):
            decoded = data
            raw_data = data.encode()
        else:
            decoded = data.decode()
            raw_data = data

        with self.output_lock:
            self.output_buffer.append(decoded)
            command_clean = decoded.strip()

            # Echo
            self.input_buffer.put(raw_data)

            # Response
            response = None
            if command_clean.startswith("ATD"):
                response = "OK"
            elif command_clean in self.responses:
                response = self.responses[command_clean]
            else:
                response = "OK"

            if response:
                self.input_buffer.put(f"\r\n{response}\r\n".encode())

            for cmd, event in self.command_waiters.items():
                if cmd in decoded:
                    event.set()

        logging.debug(f"[FAKE MODEM] Received: {decoded.strip()}")
        return len(data)

    def readline(self):
        if not self._is_open:
            raise serial.SerialException("Port not open")

        try:
            data = self.input_buffer.get(timeout=self.timeout)
            logging.debug(f"[FAKE MODEM] Sending: {data.strip()}")
            return data
        except queue.Empty:
            return b""

    def reset_input_buffer(self):
        with self.input_buffer.mutex:
            self.input_buffer.queue.clear()

    @property
    def in_waiting(self):
        return self.input_buffer.qsize()

    def add_response(self, data):
        """Inject data to be read by the script."""
        if not data.endswith("\n") and not data.endswith("\r"):
            data += "\r\n"
        self.input_buffer.put(data.encode())

    def wait_for_command(self, fragment, timeout=2.0):
        """Wait until a specific command is written to the serial port."""
        event = threading.Event()
        with self.output_lock:
            for cmd in self.output_buffer:
                if fragment in cmd:
                    return True
            self.command_waiters[fragment] = event

        return event.wait(timeout)

    def get_last_command(self):
        with self.output_lock:
            return self.output_buffer[-1] if self.output_buffer else None

    def clear_output(self):
        with self.output_lock:
            self.output_buffer = []
            self.command_waiters = {}

    def get_commands_sent(self):
        """Return all commands sent to the modem."""
        with self.output_lock:
            return list(self.output_buffer)


class TestEDCDialCodeIntegration:
    """Integration tests for EDC dial code handling in manage_modem."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        # Setup logging
        logger = logging.getLogger()
        file_handler = logging.FileHandler("edc_test.log", mode="a")
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)

        # Setup
        self.fake_serial = FakeSerial()
        self.whitelist = {"+19723105316": True}
        self.sm = ModemStateMachine(
            self.fake_serial, self.whitelist, enable_audio_routing=False
        )

        self.test_port = 5557
        self.server = ModemTCPServer(self.sm, port=self.test_port)
        self.server_thread = threading.Thread(target=self.server.start, daemon=True)
        self.server_thread.start()
        time.sleep(0.1)

        yield

        # Teardown
        logger.removeHandler(file_handler)
        file_handler.close()

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((DEFAULT_TCP_HOST, self.test_port))
            s.sendall(b'{"command": "shutdown"}\n')
            s.close()
        except Exception:
            pass

        self.sm.shutdown_flag.set()
        if self.server.server_socket:
            try:
                self.server.server_socket.close()
            except Exception:
                pass

    def send_command(self, command_dict):
        """Helper to send JSON command and get response."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        try:
            s.connect((DEFAULT_TCP_HOST, self.test_port))
            import json

            s.sendall(json.dumps(command_dict).encode())

            data = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b"\n" in chunk:
                    break

            return json.loads(data.decode())
        finally:
            s.close()

    def test_star50_strips_prefix_and_dials(self):
        """Test *50 prefix - strips prefix and dials the remaining number."""
        # Place call with *50 prefix
        cmd = {
            "command": "place_call",
            "params": {"number": "*509723105316"},
            "request_id": "test_star50",
        }

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((DEFAULT_TCP_HOST, self.test_port))

        import json

        s.sendall(json.dumps(cmd).encode())

        # Receive pending response
        data = s.recv(4096).decode()
        resp1 = json.loads(data)
        assert resp1["status"] == "pending"

        # Wait for dial command (number should be stripped of *50)
        assert self.fake_serial.wait_for_command("ATD9723105316", timeout=3.0)

        # Inject call connected
        self.fake_serial.add_response("+CIEV: call,1")

        # Receive success response
        data = s.recv(4096).decode()
        resp2 = json.loads(data)

        assert resp2["status"] == "success"

        s.close()

        # Hangup
        self.send_command({"command": "hangup", "request_id": "h1"})

    def test_star54_strips_prefix_and_dials(self):
        """Test *54 prefix - strips prefix and dials the remaining number."""
        cmd = {
            "command": "place_call",
            "params": {"number": "*548881237777"},
            "request_id": "test_star54",
        }

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((DEFAULT_TCP_HOST, self.test_port))

        import json

        s.sendall(json.dumps(cmd).encode())

        # Receive pending response
        data = s.recv(4096).decode()
        resp1 = json.loads(data)
        assert resp1["status"] == "pending"

        # Wait for dial command (number should be stripped of *54)
        assert self.fake_serial.wait_for_command("ATD8881237777", timeout=3.0)

        # Inject call connected
        self.fake_serial.add_response("+CIEV: call,1")

        # Receive success response
        data = s.recv(4096).decode()
        resp2 = json.loads(data)

        assert resp2["status"] == "success"

        s.close()

        # Hangup
        self.send_command({"command": "hangup", "request_id": "h1"})

    def test_star55_strips_prefix_and_dials(self):
        """Test *55 prefix - strips prefix and dials the remaining number."""
        cmd = {
            "command": "place_call",
            "params": {"number": "*555551234567"},
            "request_id": "test_star55",
        }

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((DEFAULT_TCP_HOST, self.test_port))

        import json

        s.sendall(json.dumps(cmd).encode())

        # Receive pending response
        data = s.recv(4096).decode()
        resp1 = json.loads(data)
        assert resp1["status"] == "pending"

        # Wait for dial command (number should be stripped of *55)
        assert self.fake_serial.wait_for_command("ATD5551234567", timeout=3.0)

        # Inject call connected
        self.fake_serial.add_response("+CIEV: call,1")

        # Receive success response
        data = s.recv(4096).decode()
        resp2 = json.loads(data)

        assert resp2["status"] == "success"

        s.close()

        # Hangup
        self.send_command({"command": "hangup", "request_id": "h1"})

    def test_normal_number_dials_as_provided(self):
        """Test normal number without special prefix - dials number exactly as
        provided."""
        cmd = {
            "command": "place_call",
            "params": {"number": "9723105316"},
            "request_id": "test_normal",
        }

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((DEFAULT_TCP_HOST, self.test_port))

        import json

        s.sendall(json.dumps(cmd).encode())

        # Receive pending response
        data = s.recv(4096).decode()
        resp1 = json.loads(data)
        assert resp1["status"] == "pending"

        # Wait for dial command
        assert self.fake_serial.wait_for_command("ATD9723105316", timeout=3.0)

        # Inject call connected
        self.fake_serial.add_response("+CIEV: call,1")

        # Receive success response
        data = s.recv(4096).decode()
        resp2 = json.loads(data)

        assert resp2["status"] == "success"

        s.close()

        # Hangup
        self.send_command({"command": "hangup", "request_id": "h1"})

    def test_star50_dials_stripped_number(self):
        """Verify *50 prefix is stripped and the remaining digits are dialed."""
        # The number after *50 should be exactly what gets dialed
        cmd = {
            "command": "place_call",
            "params": {"number": "*509723105316"},
            "request_id": "test_star50_dial",
        }

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((DEFAULT_TCP_HOST, self.test_port))

        import json

        s.sendall(json.dumps(cmd).encode())

        # Receive pending
        s.recv(4096)

        # Wait a bit for dial to happen
        time.sleep(0.5)

        # Check commands sent to modem
        commands = self.fake_serial.get_commands_sent()

        # Find the ATD command
        atd_commands = [cmd for cmd in commands if cmd.startswith("ATD")]

        assert len(atd_commands) >= 1, "No ATD command found"
        assert (
            "ATD9723105316" in atd_commands[0]
        ), f"Expected ATD9723105316, got {atd_commands[0]}"

        s.close()

        # Cleanup
        self.send_command({"command": "hangup", "request_id": "h1"})

    def test_normal_number_dialed_without_modification(self):
        """Verify that a normal number (no special prefix) is dialed exactly as
        provided."""
        test_cases = [
            ("9723105316", "ATD9723105316"),  # Plain 10-digit number
            ("+19723105316", "ATD+19723105316"),  # Number with + prefix
            ("18001234567", "ATD18001234567"),  # 1 + area code format
            ("+441234567890", "ATD+441234567890"),  # International number
        ]

        for test_number, expected_atd in test_cases:
            # Clear previous commands
            self.fake_serial.clear_output()

            cmd = {
                "command": "place_call",
                "params": {"number": test_number},
                "request_id": f"test_normal_{test_number}",
            }

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5.0)
            s.connect((DEFAULT_TCP_HOST, self.test_port))

            import json

            s.sendall(json.dumps(cmd).encode())

            # Receive pending response
            s.recv(4096)

            # Wait for dial command
            time.sleep(0.5)

            # Check commands sent to modem
            commands = self.fake_serial.get_commands_sent()

            # Find the ATD command
            atd_commands = [cmd for cmd in commands if cmd.startswith("ATD")]

            assert len(atd_commands) >= 1, f"No ATD command found for {test_number}"

            # Verify the exact number is dialed (with ; for voice call)
            assert (
                expected_atd in atd_commands[0]
            ), f"For {test_number}: Expected {expected_atd}, got {atd_commands[0]}"

            s.close()

            # Cleanup - hangup the call
            self.send_command({"command": "hangup", "request_id": f"h_{test_number}"})
            time.sleep(0.3)  # Brief pause between test cases


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
