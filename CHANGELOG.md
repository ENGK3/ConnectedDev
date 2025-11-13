# CHANGELOG Kings III Software Changes

## Version V00.03.02


### Added

Added the ability for extension 201 to join the elevator conference in progress.
The 'elevator conference' will now only end when the last conference admin leaves
the conference.

### Changed

### Removed

### Known Issues

The first time an LTE call is attempted it does not complete. It is not clear why.
There is a ticket filed with Telit on this but to this point it has not been responded
to or resolved.

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
