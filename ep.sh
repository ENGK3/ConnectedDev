
echo ""
asterisk -rx "pjsip show endpoints" \
	| awk ' /Endpoint:/ {ep=$2;}
	/Unavailable|Avail/ {state=$4;}
	/Contact/ {contacts=$2; printf ">%s<>%s<>%s<\n", ep, state, contacts;}
	' | grep -v CID
echo ""
