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

# Configuration
ARI_HOST = "127.0.0.1"
ARI_PORT = 8088
ARI_USER = "at_user"
ARI_PASSWORD = "asterisk"
ARI_APP_NAME = "conf_monitor"

# Logging setup
logging.basicConfig(level=logging.DEBUG, format="ARI_MON - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


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
        self.admin_channel_id = None  # Track admin channel
        self.conference_channels = set()  # Track all conference participants
        self.admin_call_in_progress = False  # Prevent duplicate admin calls

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

    async def originate_call(self):
        """Originate a call to the admin extension and join to conference"""
        # Prevent duplicate calls
        if self.admin_call_in_progress or self.admin_channel_id is not None:
            logger.info(
                f"Admin call already in progress or admin already in conference. "
                f"Skipping duplicate call. (in_progress={self.admin_call_in_progress}, "
                f"admin_channel_id={self.admin_channel_id})"
            )
            return None

        self.admin_call_in_progress = True
        endpoint = f"PJSIP/{self.extension}"

        originate_data = {
            "endpoint": endpoint,
            "app": ARI_APP_NAME,
            "appArgs": f"conf,{self.conference_name}",
            "callerId": f"{self.extension}",
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
                    self.admin_call_in_progress = False  # Reset on failure
                    return None
        except Exception as e:
            logger.error(f"Error originating call: {e}")
            self.admin_call_in_progress = False  # Reset on error
            return None

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
                self.admin_channel_id = channel_id  # Track admin channel
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
            print("Match found:", match.group(1))
            if match.group(1) == "200" or match.group(1) == "201":
                logging.info("Admin extension detected, skipping elevator data packet.")
                return None
            else:
                logging.info(
                    f"Extracted elevator number: {match.group(1)} "
                    f"returning last two digits."
                )
                return match.group(1)[1:]  # Return last two digits as elevator
        return None

    async def handle_channel_entered_bridge(self, event):
        """Handle channel entering bridge"""
        bridge = event.get("bridge", {})
        channel = event.get("channel", {})
        bridge_name = bridge.get("name", "")
        channel_name = channel.get("name")
        channel_id = channel.get("id")

        logger.info(f"Channel {channel_name} entered bridge {bridge_name}")

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
                f"Failed to extract elevator number from channel {channel_name}"
            )

        # Track participants in our conference
        if bridge_name == self.conference_name:
            self.conference_channels.add(channel_id)
            logger.info(f"Tracked channel {channel_id} in conference")

            # If this is the admin channel joining, reset the in-progress flag
            if channel_id == self.admin_channel_id:
                self.admin_call_in_progress = False
                logger.info(
                    f"Admin channel {channel_id} successfully joined conference"
                )
                return  # Don't trigger another admin call

            # Trigger admin join only if:
            # 1. Conference hasn't started, OR
            # 2. Admin is not in the conference and there are participants
            if not self.conference_started or (
                self.admin_channel_id is None
                and not self.admin_call_in_progress
                and len(self.conference_channels) > 0
            ):
                logger.info(
                    f"Participant joined {self.conference_name} - triggering "
                    f"admin join (conference_started={self.conference_started}, "
                    f"admin_channel={self.admin_channel_id}, "
                    f"admin_call_in_progress={self.admin_call_in_progress})"
                )
                self.conference_started = True
                await self.originate_call()

    async def handle_bridge_destroyed(self, event):
        """Handle bridge destruction - reset state"""
        bridge = event.get("bridge", {})
        bridge_name = bridge.get("name", "")

        if bridge_name == self.conference_name:
            logger.info(f"Conference {self.conference_name} ended - resetting state")
            self.conference_started = False
            self.admin_channel_id = None
            self.admin_call_in_progress = False
            self.conference_channels.clear()

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

        # If admin left the conference, hangup all remaining participants
        if bridge_name == self.conference_name and channel_id == self.admin_channel_id:
            logger.info(
                f"Admin channel {channel_id} left conference - "
                f"hanging up all participants"
            )
            await self.hangup_all_participants()
            self.admin_channel_id = None
            self.admin_call_in_progress = False  # Reset so admin can be called again

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
