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
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
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
        endpoint = f"PJSIP/{self.extension}"

        originate_data = {
            "endpoint": endpoint,
            "app": ARI_APP_NAME,
            "appArgs": f"conf,{self.conference_name}",
            "callerId": "Conference Auto-Join <9876>",
            "timeout": 30,
        }

        try:
            url = f"{self.base_url}/channels"
            async with self.session.post(url, json=originate_data) as resp:
                logger.info(f"Originating call to {endpoint}...")
                logger.info(f"resp json data: {await resp.json()}")
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
                logger.info(f"Adding channel {channel_id}to conference {conf_name}")
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

        # Check if this is our conference bridge starting
        if bridge_name == self.conference_name and not self.conference_started:
            logger.info(
                f"Conference {self.conference_name} started - triggering admin join"
            )
            self.conference_started = True
            await self.originate_call()

    async def handle_channel_entered_bridge(self, event):
        """Handle channel entering bridge"""
        bridge = event.get("bridge", {})
        channel = event.get("channel", {})
        bridge_id = bridge.get("id")
        channel_name = channel.get("name")

        logger.info(f"Channel {channel_name} entered bridge {bridge_id}")

        # Alternative trigger: first channel joins conference
        if bridge_id == self.conference_name and not self.conference_started:
            logger.info(
                f"First participant joined {self.conference_name} - triggering "
                f"admin join"
            )
            self.conference_started = True
            await self.originate_call()

    async def handle_bridge_destroyed(self, event):
        """Handle bridge destruction - reset state"""
        bridge = event.get("bridge", {})
        bridge_id = bridge.get("id")

        if bridge_id == self.conference_name:
            logger.info(f"Conference {self.conference_name} ended - resetting state")
            self.conference_started = False

    async def handle_event(self, event):
        """Route events to appropriate handlers"""
        event_type = event.get("type")

        handlers = {
            "StasisStart": self.handle_stasis_start,
            "ChannelStateChange": self.handle_channel_state_change,
            "BridgeCreated": self.handle_bridge_created,
            "ChannelEnteredBridge": self.handle_channel_entered_bridge,
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
