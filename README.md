# King3 Build Project

This repository contains scripts, configurations, and documentation for the King3 embedded system project, which includes VoIP functionality, cellular modem integration, and audio routing on Gateworks hardware platforms.

## Recent Changes from Main Branch

### Summary of Changes
This branch introduces **SIM card security management** functionality with encrypted site configuration storage:

- **SIM Lock/Unlock Management**: New utilities to programmatically lock/unlock SIM cards with PIN codes, check PIN status, and change SIM passwords
- **Encrypted Site Storage**: RSA-based encryption system for securing site-specific configuration data (PIN codes, credentials) using public/private key pairs
- **Integration**: Modem manager now automatically manages SIM security state on startup using encrypted site configuration

### Modified Files
- [manage_modem.py](manage_modem.py) - Added SIM management initialization on startup using encrypted site store
- [modem_utils.py](modem_utils.py) - Added comprehensive SIM management functions: `check_sim_pin_status()`, `check_sim_lock_status()`, `unlock_sim_with_pin()`, `set_sim_password_and_lock()`, `manage_sim()`
- [justfile](justfile) - Updated target IP and packaging to include new site store files
- [kings3_install.sh](kings3_install.sh) - Updated package dependencies (formatting change)
- `.gitignore` - Added patterns to exclude sensitive key files

### New Files (common/ directory)
- [common/site_store.py](common/site_store.py) - Python module for decrypting site configuration using RSA public key verification
- [common/encrypt_site_store.sh](common/encrypt_site_store.sh) - Bash script for encrypting site configuration with RSA private key
- `common/site_info` - Encrypted binary site configuration file (contains PIN codes and other sensitive data)
- `common/site.pub` - RSA 4096-bit public key for decrypting site configuration

See [ENCRYPTION_USAGE.md](ENCRYPTION_USAGE.md) for detailed encryption/decryption usage documentation.

## Directory Tree (as of Nov 4, 2025)

```bash
./
├── 99-ignore-modemmanager.rules
├── CHANGELOG.md
├── common
│   ├── encrypt_site_store.sh
│   ├── site_info (encrypted)
│   ├── site_store.py
│   └── site.pub
├── Digi
│   ├── TF-config
│   └── digi-config
├── ENCRYPTION_USAGE.md
├── GateworkVOIPProgramming.md
├── GateworkVOIPProgramming.pdf
├── GateworksProgrammingInstr.md
├── InitialProgrammingInstr.md
├── K3_QS2_WiringDiagram.png
├── K3_config_settings.in
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
│   ├── ep.sh
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
├── manage_modem.py
├── manage_modem.service
├── markdown-pdf.css
├── microcom.alias
├── modem_state.py
├── modem_utils.py
├── place_call.py
├── pulseaudio.service
├── pyproject.toml
├── send_EDC_info.py
├── show_version.sh
├── sounds
│   └── (audio files for pool configuration)
├── sstat.sh
├── start_ss.sh
├── stop_ss.sh
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
| `sstat.sh` | `.` | Shows systemd service status for all King3 services (get_sensor_data, voip_call_monitor, voip_ari_conference, manage_modem); requires root privileges |
| `start_ss.sh` | `.` | Starts all King3 systemd services (get_sensor_data, voip_call_monitor, voip_ari_conference, manage_modem); requires root privileges |
| `stop_ss.sh` | `.` | Stops all King3 systemd services (get_sensor_data, voip_call_monitor, voip_ari_conference, manage_modem); requires root privileges |
| `encrypt_site_store.sh` | `common/` | Encrypts site configuration files using RSA private key signing; supports both rsautl and pkeyutl methods for OpenSSL compatibility; outputs encrypted binary to site_store file |
| `ep.sh` | `VOIP/` | Shows Asterisk PJSIP endpoint status including availability and contact information; must be run as root |
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
| `manage_modem.py` | `.` | Centralized modem manager providing TCP server interface for stateful modem operations including placing calls, answering calls, handling DTMF, and monitoring call status with conflict prevention; includes SIM management initialization |
| `modem_state.py` | `.` | Diagnostic script that queries and displays current Telit modem audio and call configuration settings via AT commands |
| `modem_utils.py` | `.` | Shared module for Telit LE910C1 modem communication providing AT command functions, network registration checking, modem configuration, TCP socket operations, and SIM management (PIN/PUK status, lock/unlock, password changes) |
| `place_call.py` | `.` | Initiates VoIP calls using baresip, handles audio routing, and logs call events; refactored to use shared modem_utils module |
| `send_EDC_info.py` | `.` | Sends EDC (Emergency Dispatch Center) information packets to remote servers via the cellular modem using TCP; reports extension number, site information, and modem details |
| `site_store.py` | `common/` | Decrypts site configuration data using RSA public key verification; provides `decrypt_site_store()` function to retrieve encrypted site information (PIN codes, credentials) stored in site_info file |
| `ari-mon-conf.py` | `VOIP/asterisk/` | ARI-based conference monitor that automatically calls admin extension when first participant joins a ConfBridge conference. Implements intelligent fallback: tries extension 201 first (15-second timeout), then falls back to extension 200 (LTE) if unanswered. Captures calling extension for EDC reporting |
| `voip_call_monitor_tcp.py` | `VOIP/` | Monitors baresip via TCP socket interface, handles incoming calls, launches place_call.py for audio routing, and triggers EDC info packet transmission when calls are established |
| `voip_call_rerouting.py` | `VOIP/` | Monitors baresip output and automatically reroutes audio when calls are established by detecting call state changes |

### Systemd Service Files

| Filename | Directory | Description |
|----------|-----------|-------------|
| `manage_modem.service` | `.` | Systemd service for centralized modem manager, depends on network, Asterisk, and ttyUSB2 device, provides TCP interface on port 5555 |
| `pulseaudio.service` | `.` | Systemd user service for PulseAudio sound server, creates runtime directory and runs as user service |
| `switch_mon.service` | `.` | Systemd service for GPIO switch monitoring, depends on network and ttyUSB2 device, runs switch_mon.sh as kuser |
| `voip_ari_conference.service` | `VOIP/` | Systemd service for ARI conference monitoring, depends on Asterisk service, runs ari-mon-conf.py |
| `voip_call_monitor.service` | `VOIP/` | Systemd service for VoIP call monitoring over TCP, depends on Asterisk service and ttyUSB2 device, runs voip_call_monitor_tcp.py |

### Configuration Files

| Filename | Directory | Description |
|----------|-----------|-------------|
| `daemon.conf` | `.` | PulseAudio daemon configuration file with settings for audio processing and system behavior |
| `K3_config_settings` | `.` | **Generated file**: Kings III configuration file containing site-specific settings (CID, account code, model, APN, APP version, modem UTM, battery voltage) for EDC reporting. This file is generated from the `K3_config_settings.in` template during the build process. |
| `K3_config_settings.in` | `.` | **Template file**: Version-controlled template for `K3_config_settings`. This file is populated with the APP version and other variables during the build process to produce the final configuration file. |
| `markdown-pdf.css` | `.` | CSS stylesheet for generating PDF documentation from Markdown files, provides VS Code compatible formatting |
| `site_info` | `common/` | **Encrypted binary**: RSA-encrypted site info |
| `site.pub` | `common/` | **RSA public key**: 4096-bit RSA public key in PKCS8 format for decrypting site_info file; can be distributed freely |
| `ari.conf` | `VOIP/asterisk/` | Asterisk ARI (Asterisk REST Interface) configuration with user credentials and connection settings |
| `asterisk.override.conf` | `VOIP/asterisk/` | Systemd override for Asterisk service, adds dependencies on network and ttyUSB2 device with delayed start and restart |
| `confbridge.conf` | `VOIP/asterisk/` | Asterisk ConfBridge configuration defining user profiles (default_user for extensions 101-104, default_admin for extensions 200/201) and bridge settings with user count announcements |
| `extensions.conf` | `VOIP/asterisk/` | Asterisk dialplan for elevator conference system with extension dialing (101-104, 200, 201) and conference extension 9876 |
| `http.conf` | `VOIP/asterisk/` | Asterisk HTTP server configuration enabling the built-in HTTP server for ARI and other web interfaces |
| `modules.conf` | `VOIP/asterisk/` | Asterisk module loader configuration specifying which modules to load or exclude |
| `pjsip.conf` | `VOIP/asterisk/` | Asterisk PJSIP configuration with transport settings, endpoint templates, and extension definitions (101-104, 200, 201) |
| `config` | `VOIP/baresip/` | Baresip SIP client configuration with audio (PulseAudio), video, and network settings |

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
- **Telit LE910C1-NF** - 4G LTE modem module

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
