#!/usr/bin/env python3
"""
Modem Manager - Centralized modem control with TCP interface.

This script provides a stateful TCP server for managing modem operations
including placing calls, answering calls, and monitoring call status.
It prevents conflicts between simultaneous operations through a state machine.
"""

import argparse
import enum
import errno
import json
import logging
import os
import queue
import socket
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import serial
from dotenv import dotenv_values

from audio_routing import start_audio_bridge, terminate_pids

# Import shared modem utilities
from modem_utils import sbc_cmd, sbc_connect, sbc_disconnect

# Configuration defaults
DEFAULT_SERIAL_PORT = "/dev/ttyUSB2"
DEFAULT_BAUD_RATE = 115200
DEFAULT_TCP_PORT = 5555
DEFAULT_TCP_HOST = "0.0.0.0"
DEFAULT_CONFIG_FILE = "/mnt/data/K3_config_settings"
DEFAULT_WHITELIST = ["+19723256826", "+19723105316"]
DEFAULT_ENABLE_AUDIO_ROUTING = True  # Enable for POOL, disable for elevator

# AT Commands
AT_ANSWER = "ATA\r"
AT_HANGUP = "AT+CHUP\r"
AT_CLIP_ENABLE = "AT+CLIP=1\r"


def load_config(config_file: str) -> tuple[Dict[str, bool], bool]:
    """
    Load configuration from config file.

    Args:
        config_file: Path to K3_config_settings file

    Returns:
        Tuple of (whitelist dict with phone numbers as keys, enable_audio_routing flag)
    """
    whitelist_dict = {}

    if not os.path.exists(config_file):
        logging.warning(f"Config file not found: {config_file}")
        return whitelist_dict, DEFAULT_ENABLE_AUDIO_ROUTING

    try:
        # Load config file using dotenv
        config = dotenv_values(config_file)

        whitelist_str = config.get("WHITELIST", "")
        if not whitelist_str:
            logging.warning("WHITELIST not found in config file")
            # Still load audio routing setting
            enable_audio = config.get("ENABLE_AUDIO_ROUTING", "true").lower()
            enable_audio_routing = enable_audio in ["true", "1", "yes", "on"]
            return whitelist_dict, enable_audio_routing

        # Parse comma-separated numbers
        numbers = [num.strip() for num in whitelist_str.split(",")]

        # Create dictionary with normalized numbers (add + prefix if missing)
        for num in numbers:
            if num:
                # Normalize: add + prefix if not present
                normalized = num if num.startswith("+") else f"+1{num}"
                whitelist_dict[normalized] = True
                logging.info(f"Whitelist entry: {normalized}")

        logging.info(f"Loaded {len(whitelist_dict)} numbers from whitelist")

        # Load audio routing setting
        enable_audio = config.get("ENABLE_AUDIO_ROUTING", "true").lower()
        logging.info(
            f"[AUDIO_DEBUG] Raw ENABLE_AUDIO_ROUTING value from config: "
            f"'{config.get('ENABLE_AUDIO_ROUTING', 'true')}"
            f" -> lowercase: '{enable_audio}'"
        )
        enable_audio_routing = enable_audio in ["true", "1", "yes", "on"]
        logging.info(
            f"[AUDIO_DEBUG] Parsed enable_audio_routing: {enable_audio_routing}"
        )
        logging.info(f"Audio routing enabled: {enable_audio_routing}")

    except Exception as e:
        logging.error(f"Error loading config: {e}", exc_info=True)
        enable_audio_routing = DEFAULT_ENABLE_AUDIO_ROUTING

    return whitelist_dict, enable_audio_routing


class ModemState(enum.Enum):
    """Modem state machine states."""

    IDLE = "IDLE"
    PLACING_CALL = "PLACING_CALL"
    ANSWERING_CALL = "ANSWERING_CALL"
    CALL_ACTIVE = "CALL_ACTIVE"
    CALL_ENDING = "CALL_ENDING"


@dataclass
class CallInfo:
    """Information about current call."""

    number: Optional[str] = None
    direction: Optional[str] = None  # "outgoing" or "incoming"
    start_time: Optional[datetime] = None
    audio_modules: Optional[Tuple[Optional[str], Optional[str]]] = None
    call_connected: bool = False
    request_id: Optional[str] = None  # Track which request owns this call


@dataclass
class CommandRequest:
    """Represents a command request from TCP client."""

    command: str
    params: Dict[str, Any]
    request_id: str
    client_socket: Optional[socket.socket] = None


@dataclass
class CommandResponse:
    """Represents a response to a command."""

    status: str  # "success", "error", "pending"
    message: str
    request_id: str
    data: Optional[Dict[str, Any]] = None

    def to_json(self) -> str:
        """Convert response to JSON string."""
        return json.dumps(asdict(self))


class ModemStateMachine:
    """State machine for managing modem operations."""

    def __init__(
        self,
        serial_connection: serial.Serial,
        whitelist: Dict[str, bool],
        enable_audio_routing: bool = True,
    ):
        self.serial = serial_connection
        self.whitelist = whitelist  # Dictionary of allowed numbers
        # Enable audio loopback for POOL, disable for elevator
        self.enable_audio_routing = enable_audio_routing
        self.state = ModemState.IDLE
        self.call_info = CallInfo()
        self.state_lock = threading.Lock()
        self.serial_lock = threading.Lock()  # Protect serial port access
        self.command_queue = queue.Queue()
        self.pending_requests = {}  # request_id -> CommandRequest
        self.shutdown_flag = threading.Event()
        self.incoming_call_callbacks = []  # Callbacks for incoming call notifications

    def get_state(self) -> ModemState:
        """Thread-safe state getter."""
        with self.state_lock:
            return self.state

    def set_state(self, new_state: ModemState):
        """Thread-safe state setter with logging."""
        with self.state_lock:
            old_state = self.state
            self.state = new_state
            logging.info(f"State transition: {old_state.value} -> {new_state.value}")

    def get_status(self) -> Dict[str, Any]:
        """Get current modem status."""
        with self.state_lock:
            status = {
                "state": self.state.value,
                "call_active": self.state == ModemState.CALL_ACTIVE,
                "current_number": self.call_info.number,
                "call_direction": self.call_info.direction,
                "call_connected": self.call_info.call_connected,
            }
            if self.call_info.start_time:
                duration = (datetime.now() - self.call_info.start_time).total_seconds()
                status["call_duration"] = duration
                status["call_start_time"] = self.call_info.start_time.isoformat()
            return status

    def handle_place_call(self, request: CommandRequest) -> CommandResponse:
        """Handle place_call command."""
        current_state = self.get_state()

        if current_state != ModemState.IDLE:
            # Queue the command for later processing
            # NOTE: We don't store the client socket because it will timeout
            # before the queued command is processed
            logging.info(
                f"Modem busy (state: {current_state.value}), "
                f"queueing place_call request {request.request_id}"
            )
            # Clear client socket to prevent sending to timed-out connection
            queued_request = CommandRequest(
                command=request.command,
                params=request.params,
                request_id=request.request_id,
                client_socket=None,  # Don't store socket - it will timeout
            )
            self.command_queue.put(queued_request)
            return CommandResponse(
                status="error",
                message=(
                    f"Modem busy in {current_state.value} state - "
                    f"call cannot be placed now"
                ),
                request_id=request.request_id,
            )

        # Start placing the call
        number = request.params.get("number")
        no_audio_routing = request.params.get("no_audio_routing", False)

        if not number:
            return CommandResponse(
                status="error",
                message="Missing required parameter: number",
                request_id=request.request_id,
            )

        logging.info(f"Placing call to {number}")
        self.set_state(ModemState.PLACING_CALL)
        self.call_info = CallInfo(
            number=number,
            direction="outgoing",
            start_time=datetime.now(),
            request_id=request.request_id,
        )

        # Store pending request for async response
        self.pending_requests[request.request_id] = request

        # Start call in background thread
        thread = threading.Thread(
            target=self._place_call_worker,
            args=(number, no_audio_routing, request.request_id),
            daemon=True,
            name="PlaceCall",
        )
        thread.start()

        return CommandResponse(
            status="pending",
            message="Call placement initiated",
            request_id=request.request_id,
        )

    def _is_worker_cancelled(self, request_id: str) -> bool:
        """Check if this worker thread has been cancelled.

        A worker is cancelled if:
        - State is no longer PLACING_CALL or CALL_ACTIVE
        - call_info.request_id doesn't match (different call started)

        Args:
            request_id: The request_id this worker is handling

        Returns:
            True if worker should abort, False otherwise
        """
        current_state = self.get_state()

        # If we're in IDLE or CALL_ENDING, we've been cancelled
        if current_state in [ModemState.IDLE, ModemState.CALL_ENDING]:
            return True

        # If call_info.request_id doesn't match, a different call has started
        with self.state_lock:
            if self.call_info.request_id != request_id:
                return True

        return False

    def _place_call_worker(self, number: str, no_audio_routing: bool, request_id: str):
        """Worker thread for placing calls."""
        logging.info(
            f"[AUDIO_DEBUG] _place_call_worker started: number={number}, "
            f"no_audio_routing={no_audio_routing}"
        )
        logging.info(
            f"[AUDIO_DEBUG] self.enable_audio_routing={self.enable_audio_routing}"
        )
        try:
            logging.info(f"Worker thread started for {number}")

            # Configure modem for calling
            logging.info("Configuring modem for outgoing call...")
            self._configure_modem_for_call()
            logging.info("Modem configuration complete")

            # Check if cancelled before dialing
            if self._is_worker_cancelled(request_id):
                logging.info(f"Worker for {number} cancelled before dialing")
                return

            with self.serial_lock:
                # Flush any pending data
                self.serial.reset_input_buffer()

                # Place the call
                logging.info(f"Acquiring serial lock to dial {number}")
                dial_response = sbc_cmd(f"ATD{number};\r", self.serial, verbose=True)

            # Check if dial command failed immediately
            if "ERROR" in dial_response or "+CME ERROR" in dial_response:
                logging.error(f"Dial command failed: {dial_response}")
                with self.serial_lock:
                    sbc_cmd(AT_HANGUP, self.serial, verbose=True)
                self.set_state(ModemState.IDLE)
                self.call_info = CallInfo()

                self._send_async_response(
                    request_id,
                    CommandResponse(
                        status="error",
                        message=f"Call failed: {dial_response}",
                        request_id=request_id,
                        data={"call_connected": False},
                    ),
                )
                return

            audio_modules = None
            start_time = time.time()
            timeout = 30
            call_connected = False

            # Set shorter timeout for responsive reading
            original_timeout = self.serial.timeout
            self.serial.timeout = 0.5

            call_termination_reason = None

            try:
                while True:
                    # Check if cancelled by external command
                    if self._is_worker_cancelled(request_id):
                        logging.info(f"Worker for {number} cancelled during call setup")
                        return

                    # Check for timeout
                    if (time.time() - start_time > timeout) and not call_connected:
                        logging.warning("Call connection timeout after 30 seconds")
                        call_termination_reason = "timeout"
                        break

                    with self.serial_lock:
                        response = (
                            self.serial.readline().decode(errors="ignore").strip()
                        )

                    if response:
                        logging.info(f"Call response: {response}")

                    # Check for error responses
                    if "+CME ERROR" in response or "ERROR" in response:
                        logging.error(f"Call failed with error: {response}")
                        call_termination_reason = f"error: {response}"
                        break

                    if "+CIEV: call,1" in response:
                        logging.info("Call connected successfully")
                        call_connected = True
                        self.call_info.call_connected = True

                        audio_routing_success = True
                        logging.info(
                            f"[AUDIO_DEBUG] no_audio_routing={no_audio_routing}, "
                            f"self.enable_audio_routing={self.enable_audio_routing}"
                        )
                        if not no_audio_routing:
                            logging.info(
                                "[AUDIO_DEBUG] Attempting to start audio bridge..."
                            )
                            audio_modules = self._start_audio_bridge()
                            logging.info(
                                f"[AUDIO_DEBUG] Audio modules returned: {audio_modules}"
                            )
                            if audio_modules and audio_modules[0] and audio_modules[1]:
                                self.call_info.audio_modules = audio_modules
                                logging.info(f"Audio bridge started: {audio_modules}")
                            else:
                                audio_routing_success = False
                                logging.warning(
                                    "Call connected but audio routing failed - "
                                    "call will proceed without audio bridge"
                                )
                        else:
                            logging.info(
                                "[AUDIO_DEBUG] Audio routing skipped "
                                f"(no_audio_routing={no_audio_routing})"
                            )

                        self.set_state(ModemState.CALL_ACTIVE)

                        # Send success response to client
                        response_msg = "Call connected successfully"
                        if not no_audio_routing and not audio_routing_success:
                            response_msg += " (audio routing failed)"

                        self._send_async_response(
                            request_id,
                            CommandResponse(
                                status="success",
                                message=response_msg,
                                request_id=request_id,
                                data={
                                    "call_connected": True,
                                    "number": number,
                                    "audio_routing": audio_routing_success,
                                    "audio_routing_requested": not no_audio_routing,
                                },
                            ),
                        )

                    elif "+CIEV: call,0" in response:
                        logging.info("Call setup terminated")
                        call_termination_reason = "+CIEV: call,0"
                        break

                    elif "NO CARRIER" in response:
                        logging.info("Call terminated by remote party")
                        call_termination_reason = "NO CARRIER"
                        break

            finally:
                self.serial.timeout = original_timeout

            # Check if we were cancelled - if so, don't do any cleanup
            if self._is_worker_cancelled(request_id):
                logging.info(f"Worker for {number} cancelled, skipping cleanup")
                return

            # Cleanup based on call status
            if call_connected and call_termination_reason:
                # Call was connected but then terminated
                logging.info(
                    f"Cleaning up terminated call (reason: {call_termination_reason})"
                )
                self.set_state(ModemState.CALL_ENDING)

                # Note: Audio cleanup is handled by monitor_serial_port thread
                # to avoid race condition with multiple threads trying to unload
                # the same modules

                # Send hangup to ensure modem is clean
                with self.serial_lock:
                    sbc_cmd(AT_HANGUP, self.serial, verbose=True)

                # Reset state
                self.set_state(ModemState.IDLE)
                self.call_info = CallInfo()

                # Process any queued commands
                self._process_command_queue()

            elif not call_connected:
                # Call never connected
                logging.info("Call failed to connect, cleaning up")
                with self.serial_lock:
                    sbc_cmd(AT_HANGUP, self.serial, verbose=True)
                self.set_state(ModemState.IDLE)
                self.call_info = CallInfo()

                self._send_async_response(
                    request_id,
                    CommandResponse(
                        status="error",
                        message="Call failed or timed out",
                        request_id=request_id,
                        data={"call_connected": False},
                    ),
                )

                # Process any queued commands
                logging.debug(
                    "[AUDIO_DEBUG] Processing queued commands after call failure"
                )
                self._process_command_queue()

        except Exception as e:
            logging.error(f"Error in place_call_worker: {e}", exc_info=True)
            self.set_state(ModemState.IDLE)
            self.call_info = CallInfo()

            self._send_async_response(
                request_id,
                CommandResponse(
                    status="error",
                    message=f"Call failed: {str(e)}",
                    request_id=request_id,
                ),
            )

    def handle_hangup(self, request: CommandRequest) -> CommandResponse:
        """Handle hangup command."""
        current_state = self.get_state()

        if current_state not in [ModemState.CALL_ACTIVE, ModemState.PLACING_CALL]:
            return CommandResponse(
                status="error",
                message=f"No active call to hang up (state: {current_state.value})",
                request_id=request.request_id,
            )

        logging.info("Hanging up call")
        self.set_state(ModemState.CALL_ENDING)

        # Send hangup command
        with self.serial_lock:
            sbc_cmd(AT_HANGUP, self.serial, verbose=True)

        # Cleanup audio
        if self.call_info.audio_modules:
            self._stop_audio_bridge(self.call_info.audio_modules)
            logging.info("Audio bridge terminated")

        # Reset state
        self.set_state(ModemState.IDLE)
        self.call_info = CallInfo()

        # Process any queued commands
        threading.Thread(target=self._process_command_queue, daemon=True).start()

        return CommandResponse(
            status="success",
            message="Call terminated",
            request_id=request.request_id,
        )

    def handle_status(self, request: CommandRequest) -> CommandResponse:
        """Handle status command."""
        status_data = self.get_status()
        return CommandResponse(
            status="success",
            message="Status retrieved",
            request_id=request.request_id,
            data=status_data,
        )

    def handle_shutdown(self, request: CommandRequest) -> CommandResponse:
        """Handle shutdown command."""
        logging.info("Shutdown command received")
        self.shutdown_flag.set()

        return CommandResponse(
            status="success",
            message="Shutdown initiated",
            request_id=request.request_id,
        )

    def handle_incoming_call(self, caller_number: str):
        """Handle incoming call from serial monitoring."""
        current_state = self.get_state()

        if current_state != ModemState.IDLE:
            logging.warning(
                f"Incoming call from {caller_number} rejected - "
                f"modem busy (state: {current_state.value})"
            )
            # Send hangup to reject the incoming call
            with self.serial_lock:
                sbc_cmd(AT_HANGUP, self.serial, verbose=True)
            return

        logging.info(f"Incoming call from {caller_number}")
        self.set_state(ModemState.ANSWERING_CALL)

        # Check whitelist (dictionary lookup)
        if caller_number not in self.whitelist:
            logging.warning(
                f"Number {caller_number} not in whitelist ({len(self.whitelist)} "
                f"entries), rejecting call"
            )
            # Send hangup command to terminate the call
            with self.serial_lock:
                sbc_cmd(AT_HANGUP, self.serial, verbose=True)
            self.set_state(ModemState.IDLE)
            return

        logging.info(f"Number {caller_number} is whitelisted, answering call")

        # Answer the call
        with self.serial_lock:
            sbc_cmd(AT_ANSWER, self.serial, verbose=True)

        # Wait a moment for call to establish
        time.sleep(1)

        # Setup audio and transition to active
        audio_modules = None
        audio_routing_success = True
        logging.info(
            f"[AUDIO_DEBUG] Incoming call - "
            f"enable_audio_routing={self.enable_audio_routing}"
        )

        if self.enable_audio_routing:
            logging.info(
                "[AUDIO_DEBUG] Attempting to start audio bridge for incoming call..."
            )
            audio_modules = self._start_audio_bridge()
            logging.info(f"[AUDIO_DEBUG] Audio modules returned: {audio_modules}")
            if audio_modules and audio_modules[0] and audio_modules[1]:
                logging.info(f"Audio bridge started for incoming call: {audio_modules}")
            else:
                audio_routing_success = False
                logging.warning(
                    "Incoming call answered but audio routing failed - "
                    "call will proceed without audio bridge"
                )
        else:
            logging.info(
                "[AUDIO_DEBUG] Audio routing disabled - no audio bridge for "
                "incoming call"
            )

        self.call_info = CallInfo(
            number=caller_number,
            direction="incoming",
            start_time=datetime.now(),
            audio_modules=audio_modules,
            call_connected=True,
        )
        self.set_state(ModemState.CALL_ACTIVE)

        status_msg = f"Incoming call from {caller_number} is now active"
        if self.enable_audio_routing and not audio_routing_success:
            status_msg += " (audio routing failed)"
        logging.info(status_msg)

        # Notify any registered callbacks about incoming call
        self._notify_incoming_call(caller_number)

    def _notify_incoming_call(self, caller_number: str):
        """Notify registered callbacks about incoming call."""
        for callback in self.incoming_call_callbacks:
            try:
                callback(caller_number)
            except Exception as e:
                logging.error(f"Error in incoming call callback: {e}")

    def register_incoming_call_callback(self, callback):
        """Register a callback for incoming call notifications."""
        self.incoming_call_callbacks.append(callback)

    def _configure_modem_for_incoming_calls(self):
        """Configure modem to detect and report incoming calls."""
        logging.info("Configuring modem for incoming call detection")
        at_cmd_set = [
            "ATE1\r",  # Enable command echo
            "AT#DVI=0\r",  # Digital voice interface
            "AT#DTMF=1\r",  # Enable DTMF detection
            "AT+CLIP=1\r",  # Enable caller ID presentation
            "AT+CMEE=2\r",  # Enable verbose error reporting
            "AT#ADSPC=6\r",  # Audio/Speech configuration
            "AT#PCMRXG=1000\r",  # PCM receive gain
            "AT#AUSBC=1\r",  # Audio sub-channel
            "AT+CMER=2,0,0,2\r",  # Enable unsolicited result codes for events
            "AT+CIND=0,0,1,0,1,1,1,1,0,1,1\r",  # Configure indicators
        ]

        with self.serial_lock:
            for cmd in at_cmd_set:
                response = sbc_cmd(cmd, self.serial, verbose=True)
                if response:
                    logging.debug(f"Response to {cmd.strip()}: {response}")

        logging.info("Modem configured for incoming calls")

    def _configure_modem_for_call(self):
        """Configure modem for calling."""
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
            "AT+CMER=2,0,0,2\r",
            "AT#ADSPC=6\r",
            "AT+CIND=0,0,1,0,1,1,1,1,0,1,1\r",
        ]

        with self.serial_lock:
            for cmd in at_cmd_set:
                sbc_cmd(cmd, self.serial, verbose=False)

    def _start_audio_bridge(self) -> Optional[Tuple[Optional[str], Optional[str]]]:
        """Start PulseAudio loopback modules for audio routing."""
        logging.info("[AUDIO_DEBUG] _start_audio_bridge() called in ModemStateMachine")
        try:
            result = start_audio_bridge()
            logging.info(f"[AUDIO_DEBUG] start_audio_bridge() returned: {result}")
            return result
        except Exception as e:
            logging.error(
                f"[AUDIO_DEBUG] Exception in _start_audio_bridge: {e}", exc_info=True
            )
            logging.error(f"Failed to start audio bridge: {e}")
            return (None, None)

    def _stop_audio_bridge(self, module_ids: Tuple[Optional[str], Optional[str]]):
        """Stop PulseAudio loopback modules."""
        try:
            # Validate that both module IDs are valid before attempting to stop
            if not module_ids or not module_ids[0] or not module_ids[1]:
                logging.warning(
                    "Cannot stop audio bridge - invalid module IDs: " f"{module_ids}"
                )
                return

            terminate_pids(module_ids)
        except Exception as e:
            logging.error(f"Failed to stop audio bridge: {e}")

    def _send_async_response(self, request_id: str, response: CommandResponse):
        """Send asynchronous response to pending request."""
        if request_id in self.pending_requests:
            request = self.pending_requests.pop(request_id)
            if request.client_socket:
                try:
                    # Get the tcp_server instance to use thread-safe send
                    # This is passed via the tcp_server parameter in worker threads
                    if hasattr(self, "tcp_server") and self.tcp_server:
                        self.tcp_server._send_to_socket(
                            request.client_socket, response.to_json() + "\n"
                        )
                    else:
                        # Fallback for backwards compatibility
                        request.client_socket.sendall(
                            (response.to_json() + "\n").encode()
                        )
                except Exception as e:
                    logging.warning(
                        f"Failed to send async response "
                        f"(client may have disconnected): {e}"
                    )
            else:
                logging.debug(
                    f"No client socket for request {request_id} - response not sent"
                )

    def _process_command_queue(self):
        """Process any queued commands."""
        try:
            while not self.command_queue.empty():
                request = self.command_queue.get_nowait()
                logging.info(f"Processing queued command: {request.command}")

                # Re-route to appropriate handler
                if request.command == "place_call":
                    response = self.handle_place_call(request)
                    # Note: client_socket will be None for queued commands
                    # Response will be logged but not sent back to client
                    if request.client_socket and response.status != "pending":
                        try:
                            request.client_socket.sendall(
                                (response.to_json() + "\n").encode()
                            )
                        except Exception as e:
                            logging.warning(
                                f"Could not send response to queued command: {e}"
                            )
        except queue.Empty:
            pass
        except Exception as e:
            logging.error(f"Error processing command queue: {e}")


class ModemTCPServer:
    """TCP server for modem management."""

    def __init__(
        self,
        state_machine: ModemStateMachine,
        host: str = DEFAULT_TCP_HOST,
        port: int = DEFAULT_TCP_PORT,
    ):
        self.state_machine = state_machine
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_threads = []
        self.notification_clients = []  # Clients subscribed to notifications
        self.notification_lock = threading.Lock()
        self.socket_locks = {}  # Per-socket write locks to prevent byte interleaving
        self.socket_locks_lock = threading.Lock()  # Protects socket_locks dict

    def start(self):
        """Start the TCP server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.server_socket.settimeout(0.5)  # Shorter timeout for responsive shutdown

        logging.info(f"TCP server listening on {self.host}:{self.port}")

        while not self.state_machine.shutdown_flag.is_set():
            try:
                client_socket, client_address = self.server_socket.accept()
                logging.info(f"Client connected from {client_address}")

                # Create a lock for this socket
                with self.socket_locks_lock:
                    self.socket_locks[client_socket] = threading.Lock()

                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address),
                    daemon=True,
                    name="TCPServ",
                )
                client_thread.start()
                self.client_threads.append(client_thread)

            except socket.timeout:
                continue
            except Exception as e:
                if not self.state_machine.shutdown_flag.is_set():
                    logging.error(f"Error accepting connection: {e}")

        logging.info("TCP server shutting down")
        self.server_socket.close()

    def _handle_client(self, client_socket: socket.socket, client_address):
        """Handle individual client connection."""
        notification_mode = False

        try:
            # Set timeout for client socket
            client_socket.settimeout(60.0)

            while not self.state_machine.shutdown_flag.is_set():
                # Receive data
                data = client_socket.recv(4096)
                if not data:
                    break

                # Decode and parse JSON
                try:
                    message = data.decode().strip()
                    request_data = json.loads(message)

                    command = request_data.get("command")
                    params = request_data.get("params", {})
                    request_id = request_data.get("request_id", f"req-{time.time()}")

                    logging.info(
                        f"Received command from {client_address}: {command} "
                        f"(request_id: {request_id})"
                    )

                    # Create request object
                    request = CommandRequest(
                        command=command,
                        params=params,
                        request_id=request_id,
                        client_socket=client_socket,
                    )

                    # Route to appropriate handler
                    response = self._route_command(request)

                    # Send immediate response (async responses sent by worker threads)
                    if response:
                        self._send_to_socket(client_socket, response.to_json() + "\n")

                        # Check if entering notification mode
                        if response.data and response.data.get("notification_mode"):
                            notification_mode = True
                            logging.info(
                                f"Client {client_address} entering "
                                "notification-only mode"
                            )
                            # Enter notification mode - keep socket alive but don't read
                            self._notification_mode(client_socket, client_address)
                            break  # Exit handler loop

                except json.JSONDecodeError as e:
                    logging.error(f"Invalid JSON from {client_address}: {e}")
                    error_response = CommandResponse(
                        status="error",
                        message=f"Invalid JSON: {str(e)}",
                        request_id="unknown",
                    )
                    self._send_to_socket(client_socket, error_response.to_json() + "\n")

        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
            # Client closed connection - this is normal, log at debug level
            logging.debug(f"Client {client_address} disconnected: {e}")
        except OSError as e:
            # Handle other socket errors
            if e.errno in (errno.ECONNRESET, errno.EPIPE, errno.ECONNABORTED):
                logging.debug(f"Client {client_address} disconnected: {e}")
            else:
                logging.error(f"Socket error handling client {client_address}: {e}")
        except Exception as e:
            logging.error(f"Error handling client {client_address}: {e}")
        finally:
            if not notification_mode:
                # Only close if not in notification mode
                # (notification mode handles its own cleanup)
                # Clean up socket lock
                with self.socket_locks_lock:
                    self.socket_locks.pop(client_socket, None)
                client_socket.close()
                logging.info(f"Client {client_address} disconnected")

    def _notification_mode(self, client_socket: socket.socket, client_address):
        """Keep connection alive for notification-only clients.

        Once a client subscribes to notifications, this method keeps the socket
        alive without reading from it, allowing the client to receive push
        notifications.
        """
        try:
            logging.info(f"Notification mode active for {client_address}")
            # Keep socket alive - notifications are pushed via broadcast_incoming_call
            # Don't read from socket to avoid competing with client's read thread
            while not self.state_machine.shutdown_flag.is_set():
                time.sleep(1.0)

        except Exception as e:
            logging.error(f"Error in notification mode for {client_address}: {e}")
        finally:
            # Remove from notification clients
            with self.notification_lock:
                if client_socket in self.notification_clients:
                    self.notification_clients.remove(client_socket)

            # Clean up socket lock
            with self.socket_locks_lock:
                self.socket_locks.pop(client_socket, None)
            client_socket.close()
            logging.info(f"Notification client {client_address} disconnected")

    def _route_command(self, request: CommandRequest) -> Optional[CommandResponse]:
        """Route command to appropriate handler."""
        command = request.command

        if command == "place_call":
            return self.state_machine.handle_place_call(request)
        elif command == "hangup":
            return self.state_machine.handle_hangup(request)
        elif command == "status":
            return self.state_machine.handle_status(request)
        elif command == "subscribe_notifications":
            return self._handle_subscribe(request)
        elif command == "shutdown":
            return self.state_machine.handle_shutdown(request)
        else:
            return CommandResponse(
                status="error",
                message=f"Unknown command: {command}",
                request_id=request.request_id,
            )

    def _handle_subscribe(self, request: CommandRequest) -> CommandResponse:
        """Handle notification subscription request.

        Returns a special response that signals the handler to enter notification mode.
        """
        if request.client_socket:
            with self.notification_lock:
                if request.client_socket not in self.notification_clients:
                    self.notification_clients.append(request.client_socket)
            logging.info("Client subscribed to notifications")

            # Return response with special flag to enter notification mode
            response = CommandResponse(
                status="success",
                message="Subscribed to incoming call notifications",
                request_id=request.request_id,
            )
            response.data = {"notification_mode": True}
            return response
        else:
            return CommandResponse(
                status="error",
                message="No client socket available",
                request_id=request.request_id,
            )

    def _send_to_socket(self, client_socket: socket.socket, message: str):
        """Thread-safe method to send data to a client socket.

        Args:
            client_socket: Socket to send to
            message: String message to send (will be encoded to bytes)
        """
        with self.socket_locks_lock:
            socket_lock = self.socket_locks.get(client_socket)

        if socket_lock:
            with socket_lock:
                client_socket.sendall(message.encode())
        else:
            # Socket not in locks (maybe already removed), try anyway
            client_socket.sendall(message.encode())

    def broadcast_incoming_call(self, caller_number: str):
        """Broadcast incoming call notification to subscribed clients."""
        notification = {
            "type": "incoming_call",
            "caller_number": caller_number,
            "timestamp": datetime.now().isoformat(),
        }

        # Send as newline-delimited JSON (not netstring)
        message = json.dumps(notification) + "\n"

        logging.debug(f"Broadcasting notification: {message.strip()}")

        with self.notification_lock:
            dead_clients = []
            for client_socket in self.notification_clients:
                try:
                    self._send_to_socket(client_socket, message)
                    try:
                        peer_name = client_socket.getpeername()
                        logging.info(
                            f"Sent incoming call notification to "
                            f"{peer_name}: {caller_number}"
                        )
                    except Exception:
                        logging.info(
                            f"Sent incoming call notification to "
                            f"client: {caller_number}"
                        )
                except Exception as e:
                    try:
                        peer_name = client_socket.getpeername()
                        logging.warning(
                            f"Failed to send notification to {peer_name}: {e}"
                        )
                    except Exception:
                        logging.warning(
                            f"Failed to send notification to disconnected client: {e}"
                        )
                    dead_clients.append(client_socket)

            # Remove dead clients
            for client_socket in dead_clients:
                self.notification_clients.remove(client_socket)
                try:
                    client_socket.close()
                except Exception:
                    pass

    def broadcast_call_ended(self, reason: str = "unknown"):
        """Broadcast call ended notification to subscribed clients."""
        notification = {
            "type": "call_ended",
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }

        # Send as newline-delimited JSON (not netstring)
        message = json.dumps(notification) + "\n"

        logging.debug(f"Broadcasting call ended notification: {message.strip()}")

        with self.notification_lock:
            dead_clients = []
            for client_socket in self.notification_clients:
                try:
                    self._send_to_socket(client_socket, message)
                    try:
                        peer_name = client_socket.getpeername()
                        logging.info(
                            f"Sent call ended notification to {peer_name}: {reason}"
                        )
                    except Exception:
                        logging.info(
                            f"Sent call ended notification to client: {reason}"
                        )
                except Exception as e:
                    try:
                        peer_name = client_socket.getpeername()
                        logging.warning(
                            f"Failed to send notification to {peer_name}: {e}"
                        )
                    except Exception:
                        logging.warning(
                            f"Failed to send notification to disconnected client: {e}"
                        )
                    dead_clients.append(client_socket)

            # Remove dead clients
            for client_socket in dead_clients:
                self.notification_clients.remove(client_socket)
                try:
                    client_socket.close()
                except Exception:
                    pass

    def broadcast_dtmf(self, digit: str):
        """Broadcast DTMF digit notification to all registered notification clients."""
        notification = {
            "type": "dtmf_received",
            "digit": digit,
            "timestamp": datetime.now().isoformat(),
        }

        message = json.dumps(notification) + "\n"

        with self.notification_lock:
            dead_clients = []
            for client_socket in self.notification_clients:
                try:
                    self._send_to_socket(client_socket, message)
                    try:
                        peer_name = client_socket.getpeername()
                        logging.debug(f"Sent DTMF notification to {peer_name}: {digit}")
                    except Exception:
                        logging.debug(f"Sent DTMF notification to client: {digit}")
                except Exception as e:
                    try:
                        peer_name = client_socket.getpeername()
                        logging.warning(
                            f"Failed to send DTMF notification to {peer_name}: {e}"
                        )
                    except Exception:
                        logging.warning(
                            f"Failed to send DTMF notification to "
                            f"disconnected client: {e}"
                        )
                    dead_clients.append(client_socket)

            # Remove dead clients
            for client_socket in dead_clients:
                self.notification_clients.remove(client_socket)
                try:
                    client_socket.close()
                except Exception:
                    pass


def monitor_serial_port(state_machine: ModemStateMachine, tcp_server=None):
    """Monitor serial port for incoming calls and events.

    Args:
        state_machine: ModemStateMachine instance
        tcp_server: Optional ModemTCPServer for broadcasting notifications
    """
    logging.info("Starting serial port monitor")

    # Configure modem for incoming call detection
    state_machine._configure_modem_for_incoming_calls()

    caller_number = None

    while not state_machine.shutdown_flag.is_set():
        try:
            # Check if worker thread needs the serial port
            # If placing a call, give it priority by sleeping briefly
            current_state = state_machine.get_state()
            if current_state == ModemState.PLACING_CALL:
                # Give the worker thread time to configure and place call
                time.sleep(0.1)
                continue

            # Set short timeout to allow checking shutdown flag
            with state_machine.serial_lock:
                state_machine.serial.timeout = 0.5
                line = state_machine.serial.readline().decode(errors="ignore").strip()

            if not line:
                continue

            # Log all serial traffic at INFO level for visibility
            logging.info(f"Serial: {line}")

            # Detect incoming call
            if line == "RING":
                logging.info("Incoming call detected (RING)")

            # Detect caller ID
            if line.startswith("+CLIP:"):
                # Example: +CLIP: "+1234567890",145,"",0,"",0
                parts = line.split(",")
                if parts:
                    caller_number = parts[0].split(":")[1].strip().strip('"')
                    logging.info(f"Caller ID: {caller_number}")

                    # Handle the incoming call
                    state_machine.handle_incoming_call(caller_number)

            # Detect DTMF events
            if line.startswith("#DTMFEV:"):
                # Example: #DTMFEV: *,1 or #DTMFEV: 5,1
                parts = line.split(":")
                if len(parts) >= 2:
                    dtmf_parts = parts[1].strip().split(",")
                    if dtmf_parts:
                        dtmf_digit = dtmf_parts[0].strip()
                        logging.info(f"DTMF detected: {dtmf_digit}")

                        # Broadcast DTMF to subscribed clients
                        if tcp_server and current_state == ModemState.CALL_ACTIVE:
                            tcp_server.broadcast_dtmf(dtmf_digit)

            # Detect call state changes and terminations
            call_ended = False
            termination_reason = None

            if "+CIEV: call,0" in line:
                call_ended = True
                termination_reason = "call state change (+CIEV: call,0)"
            elif "NO CARRIER" in line:
                call_ended = True
                termination_reason = "no carrier (remote disconnect)"
            elif "BUSY" in line:
                call_ended = True
                termination_reason = "busy signal"
            elif "NO ANSWER" in line:
                call_ended = True
                termination_reason = "no answer"

            if call_ended:
                current_state = state_machine.get_state()
                if current_state in [ModemState.CALL_ACTIVE, ModemState.PLACING_CALL]:
                    logging.info(f"Call ended: {termination_reason}")
                    state_machine.set_state(ModemState.CALL_ENDING)

                    # Broadcast call ended notification to subscribed clients
                    if tcp_server:
                        tcp_server.broadcast_call_ended(termination_reason)

                    # Cleanup audio if active
                    if state_machine.call_info.audio_modules:
                        state_machine._stop_audio_bridge(
                            state_machine.call_info.audio_modules
                        )
                        logging.info("Audio bridge terminated due to call end")

                    # Reset state
                    state_machine.set_state(ModemState.IDLE)
                    state_machine.call_info = CallInfo()

                    # Process queued commands
                    threading.Thread(
                        target=state_machine._process_command_queue,
                        daemon=True,
                        name="CMDQ",
                    ).start()

        except serial.SerialException as e:
            logging.error(f"Serial port error: {e}")
            break
        except Exception as e:
            logging.error(f"Error in serial monitor: {e}", exc_info=True)

    logging.info("Serial port monitor stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Modem Manager - Centralized modem control server"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_TCP_PORT,
        help=f"TCP server port (default: {DEFAULT_TCP_PORT})",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=DEFAULT_TCP_HOST,
        help=f"TCP server host (default: {DEFAULT_TCP_HOST})",
    )
    parser.add_argument(
        "--modem",
        type=str,
        default=DEFAULT_SERIAL_PORT,
        help=f"Modem serial port (default: {DEFAULT_SERIAL_PORT})",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=DEFAULT_BAUD_RATE,
        help=f"Modem baud rate (default: {DEFAULT_BAUD_RATE})",
    )
    parser.add_argument(
        "--config-file",
        type=str,
        default=DEFAULT_CONFIG_FILE,
        help=f"Config file path (default: {DEFAULT_CONFIG_FILE})",
    )
    parser.add_argument(
        "--whitelist",
        type=str,
        nargs="+",
        default=None,
        help="Whitelist of allowed phone numbers (overrides config file)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="/mnt/data/calls.log",
        help="Log file path",
    )
    parser.add_argument(
        "--env",
        action="store_true",
        help="Print environment variables and exit",
    )

    args = parser.parse_args()

    # Handle --env flag to print environment variables
    if args.env:
        env_vars = [
            "XDG_RUNTIME_DIR",
            "PULSE_RUNTIME_PATH",
            "PULSE_SERVER",
            "DBUS_SESSION_BUS_ADDRESS",
        ]
        print("Environment Variables:")
        for var in env_vars:
            value = os.environ.get(var, "<not set>")
            print(f"  {var}={value}")
        sys.exit(0)

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s.%(msecs)03d %(levelname)-8s "
        "[MM %(threadName)s] %(message)s",
        datefmt="%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(args.log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logging.info("=" * 60)
    logging.info("Modem Manager Starting")
    logging.info(f"TCP Server: {args.host}:{args.port}")
    logging.info(f"Modem Port: {args.modem} @ {args.baud} baud")
    logging.info("=" * 60)

    # Load configuration from config file or command line
    enable_audio_routing = DEFAULT_ENABLE_AUDIO_ROUTING  # Default value
    logging.info(
        f"[AUDIO_DEBUG] Initial enable_audio_routing={enable_audio_routing} "
        f"(from DEFAULT_ENABLE_AUDIO_ROUTING)"
    )

    if args.whitelist:
        # Command line override for whitelist
        logging.info("Using whitelist from command line")
        whitelist_dict = {}
        for num in args.whitelist:
            normalized = num if num.startswith("+") else f"+1{num}"
            whitelist_dict[normalized] = True
        logging.info(f"Whitelist: {list(whitelist_dict.keys())}")
        # Still load audio routing setting from config
        _, enable_audio_routing = load_config(args.config_file)
    else:
        # Load from config file
        logging.info(f"Loading configuration from: {args.config_file}")
        whitelist_dict, enable_audio_routing = load_config(args.config_file)
        logging.info(
            f"[AUDIO_DEBUG] After load_config: "
            f"enable_audio_routing={enable_audio_routing}"
        )

        if not whitelist_dict:
            logging.warning("No whitelist loaded, using defaults")
            whitelist_dict = {num: True for num in DEFAULT_WHITELIST}
            logging.info(f"Default whitelist: {list(whitelist_dict.keys())}")

    logging.info("=" * 60)

    # Connect to modem
    serial_connection = serial.Serial()
    if not sbc_connect(serial_connection, port=args.modem, baudrate=args.baud):
        logging.error("Failed to connect to modem")
        sys.exit(1)

    try:
        # Create state machine
        logging.info(
            f"[AUDIO_DEBUG] Creating ModemStateMachine with "
            f"enable_audio_routing={enable_audio_routing}"
        )
        state_machine = ModemStateMachine(
            serial_connection, whitelist_dict, enable_audio_routing
        )
        audio_status = "ENABLED" if enable_audio_routing else "DISABLED"
        logging.info(
            f"[AUDIO_DEBUG] ModemStateMachine created, "
            f"state_machine.enable_audio_routing={state_machine.enable_audio_routing}"
        )
        logging.info(f"Audio routing: {audio_status}")

        # Create TCP server
        tcp_server = ModemTCPServer(state_machine, args.host, args.port)

        # Store reference to tcp_server in state_machine for thread-safe socket access
        state_machine.tcp_server = tcp_server

        # Register callback to broadcast incoming calls to subscribed clients
        state_machine.register_incoming_call_callback(
            tcp_server.broadcast_incoming_call
        )

        # Start serial monitor thread (pass tcp_server for call_ended broadcasts)
        serial_thread = threading.Thread(
            target=monitor_serial_port,
            args=(state_machine, tcp_server),
            daemon=False,
            name="SerialMon",
        )
        serial_thread.start()

        # Start TCP server (blocking)
        tcp_server.start()

    except KeyboardInterrupt:
        logging.info("Interrupted by user (Ctrl+C)")
        # Set shutdown flag immediately
        state_machine.shutdown_flag.set()
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        state_machine.shutdown_flag.set()
    finally:
        # Cleanup
        logging.info("Shutting down...")

        # Give threads a moment to finish
        if "serial_thread" in locals():
            serial_thread.join(timeout=2.0)
            if serial_thread.is_alive():
                logging.warning("Serial monitor thread did not exit cleanly")

        # Close serial connection
        try:
            sbc_disconnect(serial_connection)
        except Exception as e:
            logging.error(f"Error closing serial connection: {e}")

        logging.info("Modem Manager stopped")
        sys.exit(0)


if __name__ == "__main__":
    main()
