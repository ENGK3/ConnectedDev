#!/bin/bash
# Sed script to substitute UID 1000 with 1001 in service files

sed -i 's/1000/1001/g' pulseaudio.service
sed -i 's/1000/1001/g' manage_modem.service
sed -i 's/1000/1001/g' switch_mon.service

echo "Updated UIDs from 1000 to 1001 in:"
echo "  - pulseaudio.service"
echo "  - manage_modem.service"
echo "  - switch_mon.service"
