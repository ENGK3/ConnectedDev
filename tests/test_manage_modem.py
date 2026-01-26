
import logging
import queue
import socket
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import pytest
import serial

# Add parent directory to path to import manage_modem
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from manage_modem import (
    ModemStateMachine,
    ModemTCPServer,
    ModemState,
    CommandRequest,
    CommandResponse,
    DEFAULT_TCP_HOST,
    AT_ANSWER,
    AT_HANGUP,
)


class FakeSerial:
    """
    A thread-safe fake serial implementation for testing.
    """
    def __init__(self):
        self.port = "/dev/ttyFAKE"
        self.baudrate = 115200
        self.timeout = 1.0
        self._is_open = True
        self.input_buffer = queue.Queue()  # Data coming FROM the modem (to be read)
        self.output_buffer = []  # Data sent TO the modem (captured commands)
        self.output_lock = threading.Lock()
        self.command_waiters = {}  # Map of command_fragment -> threading.Event

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
        
        decoded = data.decode() if isinstance(data, bytes) else data
        with self.output_lock:
            self.output_buffer.append(decoded)
            
            # Check if anyone is waiting for this command
            for cmd, event in self.command_waiters.items():
                if cmd in decoded:
                    event.set()

        logging.debug(f"[FAKE MODEM] Received: {decoded.strip()}")
        return len(data)

    def readline(self):
        """
        Simulate readline with blocking timeout.
        """
        if not self._is_open:
            raise serial.SerialException("Port not open")
            
        try:
            # wait for data up to timeout
            data = self.input_buffer.get(timeout=self.timeout)
            logging.debug(f"[FAKE MODEM] Sending: {data.strip()}")
            return data.encode()
        except queue.Empty:
            return b""

    def reset_input_buffer(self):
        with self.input_buffer.mutex:
            self.input_buffer.queue.clear()

    @property
    def in_waiting(self):
        return self.input_buffer.qsize()
        
    # Test helpers
    def add_response(self, data):
        """Inject data to be read by the script."""
        if not data.endswith('\n') and not data.endswith('\r'):
            data += '\r\n'
        self.input_buffer.put(data)

    def wait_for_command(self, fragment, timeout=2.0):
        """Wait until a specific command is written to the serial port."""
        event = threading.Event()
        with self.output_lock:
            # Check if already received
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


class TestManageModem:
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        # Setup
        self.fake_serial = FakeSerial()
        self.whitelist = {"+1234567890": True}
        self.sm = ModemStateMachine(self.fake_serial, self.whitelist, enable_audio_routing=False)
        
        # Start server on a random port (0 lets OS choose, but we need to know it)
        # We'll pick a static high port for testing to avoid complexity
        self.test_port = 5556 
        self.server = ModemTCPServer(self.sm, port=self.test_port)
        
        self.server_thread = threading.Thread(target=self.server.start, daemon=True)
        self.server_thread.start()
        
        # Give server a moment to start
        time.sleep(0.1)
        
        yield
        
        # Teardown
        # Send shutdown command via valid socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((DEFAULT_TCP_HOST, self.test_port))
            s.sendall(b'{"command": "shutdown"}\n')
            s.close()
        except:
            pass
            
        self.sm.shutdown_flag.set()
        if self.server.server_socket:
            self.server.server_socket.close()

    def send_command(self, command_dict):
        """Helper to send JSON command and get response."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        try:
            s.connect((DEFAULT_TCP_HOST, self.test_port))
            import json
            s.sendall(json.dumps(command_dict).encode())
            
            # Read line-delimited response
            data = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b'\n' in chunk:
                    break
            
            return json.loads(data.decode())
        finally:
            s.close()

    def test_status_command(self):
        """Test getting status."""
        resp = self.send_command({"command": "status", "request_id": "test1"})
        assert resp["status"] == "success"
        assert resp["data"]["state"] == "IDLE"

    def test_place_call_success_flow(self):
        """Test full call placement flow."""
        # 1. Send place_call
        cmd = {
            "command": "place_call",
            "params": {"number": "+15551234"},
            "request_id": "call1"
        }
        
        # Use a persistent socket to receive the async response
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((DEFAULT_TCP_HOST, self.test_port))
        
        import json
        s.sendall(json.dumps(cmd).encode())
        
        # 2. Receive pending response
        data = s.recv(4096).decode()
        resp1 = json.loads(data)
        assert resp1["status"] == "pending"
        
        # 3. Simulate modem interactions
        # Script should send ATD
        assert self.fake_serial.wait_for_command("ATD+15551234")
        
        # Inject OK for dial
        # self.fake_serial.add_response("OK") # ATD usually doesn't give immediate OK until connect or it gives just nothing until connect
        # But sbc_cmd waits for OK/ERROR.
        # Let's check manage_modem: it uses sbc_cmd(..., verbose=True) which waits for OK/ERROR
        # So we MUST send OK or something.
        # Actually ATD command usually waits for CONNECT or OK.
        # sbc_cmd handles OK.
        self.fake_serial.add_response("OK")
        
        # Now it enters the loop waiting for +CIEV: call,1
        self.fake_serial.add_response("+CIEV: call,1")
        
        # 4. Receive success response
        # The worker thread sends this to the socket
        data = s.recv(4096).decode()
        resp2 = json.loads(data)
        
        assert resp2["status"] == "success"
        assert resp2["data"]["call_connected"] is True
        
        # Verify state
        assert self.sm.get_state() == ModemState.CALL_ACTIVE
        
        s.close()
        
        # 5. Hangup
        resp = self.send_command({"command": "hangup", "request_id": "h1"})
        assert resp["status"] == "success"
        assert self.fake_serial.wait_for_command("AT+CHUP")
        assert self.sm.get_state() == ModemState.IDLE

    def test_place_call_busy(self):
        """Test placing call when already busy."""
        # Manually set state
        self.sm.set_state(ModemState.CALL_ACTIVE)
        
        resp = self.send_command({
            "command": "place_call", 
            "params": {"number": "+15559999"}
        })
        
        assert resp["status"] == "error"
        assert "busy" in resp["message"]

    def test_incoming_call_whitelisted(self):
        """Test handling of incoming call from whitelisted number."""
        # Inject incoming call via method directly (simulating monitor loop)
        # We don't have the monitor loop running in this test setup, 
        # so we call handle_incoming_call directly.
        
        # Prepare mock for AT_ANSWER interactions
        # It sends ATA
        # Then asks for audio bridge...
        
        def simulate_incoming():
            self.sm.handle_incoming_call("+1234567890")
            
        t = threading.Thread(target=simulate_incoming)
        t.start()
        
        # Should send ATA
        assert self.fake_serial.wait_for_command("ATA")
        self.fake_serial.add_response("OK")
        
        t.join(timeout=2.0)
        
        assert self.sm.get_state() == ModemState.CALL_ACTIVE
        assert self.sm.call_info.direction == "incoming"

    def test_incoming_call_rejected(self):
        """Test handling of incoming call from unknown number."""
        self.sm.handle_incoming_call("+1999999999")
        
        # Should send HANGUP
        assert self.fake_serial.wait_for_command("AT+CHUP")
        assert self.sm.get_state() == ModemState.IDLE

    def test_place_call_modem_error(self):
        """Test handling of modem error during dial."""
        cmd = {
            "command": "place_call",
            "params": {"number": "+15556666"},
            "request_id": "err1"
        }
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((DEFAULT_TCP_HOST, self.test_port))
        
        import json
        s.sendall(json.dumps(cmd).encode())
        
        # Pending...
        s.recv(4096)
        
        # Wait for dial
        assert self.fake_serial.wait_for_command("ATD")
        
        # Inject ERROR
        self.fake_serial.add_response("ERROR")
        
        # Receive error response
        data = s.recv(4096).decode()
        resp = json.loads(data)
        
        assert resp["status"] == "error"
        assert "Call failed" in resp["message"]
        
        s.close()
