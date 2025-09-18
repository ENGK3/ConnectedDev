#target := "172.20.10.123"
#target := "172.20.10.137"
#target := "172.27.17.9"
#target := "172.20.10.141"
#target := "172.20.10.98"
target := "172.20.10.71"   # Gateworks Target

#nuser := "root"
nuser := "alanh"

service:
    scp switch_mon.service  {{nuser}}@{{target}}:/mnt/data/switch_mon.service
    scp microcom.alias  {{nuser}}@{{target}}:/mnt/data/microcom.alias
    scp 99-ignore-modemmanager.rules {{nuser}}@{{target}}:/mnt/data/99-ignore-modemmanager.rules
    scp config_sys.sh {{nuser}}@{{target}}:/mnt/data/config_sys.sh

boot:
    scp imx8mm-venice-gw7xxx-0x-gw16157.dtbo  {{nuser}}@{{target}}:/mnt/data/imx8mm-venice-gw7xxx-0x-gw16157.dtbo

leds:
    scp led*.sh  {{nuser}}@{{target}}:/mnt/data/.

switch:
    scp switch_detect.sh  {{nuser}}@{{target}}:/mnt/data/switch_detect.sh
    scp switch_mon.sh  {{nuser}}@{{target}}:/mnt/data/switch_mon.sh

sounds:
    scp -r sounds  {{nuser}}@{{target}}:/mnt/data/.
    scp asound.state {{nuser}}@{{target}}:/mnt/data/asound.state

modem:
    scp place_call.py  {{nuser}}@{{target}}:/mnt/data/place_call.py
    scp check_reg.py  {{nuser}}@{{target}}:/mnt/data/check_reg.py

push: modem switch leds service sounds boot
