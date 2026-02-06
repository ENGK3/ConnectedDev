# CHANGELOG Kings III Software Changes

## Version V00.03.06+ UNRELEASED

### Added

**EDC Callback Feature**: Implemented callback functionality to allow admin to initiate an outbound call back to the primary phone number with error code EC=CB send in the packet to the EDC:

- [common/edc_callback.py](common/edc_callback.py) - Async Python script that handles EDC callback; includes comprehensive error handling and timeout management- Added #25 menu entry in elevator_admin_menu to trigger edc_callback extension



**EDC Check-in Timer System**: Implemented the DTMF programming for 07, the "Check-In Interval". Implemented as a systemd-based periodic check-in functionality that sends EDC information at configurable day intervals. The system includes:
- [send_edc_checkin.service](send_edc_checkin.service) - Systemd service that executes send_EDC_info.py with E2 extension parameter
- [send_edc_checkin.timer](send_edc_checkin.timer) - Systemd timer that schedules check-ins based on CHECKIN_INTERVAL_DAYS configuration; uses OnBootSec and OnUnitActiveSec to reset cycle after each reboot
- [common/update_checkin_timer.sh](common/update_checkin_timer.sh) - Helper script to dynamically update timer intervals from K3_config_settings; supports --install flag for initial setup
- [tests/check-in-test.md](tests/check-in-test.md) - Comprehensive testing documentation with strategies for validating timer functionality without waiting multiple days
- [tests/install_quick_cycle.sh](tests/install_quick_cycle.sh) - Test helper script to install 2-minute quick cycle timer override for rapid testing; requires root privileges
- [tests/remove_quick_cycle.sh](tests/remove_quick_cycle.sh) - Test helper script to remove quick cycle override and restore configured timer interval; requires root privileges

**System Reboot via DTMF**: Implemented secure system reboot functionality accessible through Asterisk conference menu (99#) using PolicyKit authorization:

- [k3-config-reboot.service](k3-config-reboot.service) - Systemd oneshot service that runs update_checkin_timer.sh and executes system reboot; allows asterisk user to trigger privileged operations without sudo
- [50-k3-config-reboot.rules](50-k3-config-reboot.rules) - PolicyKit rule granting asterisk user permission to start k3-config-reboot.service via systemctl; installed to /etc/polkit-1/rules.d/
- Updated [VOIP/asterisk/confbridge.conf](VOIP/asterisk/confbridge.conf) - Added 99# menu entry to trigger reboot_system extension
- Updated [VOIP/asterisk/extensions.conf](VOIP/asterisk/extensions.conf) - Added reboot_system extension in addcallers context to execute systemctl command


### Changed

Small refactoring of send_EDC_info.py to clean up imports and add -h,--help argument.

Updated [kings3_install.sh](kings3_install.sh) to install and configure the EDC check-in timer system:

- Added send_edc_checkin.service to setup_common_files function
- Added send_edc_checkin.timer to both pool and elevator mode service installations
- Added edc_callback.py to install.
- Automatically runs update_checkin_timer.sh during installation to configure timer intervals from K3_config_settings

- Updated [VOIP/asterisk/extensions.conf](VOIP/asterisk/extensions.conf) - Change the enter_ext extension dialplan to use "extension" prompt file

**Enhanced Lock Debugging in manage_modem.py**: Added extensive lock acquisition timing and debug logging throughout the call placement workflow to diagnose potential deadlock issues:

- Updated [manage_modem.py](manage_modem.py) - Added [LOCK_DEBUG] logging statements in `_place_call_worker()` to track serial_lock acquisition and release for determining when lock is
being held for long periods of time.

### Fixed

**Phone Number Editing with Special Characters** (Issue #15): Fixed [common/edit_config.sh](common/edit_config.sh) to properly handle special characters (`*` and `#`) in phone numbers:

- Added escape sequence for special characters (`*`, `#`, `/`, `&`) before using them in sed replacement commands
- Changed verification from regex matching to literal string matching using `grep -F` to avoid regex interpretation issues
- Phone numbers like `*558881114321` and `#549128234567` now correctly stored in configuration file

**DTMF Translation for Phone Numbers** (Issue #5): Updated [VOIP/asterisk/extensions.conf](VOIP/asterisk/extensions.conf) to conditionally apply DTMF translation:

- DTMF sequences (`*1`=A, `*2`=B, etc.) now only translated for AC (customer account) parameter
- Phone number parameters (FIRST_NUMBER, SECOND_NUMBER, THIRD_NUMBER) use raw DTMF input without translation
- Preserves special characters `*` and `#` in phone numbers entered via DTMF

**Test Infrastructure**: Enhanced [tests/test_edit_phone_numbers.sh](tests/test_edit_phone_numbers.sh) to support both local and remote testing:

- Added local testing mode with automatic temporary test environment creation

### Known Issues

There is an inexplicable delay in the hangup function when being executed by the manage_modem code.
Debugging has been added but it is disabled by default. This needs further investigation.

## Version V00.03.06

### Added

Created a tests directory and added a TEST_README.md to describe the different tests.
New tests, tests/test_dtmf_translate.py and test_manage_modem.py to test functionality.
Added ability to enter the letters 'A' - 'F' and '*' and '#' as part of the dtmf data entry.

Added menu entries for the manual tests, for the following commands:
05 (Implemented as 75#) for "My Number" and 07 (Implemented as 77#) for the Prompt version which
is interpreted as the Software version.

Added implementation of answering only after "ANSWER_COUNT" rings.

### Changed

The script manage_modem now gathers the CNUM info and stores it in the K3_config_settings file. NOTE there is a delay between unlocking and retrieving the CNUM data. This is deliberate because the CNUM would return an ERROR if CNUM was executed immediately after unlocking.

Sim unlocking code now uses the TMobile PIN if the AT&T version doesn't work. No effort is made to determine what type of SIM is present.

The ownership of the K3_config_settings is owned by asterisk because of the need to have asterisk edit the file.  Also the sticky bit on the /mnt/data directory was set so the ownership doesn't change to the last writer for the K3_config_settings file.

Tweaked the ./kings3_install.sh verify function. Also added a restart of Asterisk as part of the update to pick up Asterisk config file changes.

Refactored the kings3_install.sh script to be more maintainable.

Added handling of special phone number prefixes :

#### Special Dial Codes

| Prefix | Behavior | Example |
|--------|----------|---------|
| `*50` | **No EDC packet** - Dials the number without sending any EDC packet | `*509723105316` dials `9723105316` (no packet) |
| `*54` | **DC Code** - Sends EDC packet with "DC" diagnostic code, then dials | `*548881237777` sends DC packet, dials `8881237777` |
| `*55` | **Normal Code** - Sends EDC packet with normal "01" code, then dials | `*555551234567` sends packet, dials `5551234567` |
| None | **Default** - Sends EDC packet with normal code (backward compatible) | `9723105316` sends packet, dials `9723105316` |

Note the sending for the packet to the EDC moved from manage_modem, to the scripts that initiate the dialing.
namely ari-mon-conf.py in the elevator configuration and place_call.py in the pool configuration.

Removed the phone number from the voip_call_monitor.service.

The script voip_call_monitory_tcp.py now reads from the K3_config_settings to get it's phone numbers and
now has the ability to cycle through numbers if call are not connected.

Merged in the cli_programming branch from this sha dcb854c.

### Removed

NA.

### Fixed

Issue #11, "Need to update "CID" field in K3_config_settings dynamically"
Issue #10, "Need to add ability to use T-Mobile SIMs after 00.03.04 update"

### Known Issues

Sending of the EDC packet is dictated by the FIRST_PHONE variable in the K3_config_settings file.
If the SECOND and THIRD number have different setting as far as the prefix ("*5x") is concerned they are not obeyed.

## Version V00.03.05

### Added

edit_config.sh script to change the programmed phone numbers in the config file.
test_edit_phone_numbers.sh a test to check the script to edit the config file works
as expected.
Implemented the reset to factory defaults for the configuration settings.
Implemented the ability to change the Customer Account code, BUT, only can enter digits.
Using letters in dtmf entry is not yet implemented.

Added ANSWER_COUNT="2" and PROGRAM_CODE="1234" in the config file, for the dtmf programming, but they are not implemented in the code, YET.

Completed the elevator verification of the elevator installation. This can be run with
the following command:

```bash
./kings3_install.sh --verify GW-Setup-V00.03.04-24-g0d82072.md5
.... output abbreviated ...
Checking for unexpected files:
No unexpected files found

==============================================
Sounds Directory Verification Summary
==============================================
Expected files:    15
Found:             15
Missing:           0
Unexpected:        0
==============================================

Sounds directory verification SUCCESSFUL!

================================
OVERALL VERIFICATION PASSED!
================================
```

### Changed

Updated the extensions.conf and confbridge.conf files to have the dtmf programming for
playing back and editing the three phone numbers that are to be called.
The king3_install scripts now edits the K3_config_settings in the installation to set which config is installed, in
the form of the HW_APP variable. It can be set to "Pool" or "Elevator"
Changed the kings3_install.sh script to be able to verify that the installed files match those in the package.
Changed the name of the K3_config_settings file to be K3_config_settings.default

The kings3_install.sh script was changed to copy in new values from K3_config_settings.default file only if the K3_config_settings is not present.

The kings3_install.sh script was changed to make sure the K3_config_settings file is owned by the asterisk user.
IF this is not the case, the updating of the file will not happen correctly.

### Removed

The early install scripts voip_config.sh and config_sys.sh have been removed from the repo.

### Known Issues

Setting the SIM lock for T-Mobile sims does not work.
Entering data in the dtmf programming accepts only digits currently.

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
