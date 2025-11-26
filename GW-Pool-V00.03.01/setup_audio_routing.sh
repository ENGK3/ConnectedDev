#!/bin/bash

# Setup PulseAudio loopbacks for audio routing between Headset and SGTL5000Card

echo "Setting up audio routing..."

# Headset → SGTL5000Card
HEADSET_TO_SGTL=$(pactl load-module module-loopback \
    source=alsa_input.usb-Logitech_Logi_USB_Headset-00.mono-fallback \
    sink=alsa_output.platform-sound.stereo-fallback \
    latency_msec=50)

# SGTL5000Card → Headset
SGTL_TO_HEADSET=$(pactl load-module module-loopback \
    source=alsa_input.platform-sound.stereo-fallback \
    sink=alsa_output.usb-Logitech_Logi_USB_Headset-00.analog-stereo \
    latency_msec=50)

echo "Loopbacks loaded:"
echo "  Headset → SGTL5000Card: Module ID $HEADSET_TO_SGTL"
echo "  SGTL5000Card → Headset: Module ID $SGTL_TO_HEADSET"

# Save module IDs for teardown
echo "$HEADSET_TO_SGTL $SGTL_TO_HEADSET" > /mnt/data/pulse/pulse_loopback_ids
