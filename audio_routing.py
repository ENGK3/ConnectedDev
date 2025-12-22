"""
Audio routing utilities for PulseAudio loopback management.

This module provides functions to detect Telit modem audio interfaces
and set up bidirectional audio routing between the modem and SGTL5000 audio card.
"""

import logging
import os
import re
import subprocess
from typing import List, Optional, Tuple


def get_pactl_sources() -> List[Tuple[str, str]]:
    """
    Get available Telit modem audio sources from PulseAudio.

    Returns:
        List of tuples containing (device_name, interface_number) for each
        detected LE910C1 or LE910C4 modem interface.
    """
    logging.debug("[AUDIO_DEBUG] get_pactl_sources() called")

    # Log relevant environment variables for debugging
    env_vars = ["XDG_RUNTIME_DIR", "PULSE_RUNTIME_PATH", "PULSE_SERVER", "USER", "HOME"]
    for var in env_vars:
        value = os.environ.get(var, "<not set>")
        logging.debug(f"[AUDIO_DEBUG] ENV {var}={value}")

    try:
        # Run the pactl command and capture output
        # Explicitly pass environment to ensure PulseAudio vars are inherited
        result = subprocess.run(
            ["pactl", "list", "sources", "short"],
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )
        logging.debug(f"[AUDIO_DEBUG] pactl returncode: {result.returncode}")
        if result.returncode != 0:
            logging.error(f"[AUDIO_DEBUG] Error running pactl: {result.stderr}")
            print("Error running pactl:", result.stderr)
            return []

        devices = []
        for line in result.stdout.strip().split("\n"):
            parts = line.split("\t")
            if len(parts) >= 2:
                source_name = parts[1]
                # Match both LE910C1 and LE910C4, capture device name and interface
                # number
                match = re.search(
                    r"output.usb-(Android_LE910C[14]-NF_[\w]+)-(\d{2})\.", source_name
                )
                if match:
                    device_name = match.group(1)
                    interface_number = match.group(2)
                    devices.append((device_name, interface_number))
        return devices

    except Exception as e:
        print("Exception occurred:", e)
        return []


def start_audio_bridge() -> Optional[Tuple[Optional[str], Optional[str]]]:
    """
    Start the audio bridge using PulseAudio loopback modules.

    Creates bidirectional audio routing between the Telit modem and
    SGTL5000 audio card using PulseAudio loopback modules.

    Returns:
        Tuple of (module_id_1, module_id_2) for the two loopback modules,
        or (None, None) if setup fails.
    """
    logging.info("[AUDIO_DEBUG] start_audio_bridge() called")
    # Figure out the device number for the LE910C1-NF or LE910C4-NF
    devices = get_pactl_sources()
    logging.info(f"[AUDIO_DEBUG] get_pactl_sources returned: {devices}")
    if not devices:
        logging.error(
            "[AUDIO_DEBUG] No LE910C1-NF or LE910C4-NF audio interfaces found."
        )
        logging.error("No LE910C1-NF or LE910C4-NF audio interfaces found.")
        return (None, None)

    # Use the first device found
    device_name, interface_number = devices[0]
    logging.info(f"Using modem device: {device_name} interface {interface_number}")

    # Setup PulseAudio loopbacks for audio routing

    # Telit modem → SGTL5000Card
    telit_to_sgtl_cmd = [
        "pactl",
        "load-module",
        "module-loopback",
        f"source=alsa_input.usb-{device_name}-{interface_number}.mono-fallback",
        "sink=alsa_output.platform-sound.stereo-fallback",
        "rate=48000",
        "latency_msec=80",
    ]

    # SGTL5000Card → Telit modem
    sgtl_to_telit_cmd = [
        "pactl",
        "load-module",
        "module-loopback",
        "source=alsa_input.platform-sound.stereo-fallback",
        f"sink=alsa_output.usb-{device_name}-{interface_number}.mono-fallback",
        "latency_msec=80",
    ]

    try:
        # Start both loopbacks and get their module IDs
        # Pass environment to ensure PulseAudio connection works
        telit_to_sgtl = (
            subprocess.check_output(telit_to_sgtl_cmd, env=os.environ.copy())
            .decode()
            .strip()
        )
        logging.info(f"Loopbacks loaded - Telit → SGTL5000Card: {telit_to_sgtl}")

        sgtl_to_telit = (
            subprocess.check_output(sgtl_to_telit_cmd, env=os.environ.copy())
            .decode()
            .strip()
        )
        logging.info(f"Loopbacks loaded - SGTL5000Card → Telit: {sgtl_to_telit}")

        return (telit_to_sgtl, sgtl_to_telit)

    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed with return code {e.returncode}")
        logging.error(f"Command: {e.cmd}")
        if hasattr(e, "output") and e.output:
            logging.error(f"Output: {e.output}")
        return (None, None)
    except Exception as e:
        logging.error(f"Unexpected error starting audio bridge: {e}")
        return (None, None)


def terminate_pids(module_ids: Tuple[Optional[str], Optional[str]]) -> None:
    """
    Unload the PulseAudio loopback modules with the given module IDs.

    Args:
        module_ids: Tuple of module IDs to unload. None values are skipped.
    """
    for module_id in module_ids:
        if module_id is None:
            continue

        try:
            # Get the module list first
            result = subprocess.run(
                ["pactl", "list", "modules", "short"],
                capture_output=True,
                text=True,
                check=True,
                env=os.environ.copy(),
            )

            # Check each line for our module ID and loopback
            module_exists = any(
                line.startswith(f"{module_id}\tmodule-loopback")
                for line in result.stdout.splitlines()
            )

            if module_exists:
                subprocess.run(
                    ["pactl", "unload-module", str(module_id)],
                    check=True,
                    env=os.environ.copy(),
                )
                logging.info(f"Unloaded PulseAudio loopback module {module_id}")
            else:
                logging.info(
                    f"Loopback module {module_id} not found or already unloaded"
                )
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to unload loopback module {module_id}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error with loopback module {module_id}: {e}")
