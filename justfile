#target := "172.20.10.123"
target := "172.20.10.137"
#target := "172.27.17.9"


service:
    scp switch_mon.service  root@{{target}}:/mnt/data/switch_mon.service
    scp microcom.alias  root@{{target}}:/mnt/data/microcom.alias
    scp 99-ignore-modemmanager.rules root@{{target}}:/mnt/data/99-ignore-modemmanager.rules

leds:
    scp led*.sh  root@{{target}}:/mnt/data/.

switch:
    scp switch_detect.sh  root@{{target}}:/mnt/data/switch_detect.sh
    scp switch_mon.sh  root@{{target}}:/mnt/data/switch_mon.sh

sounds:
    scp -r sounds  root@{{target}}:/mnt/data/.

modem:
    scp place_call.py  root@{{target}}:/mnt/data/place_call.py
    scp check_reg.py  root@{{target}}:/mnt/data/check_reg.py

push: modem switch leds service sounds
