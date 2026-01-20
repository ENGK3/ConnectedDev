# CHANGELOG Kings III Software Changes

## Version V00.03.04+ Unreleased

### Added

edit_config_phone.sh script to change the programmed phone numbers in the config file.
test_edit_phone_numbers.sh a test to check the script to edit the config file works
as expected.

### Changed

Updated the extensions.conf and confbridge.conf files to have the dtmf programming for
playing back and editing the three phone numbers that are to be called.

### Removed

The early install scripts voip_config.sh and config_sys.sh have been removed from the repo.


### Known Issues

## Version V00.03.04

### Added

set-governor.service to set the powersave mode on the system to keep the CPU clock
at 1.2 GHz.
Added kings3_install.sh to handle both pool and elevator setups.
```bash
--config pool --update
# Will update installation
--config pool
# Will install the configuration
--config pool --package --update
# Will update installation and install any missing packages.
```

RSRP_LUT.csv, RSRQ_LUT.csv, RSSI_LUT.csv files added to convert modem string values to
human readable values.

events_monitor.py events_monitor.service files to handle reporting events.

update_from_SD_card.py is a script to update from the SD card.

Added audio_routing.py file to extract the audio routing out of place_call.py
since that file no longer needed it.

### Changed

Updated justfile to add the set-governor.service in the package.
Updated justfile to combine both elevator and pool files into one package.

Updated modem_state.py script to include the phone number assigned and
the SW Version number.

Updated microcom.alias to use ttyUSB3

Updated the justfile to create a checksum file (GW-Setup-\<version\>.md5) for the files being installed and
that included with the tar file package.

Updated the switch_mon.service to use "KillSignal=SIGKILL" for terminating the service to prevent dialout
when the system reboots or does a shutdown. Fixes GitHub Issue #3.

place_call.py was updated to pull the numbers to dial from the config file.

modem_utils.py updated to use the info from the different lookup files.

Changed EVT_MON_PERIOD_SECS to 600, so that it matches the get_sensor_data.timer interval.
Cleaned up events_monitor.py

Added code to unlock the sim and lock it if necessary.

### Removed

Removed pool package from justfile, since both configs are in one package file.

### Known Issues

If "kuser" gets a UID other than 1000, then the three services:
pulseaudio.service
manage_modem.service
switch_mon.service
Will not work as expected.

## Version V00.03.03

### Added

Scripts sstat.sh start_ss.sh stop_ss.sh to get the status, start or stop
the various services for the elevator usecase.
An ep.sh script to check on the status of the various pjsip endpoints.
A script modem_state.py to printout the various AT register settings.
A markdown-pdf.css for better looking pdf generation.

GitHub Action to build a package on the push of a tag.

### Changed

Modified the manage_modem.service to include

```bash
ExecStartPre=/bin/sleep 3
```

To prevent AT command errors on startup.

Added option to voip_call_monitor_tcp.py to support --log-baresip
for logging the output from baresip in the event we need to debug a
problem.

Change how the pdf for the markdown files are generated.

### Removed

### Known Issues

## Version V00.03.02-34

### Added

Added the ability to answer incoming calls from the cellular network,
if the calling number is in the whitelist. Added
conference menu for conference admins that allows an extension to be added by
dialing "*5<three_digit_extension>" , e.g. "*5102" would add extension 102 to the
conference with the admin on inbound calls.

Added ability detect the DTMF tones and pass them to baresip for use in menu
control.

Added a script ep.sh - which shows the status to the SIP endpoints. This is not
included in the package currently.

Added a script modem_state.py - which shows the various values for the registers
of the LE910. This is not included in the package currently. It is useful for
debugging.

### Removed

Remove AT#E2SLRI command from the modem setup on the TCP packet sending.
This command is not supported in the version of the LE910 firmware we have.

### Known Issues

However, the audio from the LE910 is not present in the conference.
But the DTMF tones are passed through to the voip_call_monitor_tcp
script to be forwarded to baresip client to control the addition of
extensions this is still being investigated.

### Changed

fix:Missing package. GitHub issue #7
fix: Outbound calling does not work after V3.02 GitHub issue #5

## Version V00.03.02

### Added

Added the ability for extension 201 to join the elevator conference in progress.
The 'elevator conference' will now only end when the last conference admin leaves
the conference.

Added a new program manage_modem.py to replace place_call.py. This program introduced
a different way to interface with the voip_call_monitor_tcp program (now a socket), so
that call status can be communicated to the voip_call_monitor_tcp program. This was
primarily for adding the answer functionality.

Added get_sensor_data (.py, .service, .timer) to capture temp and voltage info.

### Changed

Master phone password in the pjsip.conf file change to make it easy for the phone
to be registered from the phone.

Updated the modem_utils and send_EDC_data script to capture changes made for
additional fields to be retrieved from the SBC.

Added the following fields to the K3_config_settings file.

```bash
ZLIST="01"
WHITELIST="9723256826,9724620611,8668073545,9729560535,9729560536"
MASTER_ANSWER_TO="15"
ENABLE_AUDIO_ROUTING="OFF"
```

### Removed

### Known Issues

The first time an LTE call is attempted it does not complete. It is not clear why.
There is a ticket filed with Telit on this but to this point it has not been responded
to or resolved.

The modem will answer the incoming LTE call, and dial the correct extension, but at the moment
the audio path is failing somewhere along the way.

---

## Version V00.03.01

### Added

### Changed

VoIP Enhancement - Ext 201 -> 200 roll over.

Changed the ari-mon-conf.py script to first dial 201 and if it is not answered
within 15 seconds the call rolls over to the LTE call at extension 200.

Changed how the K3_config_settings file is created so the SW version can be added
automatically.

### Removed

### Known Issues

The first time an LTE call is attempted it does not complete. It is not clear why.
There is a ticket filed with Telit on this but to this point it has not been responded
to or resolved.

---

## Version V00.03.00

### VoIP Enhancement - EDC Information Reporting

The system now automatically sends EDC (Emergency Dispatch Center) information packets when extensions dial into the conference bridge. Key changes include:

### Added

- **Automatic Extension Detection**: When an extension (101-104) joins the conference, the system captures the calling extension number
- **EDC Info Packet**: Sends site identification and extension information to EDC servers via cellular modem
- **Modem Utilities Module**: Refactored modem communication functions into reusable `modem_utils.py` module

### Changed

- **`ari-mon-conf.py`**: Enhanced to detect calling extension from ConfBridge events and trigger EDC reporting
- **`voip_call_monitor_tcp.py`**: Updated to coordinate with EDC info transmission during call setup
- **`place_call.py`**: Refactored to use shared modem utilities; simplified interface
- **`modem_utils.py`**: New shared module for modem AT commands, TCP operations, and network status checking
- **`send_EDC_info.py`**: New script for sending formatted EDC information packets via cellular modem
- **`K3_config_settings`**: New configuration file for site-specific EDC parameters (CID, account code, model, etc.)
### Added

VOIP captures the calling extension and uses the send_EDC_info.py script to send a packet from each extension dialing into the conference.

Refactored the sending of the INFO packet to the EDC servers so that
it could be reused for other reporting.
Created a modem_utils.py file that has many of the modem related command in one file so duplication is avoided.

### Removed

Nothing

---

## Version V00.02.00

Created VOIP configuration that successfully conferences calls to the
operator at the EDC.

---

## Version V00.01.00

### Added

Basic Pool functionality.

### Removed

Nothing.
