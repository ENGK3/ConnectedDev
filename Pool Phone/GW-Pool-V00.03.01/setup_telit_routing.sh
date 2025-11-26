#!/bin/bash

# Setup PulseAudio loopbacks for audio routing between Headset and SGTL5000Card

echo "Setting up audio routing..."

# LE910C1 → SGTL5000Card
TELIT_TO_SGTL=$(pactl load-module module-loopback \
    source=alsa_input.usb-Android_LE910C1-NF_0123456789ABCDEF-04.mono-fallback \
    sink=alsa_output.platform-sound.stereo-fallback rate=48000\
    latency_msec=50)

# SGTL5000Card → LE910C1
SGTL_TO_TELIT=$(pactl load-module module-loopback \
    source=alsa_input.platform-sound.stereo-fallback \
    sink=alsa_output.usb-Android_LE910C1-NF_0123456789ABCDEF-04.mono-fallback \
    latency_msec=50)

echo "Loopbacks loaded:"
echo "  LE910C1 → SGTL5000Card: Module ID $TELIT_TO_SGTL"
echo "  SGTL5000Card → LE910C1: Module ID $SGTL_TO_TELIT"

# Save module IDs for teardown
echo "$TELIT_TO_SGTL $SGTL_TO_TELIT" > /mnt/data/pulse/pulse_loopback_ids
