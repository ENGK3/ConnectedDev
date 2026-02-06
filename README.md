# King3 Build Project

This repository contains scripts, configurations, and documentation for the King3 embedded system project, which includes VoIP functionality, cellular modem integration, and audio routing on Gateworks hardware platforms.

## Directory Tree (as of Feb 02, 2026)

```bash
./
├── 50-k3-config-reboot.rules
├── 99-ignore-modemmanager.rules
├── CHANGELOG.md
├── CONF_ADDING/
│   ├── confbridge.conf
│   └── extensions.conf
├── common/
│   ├── dial_code_utils.py
│   ├── edc_callback.py
│   ├── edit_config.sh
│   ├── encrypt_site_store.sh
│   ├── RSRP_LUT.csv
│   ├── RSRQ_LUT.csv
│   ├── RSSI_LUT.csv
│   ├── site_info (encrypted)
│   ├── site_store.py
│   ├── site.pub
│   └── update_checkin_timer.sh
├── Digi/
│   ├── TF-config
│   └── digi-config
├── GateworksPoolProgrammingInst.md
├── GateworksVOIPProgramming.md
├── InitialProgrammingInstr.md
├── K3_QS2_WiringDiagram.png
├── K3_config_settings.in
├── kings3_install.sh
├── POC_NOTE.md
├── Pool/
│   └── GW-Pool-V00.03.02.tgz
├── programming/
│   ├── menu_modem_stats.py
│   ├── menu_sensor_update.py
│   └── programming.sh
├── README.md
├── tests/
│   ├── check-in-test.md
│   ├── install_quick_cycle.sh
│   ├── remove_quick_cycle.sh
│   └── test_edit_phone_numbers.sh
├── VERSION_INFO
├── VOIP/
│   ├── VOIP-AnswerMode.png
│   ├── VOIP-CallOutMode.png
│   ├── VOIPLayout.drawio
│   ├── VOIPLayout.png
│   ├── asterisk/
│   │   ├── ari-mon-conf.py
│   │   ├── ari-mon-conf-flow.mmd
│   │   ├── ari.conf
│   │   ├── asterisk.override.conf
│   │   ├── confbridge.conf
│   │   ├── extensions.conf
│   │   ├── http.conf
│   │   ├── modules.conf
│   │   └── pjsip.conf
│   ├── baresip/
│   │   ├── accounts
│   │   └── config
│   ├── ep.sh
│   ├── interfaces
│   ├── pulseaudio/
│   │   └── default.pa
│   ├── setup_audio_routing.sh
│   ├── setup_telit_routing.sh
│   ├── teardown_audio_routing.sh
│   ├── teardown_telit_routing.sh
│   ├── voip_ari_conference.service
│   ├── voip_call_monitor.service
│   ├── voip_call_monitor_tcp.py
│   └── voip_call_rerouting.py
├── asound.state
├── audio_routing.py
├── check_reg.py
├── daemon.conf
├── dtmf_collector.py
├── events_monitor.py
├── events_monitor.service
├── explore/
│   ├── EDC_packet.py
│   ├── EDC_packet_direct.py
│   ├── extract_dev.py
│   └── start.sh
├── generate_version.sh
├── get_sensor_data.py
├── get_sensor_data.service
├── get_sensor_data.timer
├── gw-venice-gpio-overlay.dts
├── imx8mm-venice-gw7xxx-0x-gpio.dtbo
├── justfile
├── k3-config-reboot.service
├── led_blue.sh
├── led_green.sh
├── led_red.sh
├── manage_modem.py
├── manage_modem.service
├── markdown-pdf.css
├── microcom.alias
├── modem_manager_client.py
├── modem_state.py
├── modem_utils.py
├── place_call.py
├── pulseaudio.service
├── pyproject.toml
├── send_EDC_info.py
├── send_edc_checkin.service
├── send_edc_checkin.timer
├── set-governor.service
├── show_version.sh
├── sounds/
│   └── (system sound files)
├── sstat.sh
├── start_ss.sh
├── stop_ss.sh
├── switch_detect.sh
├── switch_mon.service
├── switch_mon.sh
├── update_from_SD_card.py
├── update_uid.sh
└── verify_installation.sh
```

## Project Files

### Documentation & Changelog

| Filename | Directory | Description |
|----------|-----------|-------------|
| `README.md` | `.` | Main project documentation, directory structure, and usage guide |
| `CHANGELOG.md` | `.` | Changelog of all software changes, features, fixes, and known issues |


### Programming

The `programming/` directory contains interactive utilities for field configuration and diagnostics of the King3 system.

| Filename | Description |
|----------|-------------|
| `programming.sh` | Interactive menu-driven programming utility for configuring phone numbers, zone numbers, customer account codes, whitelist settings, and audio settings; provides system information including hardware sensor readings and cellular modem statistics |
| `menu_modem_stats.py` | Helper script that retrieves cellular modem statistics (ICCID, IMEI, IMSI, RSRQ, RSRP, signal quality) via AT commands; uses lookup tables (RSRQ_LUT.csv, RSRP_LUT.csv, RSSI_LUT.csv) to convert raw values to readable signal strength indicators; outputs data as shell export statements for use by programming.sh |
| `menu_sensor_update.py` | Helper script that retrieves hardware sensor data (system voltage, CPU temperature) using the `sensors` command and JSON parsing; outputs data as shell export statements for display in programming.sh system information menu |

### Shell Scripts

| Filename | Directory | Description |
|----------|-----------|-------------|
| `kings3_install.sh` | `.` | Unified installation script for Pool and Elevator configurations with package installation, service management, and verification |
| `justfile` | `.` | Build/package automation file for generating, packaging, and releasing project artifacts |
| `generate_version.sh` | `.` | Generates version information file with git commit hash, branch, and timestamp |
| `led_blue.sh` | `.` | Controls the blue LED on/off (GPIO control for status indication) |
| `led_green.sh` | `.` | Controls the green LED on/off on GPIO 9 (Gateworks GW7200 board) |
| `led_red.sh` | `.` | Controls the red LED on/off on GPIO 26 (Gateworks GW7200 board) |
| `show_version.sh` | `.` | Displays current version information from VERSION_INFO file |
| `verify_installation.sh` | `.` | Verifies installation integrity by comparing MD5 checksums and validating installed files |
| `update_uid.sh` | `.` | Updates unique identifier in configuration |
| `sstat.sh` | `.` | Shows systemd service status for all King3 services (get_sensor_data, voip_call_monitor, voip_ari_conference, manage_modem); requires root privileges |
| `start_ss.sh` | `.` | Starts all King3 systemd services (get_sensor_data, voip_call_monitor, voip_ari_conference, manage_modem); requires root privileges |
| `stop_ss.sh` | `.` | Stops all King3 systemd services (get_sensor_data, voip_call_monitor, voip_ari_conference, manage_modem); requires root privileges |
| `encrypt_site_store.sh` | `common/` | Encrypts site configuration files using RSA private key signing; supports both rsautl and pkeyutl methods for OpenSSL compatibility; outputs encrypted binary to site_store file |
| `edit_config.sh` | `common/` | Edits K3_config_settings file with validation; called from Asterisk dialplan for remote configuration updates |
| `update_checkin_timer.sh` | `common/` | Updates send_edc_checkin.timer systemd timer based on CHECKIN_INTERVAL_DAYS from K3_config_settings; supports --install flag for initial setup; reloads systemd daemon and restarts timer when changes are made |
| `setup_audio_routing.sh` | `VOIP/` | Sets up PulseAudio loopback modules for routing audio between USB headset and SGTL5000 sound card |
| `setup_telit_routing.sh` | `VOIP/` | Configures PulseAudio loopback modules for routing audio between Telit LE910C1 modem and SGTL5000 sound card |
| `switch_detect.sh` | `.` | Emergency switch press handler that plays audio alert and initiates emergency call |
| `switch_mon.sh` | `.` | GPIO monitoring service that detects switch press events and triggers the switch_detect script |
| `teardown_audio_routing.sh` | `VOIP/` | Removes PulseAudio loopback modules for headset audio routing |
| `teardown_telit_routing.sh` | `VOIP/` | Removes PulseAudio loopback modules for Telit modem audio routing |

### Python Scripts

| Filename | Directory | Description |
|----------|-----------|-------------|
| `check_reg.py` | `.` | Checks cellular network registration status via AT commands to the Telit modem |
| `manage_modem.py` | `.` | Centralized modem manager providing TCP server interface for stateful modem operations including placing calls, answering calls, handling DTMF, and monitoring call status with conflict prevention; includes SIM management initialization |
| `modem_manager_client.py` | `.` | TCP client library for communicating with manage_modem.py server; provides programmatic interface to modem operations |
| `modem_state.py` | `.` | Diagnostic script that queries and displays current Telit modem audio and call configuration settings via AT commands (not in git) |
| `modem_utils.py` | `.` | Shared module for Telit LE910C1 modem communication providing AT command functions, network registration checking, modem configuration, TCP socket operations, and SIM management (PIN/PUK status, lock/unlock, password changes) |
| `place_call.py` | `.` | Initiates VoIP calls using modem manager TCP interface; reads phone numbers from config, parses dial code prefixes (*50/*54/*55) to control EDC packet behavior, sends EDC packets (respecting prefix) before dialing, and monitors call status with automatic fallback to alternate numbers |
| `send_EDC_info.py` | `.` | Sends EDC (Emergency Dispatch Center) information packets to remote servers via the cellular modem using TCP; reports extension number, site information, and modem details |
| `audio_routing.py` | `.` | Python-based audio routing management for PulseAudio loopback configuration |
| `dtmf_collector.py` | `.` | Collects and processes DTMF tones from cellular calls; implements action dispatch based on DTMF configuration |
| `events_monitor.py` | `.` | System events monitoring daemon; tracks and logs system events for diagnostics |
| `get_sensor_data.py` | `.` | Collects sensor data (temperature, voltage, signal strength) periodically via systemd timer; logs to file for monitoring |
| `update_from_SD_card.py` | `.` | Automates system updates from SD card; checks for update packages and installs them |
| `site_store.py` | `common/` | Decrypts site configuration data using RSA public key verification; provides `decrypt_site_store()` function to retrieve encrypted site information (PIN codes, credentials) stored in site_info file |
| `dial_code_utils.py` | `common/` | Shared utility module for parsing special dial code prefixes (*50/*54/*55) that control EDC (Event Data Collection) packet behavior; used by both manage_modem.py and ari-mon-conf.py to provide unified EDC control across elevator and outgoing call events |
| `edc_callback.py` | `common/` | Async script for EDC callback functionality; ensures existing call is hung up, reads FIRST_NUMBER from config (strips any *5x prefix), initiates callback with EC=CB error code, and adds extension 200 to conference bridge via ARI; invoked from Asterisk dialplan when admin enters #25 DTMF sequence |
| `ari-mon-conf.py` | `VOIP/asterisk/` | ARI-based conference monitor that automatically calls admin extension when first participant joins a ConfBridge conference. Implements intelligent fallback: tries extension 201 first (15-second timeout), then falls back to extension 200 (LTE) if unanswered. Captures calling extension for EDC reporting |
| `voip_call_monitor_tcp.py` | `VOIP/` | Monitors baresip via TCP socket interface, handles incoming calls, launches place_call.py for audio routing, and triggers EDC info packet transmission when calls are established |
| `voip_call_rerouting.py` | `VOIP/` | Monitors baresip output and automatically reroutes audio when calls are established by detecting call state changes |

### Systemd Service Files

| Filename | Directory | Description |
|----------|-----------|-------------|
| `manage_modem.service` | `.` | Systemd service for centralized modem manager, depends on network, Asterisk, and ttyUSB2 device, provides TCP interface on port 5555 |
| `pulseaudio.service` | `.` | Systemd user service for PulseAudio sound server, creates runtime directory and runs as user service |
| `switch_mon.service` | `.` | Systemd service for GPIO switch monitoring, depends on network and ttyUSB2 device, runs switch_mon.sh as kuser |
| `events_monitor.service` | `.` | Systemd service for system events monitoring, runs events_monitor.py to track and log system events |
| `get_sensor_data.service` | `.` | Systemd service for sensor data collection, triggered by get_sensor_data.timer |
| `get_sensor_data.timer` | `.` | Systemd timer for periodic sensor data collection (temperature, voltage, cellular signal strength) |
| `send_edc_checkin.service` | `.` | Systemd service for EDC check-in reporting, executes send_EDC_info.sh with E2 extension parameter, triggered by send_edc_checkin.timer |
| `send_edc_checkin.timer` | `.` | Systemd timer for periodic EDC check-in based on CHECKIN_INTERVAL_DAYS configuration; uses OnBootSec and OnUnitActiveSec to reset cycle after reboot |
| `k3-config-reboot.service` | `.` | Systemd oneshot service that runs update_checkin_timer.sh and reboots the system; allows privileged reboot via PolicyKit for asterisk user |
| `set-governor.service` | `.` | Systemd service to set CPU governor policy on boot for power management |
| `voip_ari_conference.service` | `VOIP/` | Systemd service for ARI conference monitoring, depends on Asterisk service, runs ari-mon-conf.py |
| `voip_call_monitor.service` | `VOIP/` | Systemd service for VoIP call monitoring over TCP, depends on Asterisk service and ttyUSB2 device, runs voip_call_monitor_tcp.py |

### Configuration Files

| Filename | Directory | Description |
|----------|-----------|-------------|
| `daemon.conf` | `.` | PulseAudio daemon configuration file with settings for audio processing and system behavior |
| `50-k3-config-reboot.rules` | `.` | PolicyKit rule granting asterisk user permission to start k3-config-reboot.service for secure system reboot |
|| `K3_config_settings.in` | `.` | **Template file**: Version-controlled template for build process; populated with APP version during package generation |
| `markdown-pdf.css` | `.` | CSS stylesheet for generating PDF documentation from Markdown files, provides VS Code compatible formatting |
| `microcom.alias` | `.` | Bash aliases for microcom serial terminal commands for easier modem interaction |
| `asound.state` | `.` | ALSA sound card state configuration for audio device initialization |
| `site_info` | `common/` | **Encrypted binary**: RSA-encrypted site configuration file containing PIN codes and sensitive data |
| `site.pub` | `common/` | **RSA public key**: 4096-bit RSA public key in PKCS8 format for decrypting site_info file; can be distributed freely |
| `RSRP_LUT.csv` | `common/` | **Lookup table**: Reference Signal Received Power lookup table for cellular signal strength interpretation |
| `RSRQ_LUT.csv` | `common/` | **Lookup table**: Reference Signal Received Quality lookup table for cellular signal quality interpretation |
| `RSSI_LUT.csv` | `common/` | **Lookup table**: Received Signal Strength Indicator lookup table for cellular signal strength interpretation |
| `ari.conf` | `VOIP/asterisk/` | Asterisk ARI (Asterisk REST Interface) configuration with user credentials and connection settings |
| `asterisk.override.conf` | `VOIP/asterisk/` | Systemd override for Asterisk service, adds dependencies on network and ttyUSB2 device with delayed start and restart |
| `confbridge.conf` | `VOIP/asterisk/` | Asterisk ConfBridge configuration defining user profiles (default_user for extensions 101-104, default_admin for extensions 200/201) and bridge settings with user count announcements; includes elevator_admin_menu for DTMF controls |
| `extensions.conf` | `VOIP/asterisk/` | Asterisk dialplan for elevator conference system with extension dialing (101-104, 200, 201), conference extension 9876, admin conference 9877, and configuration management extensions (edit/playback phone numbers, factory reset) |
| `http.conf` | `VOIP/asterisk/` | Asterisk HTTP server configuration enabling the built-in HTTP server for ARI and other web interfaces |
| `modules.conf` | `VOIP/asterisk/` | Asterisk module loader configuration specifying which modules to load or exclude |
| `pjsip.conf` | `VOIP/asterisk/` | Asterisk PJSIP configuration with transport settings, endpoint templates, and extension definitions (101-104, 200, 201) |
| `accounts` | `VOIP/baresip/` | Baresip SIP account configuration with authentication credentials and server settings |
| `config` | `VOIP/baresip/` | Baresip SIP client configuration with audio (PulseAudio), video, and network settings |
| `interfaces` | `VOIP/` | Network interfaces configuration file for Debian-based network setup |
| `default.pa` | `VOIP/pulseaudio/` | PulseAudio default configuration script for audio device initialization and routing |

### Test Scripts & Documentation

| Filename | Directory | Description |
|----------|-----------|-------------|
| `check-in-test.md` | `tests/` | Testing guide for EDC check-in timer functionality, including quick-cycle and verification steps |
| `install_quick_cycle.sh` | `tests/` | Test helper script to install a 2-minute quick cycle override for send_edc_checkin.timer; requires root privileges |
| `remove_quick_cycle.sh` | `tests/` | Test helper script to remove quick cycle override and restore configured timer interval; requires root privileges |

## System Overview

This project implements an embedded communication system with the following key features:

- **Cellular Connectivity**: Telit LE910C1 4G LTE modem for data and voice
- **SIM Security Management**: Automated SIM card lock/unlock with encrypted PIN storage using RSA public/private key encryption
- **VoIP Integration**: Baresip-based SIP client for VoIP calling
- **Audio Routing**: PulseAudio-based dynamic audio routing between multiple audio devices
- **Event Reporting**: TCP-based event transmission to remote servers
- **Emergency Calling**: GPIO-triggered emergency call functionality
- **LED Status Indication**: Visual feedback using RGB LEDs

## Hardware Platforms

- **Gateworks Venice GW7200** - Primary embedded platform
- **Telit LE910C4-NF** - 4G LTE modem module

## Key Technologies

- PulseAudio for audio routing
- Baresip for VoIP functionality
- Serial AT command interface for modem control
- RSA 4096-bit encryption for secure configuration storage
- GPIO control for switches and LEDs
- Docker containerization for cross-compilation
- Systemd services for background monitoring
- Asterisk ARI (REST Interface) for call control and conference management

## VoIP Call Flow

### Conference Admin Connection (Extensions 201 → 200 Fallback)

When an elevator extension (101-104) initiates a conference call:

1. **Primary Admin Call (Extension 201)**
   - System automatically calls extension 201 first
   - 15-second timeout begins
   - If 201 answers within timeout → joins conference as admin
   - Timeout is cancelled, system ready for next conference

2. **Fallback Admin Call (Extension 200 - LTE)**
   - If 201 doesn't answer within 15 seconds
   - Extension 201 is hung up
   - System automatically calls extension 200 (LTE cellular connection)
   - Extension 200 joins conference as admin

3. **Conference Control**
   - Admin extension (201 or 200) has full conference privileges
   - When admin leaves, all participants are automatically disconnected
   - System resets and ready for next conference

#### Configuration File (`K3_config_settings.in`)

Contains site-specific settings the current defaults are:

```bash
MDL="Q01"
APN="broadband"
UTM="02EBA09E"  # Should come from the modem.
bat_voltage="1323"  # Should come from the latest reading of the system.
ZLST="01"
ANSWER_COUNT="2"
PROGRAM_CODE="1234"

WHITELIST="9723256826,9724620611,8668073545,9729560535,9729560536"
MASTER_ANSWER_TO="15"
ENABLE_AUDIO_ROUTING="OFF"

FIRST_NUMBER="9723507770"
SECOND_NUMBER="9727459072"
THIRD_NUMBER="9723507770"

EVT_MON_PERIOD_SECS="600" # event reporting update time in secs
CHECKIN_INTERVAL_DAYS=1
```

## Ignore the following directories

The directories are experimental and not part of the production code.

```bash
explore
integrity-system
```
