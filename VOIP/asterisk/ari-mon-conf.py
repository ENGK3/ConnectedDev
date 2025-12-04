#!/usr/bin/env python3
"""
ARI-based Conference Monitor
Monitors a ConfBridge conference and automatically adds a specified extension
as an admin when the first participant joins.
"""

import argparse
import asyncio
import logging
import sys

import aiohttp
from dotenv import dotenv_values

# Configuration
ARI_HOST = "127.0.0.1"
ARI_PORT = 8088
ARI_USER = "at_user"
ARI_PASSWORD = "asterisk"
ARI_APP_NAME = "conf_monitor"

# Logging setup

logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s.%(msecs)03d %(levelname)-8s [ARI_MON] %(message)s",
        datefmt="%m-%d %H:%M:%S",
        filename="/mnt/data/calls.log",
        filemode="a+",
    )

logger = logging.getLogger(__name__)

ADMIN_EXT_MASTER = "201"
ADMIN_EXT_EDC = "200"

# Load MASTER_ANSWER_TO from K3_config_settings file
config = dotenv_values("/mnt/data/K3_config_settings")
ADMIN_TIMEOUT_SECONDS = int(config.get("MASTER_ANSWER_TO", 15))


class ARIConfMonitor:
    """Monitors ConfBridge via ARI and auto-adds admin extension"""

    def __init__(self, extension, conference_name):
        self.extension = extension
        self.conference_name = conference_name
        self.base_url = f"http://{ARI_HOST}:{ARI_PORT}/ari"
        self.ws_url = f"ws://{ARI_HOST}:{ARI_PORT}/ari/events"
        self.auth = aiohttp.BasicAuth(ARI_USER, ARI_PASSWORD)
        self.session = None
        self.ws = None
        self.conference_started = False
        self.admin_channels = set()  # Track all admin channels
        self.conference_channels = set()  # Track all conference participants
        self.admin_call_in_progress = False  # Prevent duplicate admin calls

        # New attributes for handling extension 201 -> 200 fallback
        self.master_call_task = None  # Task for calling extension 201
        self.master_channel_id = None  # Channel ID for extension 201 call
        self.master_answered = False  # Whether extension 201 answered
        self.fallback_scheduled = False  # Whether fallback to 200 is scheduled

    async def connect(self):
        """Establish connection to ARI"""
        self.session = aiohttp.ClientSession(auth=self.auth)

        # Connect to WebSocket for events
        ws_params = {"app": ARI_APP_NAME, "subscribeAll": "true"}

        try:
            self.ws = await self.session.ws_connect(
                self.ws_url, params=ws_params, heartbeat=30
            )
            logger.info(f"Connected to ARI at {ARI_HOST}:{ARI_PORT}")
            logger.info(f"Monitoring conference: {self.conference_name}")
            logger.info(f"Will auto-add extension: {self.extension}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ARI: {e}")
            return False

    async def originate_call_to_extension(self, extension_number):
        """Originate a call to a specific extension"""
        endpoint = f"PJSIP/{extension_number}"

        originate_data = {
            "endpoint": endpoint,
            "app": ARI_APP_NAME,
            "appArgs": f"conf,{self.conference_name}",
            "callerId": f"{extension_number}",
            "timeout": 30,
        }

        try:
            url = f"{self.base_url}/channels"
            async with self.session.post(url, json=originate_data) as resp:
                logger.info(f"Originating call to {endpoint}...")
                logger.debug(f"resp json data: {await resp.json()}")
                if resp.status == 200:
                    channel_data = await resp.json()
                    channel_id = channel_data["id"]
                    logger.info(
                        f"Successfully originated call to {endpoint}, "
                        f"channel: {channel_id}"
                    )
                    return channel_id
                else:
                    error_text = await resp.text()
                    logger.error(
                        f"Failed to originate call: {resp.status} - {error_text}"
                    )
                    return None
        except Exception as e:
            logger.error(f"Error originating call: {e}")
            return None

    async def start_admin_call_sequence(self):
        """Start the admin call sequence - try 201 first, then 200 if no answer"""
        # Prevent duplicate calls
        if self.admin_call_in_progress:
            logger.info(
                f"Admin call already in progress. "
                f"Skipping duplicate call. (in_progress={self.admin_call_in_progress}, "
                f"admin_channels={len(self.admin_channels)})"
            )
            return

        self.admin_call_in_progress = True
        self.master_answered = False
        self.fallback_scheduled = False

        logger.info(f"Starting admin call sequence - trying {ADMIN_EXT_MASTER} first")

        # Try calling extension 201 first
        master_channel_id = await self.originate_call_to_extension(ADMIN_EXT_MASTER)

        if master_channel_id:
            self.master_channel_id = master_channel_id
            # Start timeout task for fallback to extension 200
            self.master_call_task = asyncio.create_task(self._master_timeout_handler())
        else:
            # Failed to call 201, try 200 immediately
            logger.warning(f"Failed to call {ADMIN_EXT_MASTER}, trying {ADMIN_EXT_EDC}")
            await self._fallback_to_edc()

    async def _master_timeout_handler(self):
        """Handle timeout for extension 201 - fallback to 200 if no answer"""
        try:
            await asyncio.sleep(ADMIN_TIMEOUT_SECONDS)

            # If we reach here, extension 201 didn't answer in time
            if not self.master_answered and not self.fallback_scheduled:
                logger.info(
                    f"Extension {ADMIN_EXT_MASTER} did not answer within "
                    f"{ADMIN_TIMEOUT_SECONDS} seconds, falling back to {ADMIN_EXT_EDC}"
                )
                self.fallback_scheduled = True

                # Hangup the call to extension 201
                if self.master_channel_id:
                    await self._hangup_channel(self.master_channel_id)

                # Call extension 200
                await self._fallback_to_edc()

        except asyncio.CancelledError:
            logger.debug("Master timeout handler cancelled - extension 201 answered")
        except Exception as e:
            logger.error(f"Error in master timeout handler: {e}")

    async def _fallback_to_edc(self):
        """Fallback to calling extension 200"""
        edc_channel_id = await self.originate_call_to_extension(ADMIN_EXT_EDC)
        if not edc_channel_id:
            logger.error(f"Failed to call fallback extension {ADMIN_EXT_EDC}")
            self.admin_call_in_progress = False
            self.master_channel_id = None
            self.master_answered = False
            self.fallback_scheduled = False

    async def _hangup_channel(self, channel_id):
        """Hangup a specific channel"""
        try:
            hangup_url = f"{self.base_url}/channels/{channel_id}"
            async with self.session.delete(hangup_url) as resp:
                if resp.status == 204:
                    logger.info(f"Hung up channel {channel_id}")
                else:
                    logger.warning(
                        f"Failed to hangup channel {channel_id}: {resp.status}"
                    )
        except Exception as e:
            logger.error(f"Error hanging up channel {channel_id}: {e}")

    async def add_to_conference(self, channel_id):
        """Add a channel to the ConfBridge conference as admin"""
        try:
            # Answer the channel first
            answer_url = f"{self.base_url}/channels/{channel_id}/answer"
            async with self.session.post(answer_url) as resp:
                if resp.status == 204:
                    logger.info(f"Channel {channel_id} answered")
                else:
                    logger.warning(f"Failed to answer channel: {resp.status}")

            # Wait a moment for channel to stabilize
            await asyncio.sleep(0.5)

            # Set channel variables for ConfBridge
            var_url = f"{self.base_url}/channels/{channel_id}/variable"

            # Set the conference name as a channel variable
            async with self.session.post(
                var_url,
                params={
                    "variable": "CONFBRIDGE_CONFERENCE",
                    "value": self.conference_name,
                },
            ) as resp:
                if resp.status == 204:
                    logger.debug("Set conference name variable")

            # Set admin profile
            async with self.session.post(
                var_url,
                params={
                    "variable": "CONFBRIDGE_USER_PROFILE",
                    "value": "default_admin",
                },
            ) as resp:
                if resp.status == 204:
                    logger.info("Set ConfBridge admin profile")

            # Exit Stasis and continue to dialplan extension that runs ConfBridge
            # This extension must exist in your dialplan
            continue_url = f"{self.base_url}/channels/{channel_id}/continue"
            continue_data = {
                "context": "from-internal",
                "extension": "confbridge_admin_join",
                "priority": 1,
            }

            async with self.session.post(continue_url, json=continue_data) as resp:
                if resp.status == 204:
                    logger.info(
                        f"Successfully sent {self.extension} to join conference "
                        f"{self.conference_name} as admin"
                    )
                else:
                    error_text = await resp.text()
                    logger.error(
                        f"Failed to continue to dialplan: {resp.status} - {error_text}"
                    )

        except Exception as e:
            logger.error(f"Error adding to conference: {e}")

    async def handle_stasis_start(self, event):
        """Handle StasisStart event when our originated call is answered"""
        channel_id = event["channel"]["id"]
        app_args = event.get("args", [])

        logger.info(f"StasisStart: channel {channel_id}, args: {app_args}")

        # Check if this is our conference join request
        if len(app_args) >= 2 and app_args[0] == "conf":
            conf_name = app_args[1]
            if conf_name == self.conference_name:
                logger.info(f"Adding channel {channel_id} to conference {conf_name}")

                # Check if this is extension 201 answering
                if channel_id == self.master_channel_id:
                    logger.info(f"Extension {ADMIN_EXT_MASTER} answered!")
                    self.master_answered = True

                    # Cancel the timeout task since 201 answered
                    if self.master_call_task and not self.master_call_task.done():
                        self.master_call_task.cancel()
                        logger.debug("Cancelled master timeout task")

                self.admin_channels.add(channel_id)  # Track admin channel
                # Don't reset admin_call_in_progress yet - wait until they actually
                # join the bridge
                await self.add_to_conference(channel_id)

    async def handle_channel_state_change(self, event):
        """Handle channel state changes"""
        channel = event.get("channel", {})
        state = channel.get("state")
        channel_id = channel.get("id")

        logger.debug(f"Channel {channel_id} state: {state}")

        # You can add additional logic here if needed

    async def handle_confbridge_join(self, event):
        """Handle ConfBridge join events (requires dialplan integration)"""
        # Note: This event is from AMI, not ARI.
        # For pure ARI monitoring, you'd track BridgeCreated/ChannelEnteredBridge events
        pass

    async def handle_bridge_created(self, event):
        """Handle bridge creation events"""
        bridge = event.get("bridge", {})
        bridge_id = bridge.get("id")
        bridge_type = bridge.get("bridge_type")
        bridge_name = bridge.get("name")

        logger.info(
            f"Bridge created: {bridge_id}, name: {bridge_name}: (type: {bridge_type})"
        )

        # Don't trigger on bridge creation - wait for first participant to join
        # This prevents duplicate admin calls
        logger.debug(f"Bridge {bridge_name} created, waiting for participants to join")

    def extract_elevator_number(self, channel_name):
        """
        Extract elevator number from channel name.
        Assumes elevator number is a numeric substring in the channel name.
        Returns the first found number or None.
        """
        import re

        match = re.search(r"PJSIP/(\d{3})", channel_name)

        # if the extension is "200" or "201" we skip sending elevator data
        # packet to the server.
        if match:
            if match.group(1) == ADMIN_EXT_EDC or match.group(1) == ADMIN_EXT_MASTER:
                logging.info("Admin extension detected, skipping elevator data packet.")
                return None
            else:
                logging.info(
                    f"Extracted elevator number: {match.group(1)} "
                    f"returning last two digits."
                )
                return match.group(1)[1:]  # Return last two digits as elevator
        return None

    async def send_elevator_edc_packet(self, channel_name):
        """
        Send EDC info packet for an elevator extension.

        Args:
            channel_name: The channel name to extract elevator number from
        """
        # extract the elevator number from the calling extension.
        elevator_number = self.extract_elevator_number(channel_name)

        if elevator_number:
            logger.info(
                f"Extracted elevator number {elevator_number} from channel "
                f"{channel_name}"
            )

            # Invoke the script "python3 send_EDC_info.py -e <elevator_number>"
            # and capture its return code. Log success or failure.
            # Also wait for this script to complete before proceeding

            result = await asyncio.create_subprocess_exec(
                "python3",
                "/mnt/data/send_EDC_info.py",
                "-e",
                elevator_number,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            if result.returncode == 0:
                logger.info(
                    f"send_EDC_info.py completed successfully for elevator "
                    f"{elevator_number}"
                )
            else:
                logger.error(
                    f"send_EDC_info.py failed for elevator {elevator_number} with "
                    f"return code {result.returncode}: {stderr.decode().strip()}"
                )
        else:
            # Not clear what the correct thing to do here is - TODO: Ask about.
            logger.warning(
                f"Failed to extract elevator number/or admin channel {channel_name}"
            )

    async def handle_channel_entered_bridge(self, event):
        """Handle channel entering bridge"""
        bridge = event.get("bridge", {})
        channel = event.get("channel", {})
        bridge_name = bridge.get("name", "")
        channel_name = channel.get("name")
        channel_id = channel.get("id")

        logger.info(f"Channel {channel_name} entered bridge {bridge_name}")

        # Track participants in our conference
        if bridge_name == self.conference_name:

            # Send EDC packet for elevator extensions
            await self.send_elevator_edc_packet(channel_name)

            self.conference_channels.add(channel_id)
            logger.info(f"Tracked channel {channel_id} in conference")

            # Check if this channel is an admin by inspecting channel name
            # Extensions 200 and 201 are admins
            is_admin = False
            if "PJSIP/200-" in channel_name or "PJSIP/201-" in channel_name:
                is_admin = True
                if channel_id not in self.admin_channels:
                    self.admin_channels.add(channel_id)
                    logger.info(
                        f"Detected admin extension joining via dialplan: {channel_id}"
                    )

            # If this is an admin channel joining, reset the in-progress flag
            if is_admin or channel_id in self.admin_channels:
                self.admin_call_in_progress = False
                logger.info(
                    f"Admin channel {channel_id} successfully joined conference"
                )
                return  # Don't trigger another admin call

            # Trigger admin join only if:
            # 1. No admin is currently in the conference
            # 2. No admin call is already in progress
            # 3. There are participants in the conference
            if (
                len(self.admin_channels) == 0
                and not self.admin_call_in_progress
                and len(self.conference_channels) > 0
            ):
                logger.info(
                    f"Non-admin participant joined {self.conference_name} with no admin present - "
                    f"triggering admin join (conference_started={self.conference_started}, "
                    f"admin_channels={len(self.admin_channels)}, "
                    f"admin_call_in_progress={self.admin_call_in_progress})"
                )
                self.conference_started = True
                await self.start_admin_call_sequence()
            else:
                logger.info(
                    f"Non-admin participant joined but admin already present or being called "
                    f"(admin_channels={len(self.admin_channels)}, "
                    f"admin_call_in_progress={self.admin_call_in_progress}) - skipping admin call"
                )
                # Mark conference as started even if we don't call admin
                self.conference_started = True

    async def handle_bridge_destroyed(self, event):
        """Handle bridge destruction - reset state"""
        bridge = event.get("bridge", {})
        bridge_name = bridge.get("name", "")

        if bridge_name == self.conference_name:
            logger.info(f"Conference {self.conference_name} ended - resetting state")
            self.conference_started = False
            self.admin_channels.clear()
            self.admin_call_in_progress = False
            self.conference_channels.clear()

            # Cancel any pending master call timeout task
            if self.master_call_task and not self.master_call_task.done():
                self.master_call_task.cancel()

            # Reset master call state
            self.master_channel_id = None
            self.master_answered = False
            self.fallback_scheduled = False

    async def handle_channel_left_bridge(self, event):
        """Handle channel leaving bridge - hangup others if admin leaves"""
        bridge = event.get("bridge", {})
        channel = event.get("channel", {})
        bridge_name = bridge.get("name", "")
        channel_id = channel.get("id")
        channel_name = channel.get("name")

        logger.info(f"Channel {channel_name} left bridge {bridge_name}")

        # Remove from tracking
        if channel_id in self.conference_channels:
            self.conference_channels.discard(channel_id)

        # If an admin left the conference, check if any admins remain
        if bridge_name == self.conference_name and channel_id in self.admin_channels:
            self.admin_channels.discard(channel_id)
            logger.info(
                f"Admin channel {channel_id} left conference - "
                f"{len(self.admin_channels)} admin(s) remaining"
            )

            # Only hangup all participants if this was the LAST admin
            if len(self.admin_channels) == 0:
                logger.info("Last admin left conference - hanging up all participants")
                await self.hangup_all_participants()
                # Reset so admin can be called again
                self.admin_call_in_progress = False

                # Reset master call state
                self.master_channel_id = None
                self.master_answered = False
                self.fallback_scheduled = False
            else:
                logger.info(
                    f"Conference continues with {len(self.admin_channels)} "
                    f"admin(s) remaining"
                )

    async def hangup_all_participants(self):
        """Hangup all channels still in the conference"""
        channels_to_hangup = list(self.conference_channels)

        for channel_id in channels_to_hangup:
            try:
                hangup_url = f"{self.base_url}/channels/{channel_id}"
                async with self.session.delete(hangup_url) as resp:
                    if resp.status == 204:
                        logger.info(f"Hung up channel {channel_id}")
                    else:
                        logger.warning(
                            f"Failed to hangup channel {channel_id}: {resp.status}"
                        )
            except Exception as e:
                logger.error(f"Error hanging up channel {channel_id}: {e}")

        self.conference_channels.clear()

    async def handle_event(self, event):
        """Route events to appropriate handlers"""
        event_type = event.get("type")

        handlers = {
            "StasisStart": self.handle_stasis_start,
            "ChannelStateChange": self.handle_channel_state_change,
            "BridgeCreated": self.handle_bridge_created,
            "ChannelEnteredBridge": self.handle_channel_entered_bridge,
            "ChannelLeftBridge": self.handle_channel_left_bridge,
            "BridgeDestroyed": self.handle_bridge_destroyed,
        }

        handler = handlers.get(event_type)
        if handler:
            await handler(event)
        else:
            logger.debug(f"Unhandled event type: {event_type}")

    async def listen(self):
        """Listen for events from ARI WebSocket"""
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    event = msg.json()
                    await self.handle_event(event)
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.warning("WebSocket closed")
                    break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {self.ws.exception()}")
                    break
        except Exception as e:
            logger.error(f"Error in event loop: {e}")

    async def run(self):
        """Main run loop"""
        if not await self.connect():
            return

        try:
            logger.info("Starting event listener...")
            await self.listen()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean up connections"""
        # Cancel any pending master call timeout task
        if self.master_call_task and not self.master_call_task.done():
            self.master_call_task.cancel()
            try:
                await self.master_call_task
            except asyncio.CancelledError:
                pass

        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
        logger.info("Disconnected from ARI")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Monitor ConfBridge and auto-add admin extension via ARI"
    )
    parser.add_argument(
        "-e",
        "--extension",
        type=str,
        default="200",
        help="Extension number to dial and add as admin (default: 200)",
    )
    parser.add_argument(
        "-c",
        "--conference",
        type=str,
        default="elevator_conference",
        help="Conference name to monitor (default: elevator_conference)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose debug logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    monitor = ARIConfMonitor(args.extension, args.conference)

    try:
        asyncio.run(monitor.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
