# King3 Build Project

This repository contains scripts, configurations, and documentation for the King3 embedded system project, which includes VoIP functionality, cellular modem integration, and audio routing on Gateworks hardware platforms.

## Directory Tree (as of Nov 4, 2025)

```bash
./
├── 99-ignore-modemmanager.rules
├── CHANGELOG.md
├── Digi
│   ├── TF-config
│   └── digi-config
├── GateworkVOIPProgramming.md
├── GateworkVOIPProgramming.pdf
├── GateworksProgrammingInstr.md
├── InitialProgrammingInstr.md
├── K3_QS2_WiringDiagram.png
├── K3_config_settings
├── POC_NOTE.md
├── README.md
├── VERSION_INFO
├── VOIP
│   ├── VOIPLayout.drawio
│   ├── VOIPLayout.png
│   ├── asterisk
│   │   ├── ari-mon-conf.py
│   │   ├── ari.conf
│   │   ├── asterisk.override.conf
│   │   ├── confbridge.conf
│   │   ├── extensions.conf
│   │   ├── http.conf
│   │   ├── modules.conf
│   │   └── pjsip.conf
│   ├── baresip
│   │   ├── accounts
│   │   └── config
│   ├── interfaces
│   ├── pulseaudio
│   │   └── default.pa
│   ├── setup_audio_routing.sh
│   ├── setup_telit_routing.sh
│   ├── teardown_audio_routing.sh
│   ├── teardown_telit_routing.sh
│   ├── voip_ari_conference.service
│   ├── voip_call_monitor.service
│   ├── voip_call_monitor_tcp.py
│   ├── voip_call_rerouting.py
│   └── voip_config.sh
├── asound.state
├── brd1.pkg
├── brd2.pkg
├── check_reg.py
├── config_sys.sh
├── daemon.conf
├── explore
│   └── Ignore for the time being.
├── generate_version.sh
├── gw-venice-gpio-overlay.dts
├── imx8mm-venice-gw7xxx-0x-gpio.dtbo
├── integrity-system
│   └── Ignore for the time being.
├── justfile
├── led_blue.sh
├── led_green.sh
├── led_red.sh
├── microcom.alias
├── modem_utils.py
├── place_call.py
├── pulseaudio.service
├── pyproject.toml
├── send_EDC_info.py
├── show_version.sh
├── sounds
│   └── (audio files for pool configuration)
├── switch_detect.sh
├── switch_mon.service
└── switch_mon.sh
```

## Project Files

### Shell Scripts

| Filename | Directory | Description |
|----------|-----------|-------------|
| `config_sys.sh` | `.` | System configuration script that sets up udev rules, systemd services, PulseAudio configuration, and enables necessary system services |
| `generate_version.sh` | `.` | Generates version information file with git commit hash, branch, and timestamp |
| `led_blue.sh` | `.` | Controls the blue LED on/off (GPIO control for status indication) |
| `led_green.sh` | `.` | Controls the green LED on/off on GPIO 9 (Gateworks GW7200 board) |
| `led_red.sh` | `.` | Controls the red LED on/off on GPIO 26 (Gateworks GW7200 board) |
| `show_version.sh` | `.` | Displays current version information from VERSION_INFO file |
| `setup_audio_routing.sh` | `VOIP/` | Sets up PulseAudio loopback modules for routing audio between USB headset and SGTL5000 sound card |
| `setup_telit_routing.sh` | `VOIP/` | Configures PulseAudio loopback modules for routing audio between Telit LE910C1 modem and SGTL5000 sound card |
| `start.sh` | `explore/` | Docker container startup script for DEY 4.0 development environment |
| `switch_detect.sh` | `.` | Emergency switch press handler that plays audio alert and initiates emergency call |
| `switch_mon.sh` | `.` | GPIO monitoring service that detects switch press events and triggers the switch_detect script |
| `teardown_audio_routing.sh` | `VOIP/` | Removes PulseAudio loopback modules for headset audio routing |
| `teardown_telit_routing.sh` | `VOIP/` | Removes PulseAudio loopback modules for Telit modem audio routing |
| `voip_config.sh` | `VOIP/` | Copies VoIP configuration files (Asterisk, Baresip, PulseAudio, network interfaces) to system directories and sets up systemd services |

### Python Scripts

| Filename | Directory | Description |
|----------|-----------|-------------|
| `check_reg.py` | `.` | Checks cellular network registration status via AT commands to the Telit modem |
| `modem_utils.py` | `.` | Shared module for Telit LE910C1 modem communication providing AT command functions, network registration checking, modem configuration, and TCP socket operations |
| `place_call.py` | `.` | Initiates VoIP calls using baresip, handles audio routing, and logs call events; refactored to use shared modem_utils module |
| `send_EDC_info.py` | `.` | Sends EDC (Emergency Dispatch Center) information packets to remote servers via the cellular modem using TCP; reports extension number, site information, and modem details |
| `ari-mon-conf.py` | `VOIP/asterisk/` | ARI-based conference monitor that automatically adds a specified extension as admin when the first participant joins a ConfBridge conference; captures calling extension for EDC reporting |
| `voip_call_monitor_tcp.py` | `VOIP/` | Monitors baresip via TCP socket interface, handles incoming calls, launches place_call.py for audio routing, and triggers EDC info packet transmission when calls are established |
| `voip_call_rerouting.py` | `VOIP/` | Monitors baresip output and automatically reroutes audio when calls are established by detecting call state changes |

### Systemd Service Files

| Filename | Directory | Description |
|----------|-----------|-------------|
| `pulseaudio.service` | `.` | Systemd user service for PulseAudio sound server, creates runtime directory and runs as user service |
| `switch_mon.service` | `.` | Systemd service for GPIO switch monitoring, depends on network and ttyUSB2 device, runs switch_mon.sh as kuser |
| `voip_ari_conference.service` | `VOIP/` | Systemd service for ARI conference monitoring, depends on Asterisk service, runs ari-mon-conf.py |
| `voip_call_monitor.service` | `VOIP/` | Systemd service for VoIP call monitoring over TCP, depends on Asterisk service and ttyUSB2 device, runs voip_call_monitor_tcp.py |

### Configuration Files

| Filename | Directory | Description |
|----------|-----------|-------------|
| `daemon.conf` | `.` | PulseAudio daemon configuration file with settings for audio processing and system behavior |
| `K3_config_settings` | `.` | Kings III configuration file containing site-specific settings (CID, account code, model, APN, modem UTM, battery voltage) for EDC reporting |
| `ari.conf` | `VOIP/asterisk/` | Asterisk ARI (Asterisk REST Interface) configuration with user credentials and connection settings |
| `asterisk.override.conf` | `VOIP/asterisk/` | Systemd override for Asterisk service, adds dependencies on network and ttyUSB2 device with delayed start and restart |
| `confbridge.conf` | `VOIP/asterisk/` | Asterisk ConfBridge configuration defining user profiles (default_user for extensions 101-104, default_admin for extension 200) and bridge settings |
| `extensions.conf` | `VOIP/asterisk/` | Asterisk dialplan for elevator conference system with extension dialing (101-104, 200, 201) and conference extension 9876 |
| `http.conf` | `VOIP/asterisk/` | Asterisk HTTP server configuration enabling the built-in HTTP server for ARI and other web interfaces |
| `modules.conf` | `VOIP/asterisk/` | Asterisk module loader configuration specifying which modules to load or exclude |
| `pjsip.conf` | `VOIP/asterisk/` | Asterisk PJSIP configuration with transport settings, endpoint templates, and extension definitions (101-104, 200, 201) |
| `config` | `VOIP/baresip/` | Baresip SIP client configuration with audio (PulseAudio), video, and network settings |

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

#### Configuration File (`K3_config_settings`)

Contains site-specific settings:

```bash
CID="5822460189"         # Customer ID
AC="C12345"              # Account Code
MDL="Q01"                # Model designation
APN="broadband"          # Cellular APN
UTM="02EBA09E"           # Modem UTM (auto-retrieved if available)
bat_voltage="1323"       # Battery voltage reading
```

## Ignore the following directories

The directories are experimental and not part of the production code.

```bash
explore
integrity-system
```
