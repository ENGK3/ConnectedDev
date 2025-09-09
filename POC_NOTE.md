# POOL POC NOTES

There are a number of assumptions about these POC units that should be made clear.

1. There is **NO PASSWORD** root login. Type root at the serial console prompt.
1. There is **NO PIN** set on the sim card.
1. There is **NO Firmware Over The Air** (FOTA) update.
1. This is **NO hardenging** of the system to prevent malicious intruders from causing problems.
1. There is a call log file produced in the /mnt/data/calls.log file. There is no limit on the size of this
file, so care should be taken to make sure it doesn't get too big. Also note that the times in it may be erronious as
there is no Real Time Clock and the time is not captured from the LTE network.
1. There is an issue on a controlled shutdown where the unit makes an unintended call. This is not an issue if the power is just removed.

