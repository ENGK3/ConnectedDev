# EDC Check-in Timer Testing Guide

This document describes how to test the EDC check-in timer functionality without waiting multiple days for verification.

## Overview

The EDC check-in system uses systemd timers to periodically send check-in information based on the `CHECKIN_INTERVAL_DAYS` configuration value. The timer resets on each boot and uses `OnBootSec` and `OnUnitActiveSec` to schedule executions.

## Files Involved

- **send_edc_checkin.service** - Systemd service that executes `/usr/bin/python3 /mnt/data/send_EDC_info.py -e E2`
- **send_edc_checkin.timer** - Systemd timer that schedules the service based on configured interval
- **common/update_checkin_timer.sh** - Helper script to update timer based on `K3_config_settings`
- **K3_config_settings** - Configuration file containing `CHECKIN_INTERVAL_DAYS` (default: 1)

## Testing Strategies

### 1. Fast-Cycle Testing with Temporary Override

Test with a short interval (e.g., 2 minutes) instead of days:

```bash
# SSH into the target device
ssh root@GWorks2

# Create a systemd drop-in override directory
mkdir -p /etc/systemd/system/send_edc_checkin.timer.d

# Create override configuration for 2-minute testing
cat > /etc/systemd/system/send_edc_checkin.timer.d/testing.conf <<'EOF'
[Timer]
OnBootSec=2min
OnUnitActiveSec=2min
EOF

# Reload systemd to pick up the override
systemctl daemon-reload

# Restart the timer to apply new settings
systemctl restart send_edc_checkin.timer

# Monitor the timer status
watch -n 5 'systemctl list-timers send_edc_checkin.timer'
```

**Expected Result**: Timer should trigger every 2 minutes. Watch the logs to confirm:

```bash
journalctl -u send_edc_checkin.service -f
```

**Cleanup**: Remove the override after testing:

```bash
rm -rf /etc/systemd/system/send_edc_checkin.timer.d
systemctl daemon-reload
systemctl restart send_edc_checkin.timer
```

### 2. Manual Service Triggering

Test the service independently without waiting for the timer:

```bash
ssh root@GWorks2

# Manually trigger the service
systemctl start send_edc_checkin.service

# Check the execution logs immediately
journalctl -u send_edc_checkin.service -n 50 --no-pager

# Verify exit status
systemctl status send_edc_checkin.service
```

**Expected Result**: Service should execute successfully with exit code 0.

### 3. Timer Schedule Verification

Verify the timer calculates the correct next execution time:

```bash
ssh root@GWorks2

# Check current timer status and next scheduled run
systemctl list-timers send_edc_checkin.timer

# Get detailed timer information
systemctl status send_edc_checkin.timer

# Show timer properties
systemctl show send_edc_checkin.timer
```

**Expected Output**:
```
NEXT                         LEFT       LAST                         PASSED  UNIT                      ACTIVATES
Wed 2026-02-03 12:06:47 CST  23h left   Tue 2026-02-02 12:06:47 CST  1h ago  send_edc_checkin.timer    send_edc_checkin.service
```

### 4. Boot Behavior Testing

Verify the timer resets properly after reboot:

```bash
ssh root@GWorks2

# Note the current NEXT scheduled time
systemctl list-timers send_edc_checkin.timer

# Reboot the system
reboot

# After reboot, SSH back in and check timer
ssh root@GWorks2
systemctl list-timers send_edc_checkin.timer
```

**Expected Result**: The `NEXT` time should be recalculated from the boot time, not the previous schedule.

### 5. Configuration Change Testing

Test updating the interval via the helper script:

```bash
ssh root@GWorks2

# Check current interval
grep CHECKIN_INTERVAL_DAYS /mnt/data/K3_config_settings

# Update configuration to 2 days
sed -i 's/CHECKIN_INTERVAL_DAYS=.*/CHECKIN_INTERVAL_DAYS=2/' /mnt/data/K3_config_settings

# Run the update script
cd /mnt/data
./common/update_checkin_timer.sh

# Verify the timer file was updated
grep "OnBootSec\|OnUnitActiveSec" /etc/systemd/system/send_edc_checkin.timer

# Check new schedule
systemctl list-timers send_edc_checkin.timer
```

**Expected Result**: Timer intervals should show `2d` and next scheduled run should reflect the change.

### 6. Service Logging Verification

Monitor and verify logging behavior:

```bash
ssh root@GWorks2

# Manually trigger and watch logs in real-time
systemctl start send_edc_checkin.service &
journalctl -u send_edc_checkin.service -f

# Check for recent executions
journalctl -u send_edc_checkin.service --since "1 hour ago"

# Filter by specific patterns (e.g., errors)
journalctl -u send_edc_checkin.service | grep -i error
```

### 7. Dry-Run Mode Testing (Recommended Enhancement)

If the `send_EDC_info.py` script is modified to support a dry-run mode:

```bash
# Temporarily modify the service to use dry-run
sudo sed -i 's|ExecStart=.*|ExecStart=/usr/bin/python3 /mnt/data/send_EDC_info.py -e E2 --dry-run|' \
    /etc/systemd/system/send_edc_checkin.service

systemctl daemon-reload
systemctl start send_edc_checkin.service
journalctl -u send_edc_checkin.service -n 20
```

### 8. Multi-Cycle Automated Test

Run an automated test that triggers and monitors multiple cycles:

```bash
ssh root@GWorks2

# Set to 30-second interval for rapid testing
cat > /etc/systemd/system/send_edc_checkin.timer.d/testing.conf <<'EOF'
[Timer]
OnBootSec=30sec
OnUnitActiveSec=30sec
EOF

systemctl daemon-reload
systemctl restart send_edc_checkin.timer

# Monitor 5 cycles (2.5 minutes)
for i in {1..5}; do
    echo "=== Cycle $i at $(date) ==="
    sleep 30
    journalctl -u send_edc_checkin.service --since "35 seconds ago" | tail -5
    systemctl list-timers send_edc_checkin.timer --no-pager | grep send_edc
done

# Cleanup
rm -rf /etc/systemd/system/send_edc_checkin.timer.d
systemctl daemon-reload
systemctl restart send_edc_checkin.timer
```

## Installation Testing

Test the installation process:

```bash
ssh root@GWorks2
cd /mnt/data

# Run installation with the helper script
./common/update_checkin_timer.sh --install

# Verify installation
systemctl is-enabled send_edc_checkin.timer
systemctl is-active send_edc_checkin.timer
systemctl list-timers send_edc_checkin.timer
```

## Common Issues and Troubleshooting

### Timer Not Running

```bash
# Check if timer is enabled
systemctl is-enabled send_edc_checkin.timer

# Enable if not enabled
systemctl enable send_edc_checkin.timer

# Start the timer
systemctl start send_edc_checkin.timer
```

### Service Fails to Execute

```bash
# Check service status
systemctl status send_edc_checkin.service

# View detailed error logs
journalctl -u send_edc_checkin.service -xe

# Verify script exists and is executable
ls -la /mnt/data/send_EDC_info.py
/usr/bin/python3 /mnt/data/send_EDC_info.py --help
```

### Timer Shows Wrong Interval

```bash
# Verify timer file contents
cat /etc/systemd/system/send_edc_checkin.timer

# Check configuration
grep CHECKIN_INTERVAL_DAYS /mnt/data/K3_config_settings

# Re-run update script
cd /mnt/data
./common/update_checkin_timer.sh
```

### Timer Not Resetting After Boot

```bash
# Check that timer is using OnBootSec (not OnCalendar)
systemctl cat send_edc_checkin.timer | grep OnBootSec

# Verify timer is properly enabled
systemctl list-unit-files | grep send_edc_checkin
```

## Test Checklist

- [ ] Service executes successfully when manually triggered
- [ ] Timer schedules correct interval based on configuration
- [ ] Timer resets after system reboot
- [ ] Configuration changes are applied correctly
- [ ] Logs show expected output in journal
- [ ] Helper script updates timer file correctly
- [ ] Installation process completes without errors
- [ ] Multiple execution cycles work without accumulation/drift

## Performance Expectations

- **Service Execution Time**: < 5 seconds (depends on network)
- **Timer Accuracy**: ± 1 minute for day-based intervals
- **Boot Delay**: 1 day (or configured interval) after boot
- **Configuration Update**: Takes effect after `systemctl daemon-reload`

## Notes

- The timer uses `OnUnitActiveSec` which measures time from when the service last completed
- On system boot, `OnBootSec` determines the initial delay
- The timer is persistent and survives crashes/reboots
- systemd timers have built-in randomization that can be controlled with `RandomizedDelaySec`
- Use `systemd-analyze calendar` to test calendar expressions if switching to `OnCalendar`
