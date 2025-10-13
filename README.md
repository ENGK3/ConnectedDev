# King3 Build Project

This repository contains scripts, configurations, and documentation for the King3 embedded system project, which includes VoIP functionality, cellular modem integration, and audio routing on Gateworks hardware platforms.

## Project Files

### Shell Scripts

| Filename | Directory | Description |
|----------|-----------|-------------|
| `config_sys.sh` | `.` | System configuration script that sets up udev rules, systemd services, PulseAudio configuration, and enables necessary system services |
| `led_blue.sh` | `.` | Controls the blue LED on/off (GPIO control for status indication) |
| `led_green.sh` | `.` | Controls the green LED on/off on GPIO 9 (Gateworks GW7200 board) |
| `led_red.sh` | `.` | Controls the red LED on/off on GPIO 26 (Gateworks GW7200 board) |
| `setup_audio_routing.sh` | `.` | Sets up PulseAudio loopback modules for routing audio between USB headset and SGTL5000 sound card |
| `setup_telit_routing.sh` | `.` | Configures PulseAudio loopback modules for routing audio between Telit LE910C1 modem and SGTL5000 sound card |
| `start.sh` | `.` | Docker container startup script for DEY 4.0 development environment |
| `switch_detect.sh` | `.` | Emergency switch press handler that plays audio alert and initiates emergency call |
| `switch_mon.sh` | `.` | GPIO monitoring service that detects switch press events and triggers the switch_detect script |
| `teardown_audio_routing.sh` | `.` | Removes PulseAudio loopback modules for headset audio routing |
| `teardown_telit_routing.sh` | `.` | Removes PulseAudio loopback modules for Telit modem audio routing |



### Python Scripts

| Filename | Directory | Description |
|----------|-----------|-------------|
| `check_reg.py` | `.` | Checks cellular network registration status via AT commands to the Telit modem |
| `EDC_packet.py` | `.` | TCP packet transmission using Telit LE910C1 modem with AT commands for event data communication |
| `EDC_packet_direct.py` | `.` | Direct TCP socket implementation for sending event packets without using modem AT commands |
| `extract_dev.py` | `.` | Extracts USB device interface numbers from PulseAudio source list (used for Telit modem detection) |
| `place_call.py` | `.` | Initiates VoIP calls using baresip, handles audio routing, and logs call events |
| `voip_call_rerouting.py` | `.` | Monitors baresip output and automatically reroutes audio when calls are established |
| `Wait-answer.py` | `.` | Monitors baresip FIFO for incoming calls and automatically answers after a configurable delay |

### Markdown Documentation

| Filename | Directory | Description |
|----------|-----------|-------------|
| `GateworksProgrammingInstr.md` | `.` | Programming and setup instructions for Gateworks Venice board with pool configuration |
| `GateworkVOIPProgramming.md` | `.` | Programming instructions specific to VoIP solution on Gateworks Venice board with PoE configuration |
| `InitialProgrammingInstr.md` | `.` | Initial programming instructions for Digiboard CC6 using UUU tool and firmware flashing |
| `POC_NOTE.md` | `.` | Important notes and limitations about the POC (Proof of Concept) units including security warnings |



## System Overview

This project implements an embedded communication system with the following key features:

- **Cellular Connectivity**: Telit LE910C1 4G LTE modem for data and voice
- **VoIP Integration**: Baresip-based SIP client for VoIP calling
- **Audio Routing**: PulseAudio-based dynamic audio routing between multiple audio devices
- **Event Reporting**: TCP-based event transmission to remote servers
- **Emergency Calling**: GPIO-triggered emergency call functionality
- **LED Status Indication**: Visual feedback using RGB LEDs

## Hardware Platforms

- **Gateworks Venice GW7200** - Primary embedded platform
- **Digiboard CC6** - Alternative platform (legacy)
- **Telit LE910C1-NF** - 4G LTE modem module

## Key Technologies

- PulseAudio for audio routing
- Baresip for VoIP functionality
- Serial AT command interface for modem control
- GPIO control for switches and LEDs
- Docker containerization for cross-compilation
- Systemd services for background monitoring
