#!/usr/bin/bash
# Script to show PJSIP endpoint status in Asterisk
# Must be run on the Asterisk server as root
echo ""
asterisk -rx "pjsip show endpoints" \
	| awk ' /Endpoint:/ {ep=$2;}
	/Unavailable|Avail/ {state=$4;}
	/Contact/ {contacts=$2; printf ">%s<>%s<>%s<\n", ep, state, contacts;}
	' | grep -v CID
echo ""
