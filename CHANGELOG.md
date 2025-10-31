# CHANGELOG Kings III Software Changes

## Version V00.03.00

### Added

VOIP captures the calling extension and uses the send_EDC_info.py script to send a packet from each extension dialing into the conference.

### Changed

Refactored the sending of the INFO packet to the EDC servers so that
it could be reused for other reporting.
Created a modem_utils.py file that has many of the modem related command in one file so duplication is avoided.

### Removed

Nothing

## Version V00.02.00

Created VOIP configuration that successfully conferences calls to the
operator at the EDC.

## Version V00.01.00

### Added

Basic Pool functionality.

### Removed

Nothing.
