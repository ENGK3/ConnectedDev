# King3 Build Project

This repository contains scripts, configurations, and documentation for the King3 embedded system project, which includes VoIP functionality, cellular modem integration, and audio routing on Gateworks hardware platforms.

## Directory Tree (as of October 22, 2025)

```bash
King3-build/
├── 99-ignore-modemmanager.rules
├── GateworkVOIPProgramming.md
├── GateworkVOIPProgramming.pdf
├── GateworksProgrammingInstr.md
├── InitialProgrammingInstr.md
├── K3_QS2_WiringDiagram.png
├── POC_NOTE.md
├── README.md
├── TF-config
├── VOIP
│   ├── VOIPLayout.drawio
│   ├── VOIPLayout.png
│   ├── asterisk
│   │   ├── ari-mon-conf.py
│   │   ├── asterisk.override.conf
│   │   ├── confbridge.conf
│   │   ├── extensions.conf
│   │   ├── modules.conf
│   │   └── pjsip.conf
│   ├── baresip
│   │   ├── accounts
│   │   └── config
│   ├── interfaces
│   ├── latest
│   │   ├── confbridge.conf
│   │   ├── extensions.conf
│   │   └── pjsip.conf
│   ├── pulseaudio
│   │   └── default.pa
│   ├── setup_audio_routing.sh
│   ├── setup_telit_routing.sh
│   ├── teardown_audio_routing.sh
│   ├── teardown_telit_routing.sh
│   ├── voip_call_monitor.service
│   ├── voip_call_monitor_tcp.py
│   ├── voip_call_rerouting.py
│   └── voip_config.sh
├── asound.state
├── check_reg.py
├── common
├── config_sys.sh
├── daemon.conf
├── digi-config
├── explore
│   ├── .. a directory of file that I don't want to
|    lose, but don't have any functional value currently.
|    Mostly debugging exploring ideas types of scripts.
├── gw-venice-gpio-overlay.dts
├── imx8mm-venice-gw7xxx-0x-gpio.dtbo
├── integrity-system
│   ├── .. ignore
├── justfile
├── led_blue.sh
├── led_green.sh
├── led_red.sh
├── microcom.alias
├── place_call.py
├── pulseaudio.service
├── pyproject.toml
├── sounds
│   ├── .. sounds for the pool config
├── switch_detect.sh
├── switch_mon.service
└── switch_mon.sh
```

## Project Files

### Shell Scripts

| Filename | Directory | Description |
|----------|-----------|-------------|
| `config_sys.sh` | `.` | System configuration script that sets up udev rules, systemd services, PulseAudio configuration, and enables necessary system services |
| `led_blue.sh` | `.` | Controls the blue LED on/off (GPIO control for status indication) |
| `led_green.sh` | `.` | Controls the green LED on/off on GPIO 9 (Gateworks GW7200 board) |
| `led_red.sh` | `.` | Controls the red LED on/off on GPIO 26 (Gateworks GW7200 board) |
| `setup_audio_routing.sh` | `VOIP/` | Sets up PulseAudio loopback modules for routing audio between USB headset and SGTL5000 sound card |
| `setup_telit_routing.sh` | `VOIP/` | Configures PulseAudio loopback modules for routing audio between Telit LE910C1 modem and SGTL5000 sound card |
| `start.sh` | `explore/` | Docker container startup script for DEY 4.0 development environment |
| `switch_detect.sh` | `.` | Emergency switch press handler that plays audio alert and initiates emergency call |
| `switch_mon.sh` | `.` | GPIO monitoring service that detects switch press events and triggers the switch_detect script |
| `teardown_audio_routing.sh` | `VOIP/` | Removes PulseAudio loopback modules for headset audio routing |
| `teardown_telit_routing.sh` | `VOIP/` | Removes PulseAudio loopback modules for Telit modem audio routing |
| `show_version.sh` | `integrity-system/` | Displays current version info |
| `check_modifications.sh` | `integrity-system/` | Checks for unauthorized modifications |
| `commit_authorized_changes.sh` | `integrity-system/` | Commits authorized changes |
| `generate_checksums.sh` | `integrity-system/` | Generates checksums for integrity verification |
| `generate_version.sh` | `integrity-system/` | Generates version info |
| `init_deployment.sh` | `integrity-system/` | Initializes deployment |
| `verify_installation.sh` | `integrity-system/` | Verifies installation integrity |



### Python Scripts

| Filename | Directory | Description |
|----------|-----------|-------------|
| `check_reg.py` | `.` | Checks cellular network registration status via AT commands to the Telit modem |
| `EDC_packet.py` | `explore/` | TCP packet transmission using Telit LE910C1 modem with AT commands for event data communication |
| `EDC_packet_direct.py` | `explore/` | Direct TCP socket implementation for sending event packets without using modem AT commands |
| `extract_dev.py` | `explore/` | Extracts USB device interface numbers from PulseAudio source list (used for Telit modem detection) |
| `place_call.py` | `.` | Initiates VoIP calls using baresip, handles audio routing, and logs call events |
| `voip_call_rerouting.py` | `VOIP/` | Monitors baresip output and automatically reroutes audio when calls are established |
| `integrity_monitor.py` | `integrity-system/` | Monitors system integrity and reports unauthorized changes |
| `version_info.py` | `integrity-system/` | Provides version information |
| `voip_call_monitor_tcp.py` | `VOIP/` | Monitors VoIP calls over TCP |

### Markdown Documentation

| Filename | Directory | Description |
|----------|-----------|-------------|
| `GateworksProgrammingInstr.md` | `.` | Programming and setup instructions for Gateworks Venice board with pool configuration |
| `GateworkVOIPProgramming.md` | `.` | Programming instructions specific to VoIP solution on Gateworks Venice board with PoE configuration |
| `InitialProgrammingInstr.md` | `.` | Initial programming instructions for Digiboard CC6 using UUU tool and firmware flashing |
| `POC_NOTE.md` | `.` | Important notes and limitations about the POC (Proof of Concept) units including security warnings |
| `BARESIP_TCP_API.md` | `explore/` | Documentation for Baresip TCP API |
| `PLACE_CALL_FIX.md` | `explore/` | Notes on place call fixes |
| `VOIP_MONITOR_CHANGELOG.md` | `explore/` | Changelog for VoIP monitor |
| `README.txt` | `integrity-system/` | Integrity system documentation |
| `QUICK_REFERENCE.txt` | `integrity-system/` | Quick reference for integrity system |
| `barge_notes.md` | `VOIP/asterisk/` | Notes on asterisk barge feature |

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
