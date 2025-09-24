#target := "172.20.10.123"
#target := "172.20.10.137"
#target := "172.27.17.9"
#target := "172.20.10.141"
#target := "172.20.10.98"
target := "172.20.10.71"   # Gateworks Target
#target := "172.27.17.22"

#nuser := "root"
nuser := "kuser"

pulse:
    scp daemon.conf  {{nuser}}@{{target}}:/mnt/data/pulse/daemon.conf
    scp pulseaudio.service {{nuser}}@{{target}}:/mnt/data/pulse/pulseaudio.service
    scp setup_audio_routing.sh  {{nuser}}@{{target}}:/mnt/data/pulse/setup_audio_routing.sh
    scp setup_telit_routing.sh  {{nuser}}@{{target}}:/mnt/data/pulse/setup_telit_routing.sh
    scp teardown_audio_routing.sh  {{nuser}}@{{target}}:/mnt/data/pulse/teardown_audio_routing.sh
    scp teardown_telit_routing.sh  {{nuser}}@{{target}}:/mnt/data/pulse/teardown_telit_routing.sh

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

push: modem switch leds service sounds boot pulse
