#target := "172.20.10.123"
#target := "172.20.10.137"
#target := "172.27.17.9"
#target := "172.20.10.141"
#target := "172.20.10.93"
target := "172.20.10.223"   # Gateworks Target
#target := "172.27.17.9"

#nuser := "root"
nuser := "kuser"

pulse:
    scp daemon.conf  {{nuser}}@{{target}}:/mnt/data/pulse/daemon.conf
    scp pulseaudio.service {{nuser}}@{{target}}:/mnt/data/pulse/pulseaudio.service
    scp VOIP/pulseaudio/default.pa  {{nuser}}@{{target}}:/mnt/data/pulse/default.pa
    # scp setup_audio_routing.sh  {{nuser}}@{{target}}:/mnt/data/pulse/setup_audio_routing.sh
    # scp setup_telit_routing.sh  {{nuser}}@{{target}}:/mnt/data/pulse/setup_telit_routing.sh
    # scp teardown_audio_routing.sh  {{nuser}}@{{target}}:/mnt/data/pulse/teardown_audio_routing.sh
    # scp teardown_telit_routing.sh  {{nuser}}@{{target}}:/mnt/data/pulse/teardown_telit_routing.sh

service:
    scp switch_mon.service  {{nuser}}@{{target}}:/mnt/data/switch_mon.service
    scp microcom.alias  {{nuser}}@{{target}}:/mnt/data/microcom.alias
    scp 99-ignore-modemmanager.rules {{nuser}}@{{target}}:/mnt/data/99-ignore-modemmanager.rules
    scp config_sys.sh {{nuser}}@{{target}}:/mnt/data/config_sys.sh

boot:
    scp imx8mm-venice-gw7xxx-0x-gpio.dtbo {{nuser}}@{{target}}:/mnt/data/imx8mm-venice-gw7xxx-0x-gpio.dtbo

leds:
    scp led*.sh {{nuser}}@{{target}}:/mnt/data/.

switch:
    scp switch_detect.sh {{nuser}}@{{target}}:/mnt/data/switch_detect.sh
    scp switch_mon.sh {{nuser}}@{{target}}:/mnt/data/switch_mon.sh

sounds:
    scp -r sounds {{nuser}}@{{target}}:/mnt/data/.
    scp asound.state {{nuser}}@{{target}}:/mnt/data/asound.state

modem:
    scp place_call.py {{nuser}}@{{target}}:/mnt/data/place_call.py
    scp check_reg.py {{nuser}}@{{target}}:/mnt/data/check_reg.py

voip:
    scp VOIP/voip_call_monitor_tcp.py {{nuser}}@{{target}}:/mnt/data/voip_call_monitor_tcp.py
    scp VOIP/voip_call_monitor.service {{nuser}}@{{target}}:/mnt/data/voip_call_monitor.service
    scp VOIP/baresip/config {{nuser}}@{{target}}:/mnt/data/baresip.config
    scp VOIP/baresip/accounts {{nuser}}@{{target}}:/mnt/data/accounts
    scp 99-ignore-modemmanager.rules {{nuser}}@{{target}}:/mnt/data/99-ignore-modemmanager.rules

conf:
    scp VOIP/asterisk/extensions.conf {{nuser}}@{{target}}:/mnt/data/extensions.conf
    scp VOIP/asterisk/confbridge.conf {{nuser}}@{{target}}:/mnt/data/confbridge.conf

ari:
    scp VOIP/asterisk/ari-mon-conf.py {{nuser}}@{{target}}:/mnt/data/ari-mon-conf.py
    scp VOIP/voip_ari_conference.service {{nuser}}@{{target}}:/mnt/data/voip_ari_conference.service

asterisk:
    scp VOIP/interfaces {{nuser}}@{{target}}:/mnt/data/interfaces
    scp VOIP/asterisk/pjsip.conf {{nuser}}@{{target}}:/mnt/data/pjsip.conf
    scp VOIP/asterisk/extensions.conf {{nuser}}@{{target}}:/mnt/data/extensions.conf
    scp VOIP/voip_config.sh {{nuser}}@{{target}}:/mnt/data/voip_config.sh
    scp VOIP/asterisk/confbridge.conf {{nuser}}@{{target}}:/mnt/data/confbridge.conf

push: modem switch leds service sounds boot pulse voip asterisk

vpush: asterisk voip modem pulse modem

pkg:
    rm -f GW-Pool-Setup.tgz
    tar -zcvf GW-Pool-Setup.tgz sounds/* *.py *.sh *.service *.dtbo *.conf 99* *.alias

pkgvoip:
    rm -f GW-VoIP-Setup*.tgz
    tar -zcvf GW-VoIP-Setup.tgz place_call.py daemon.conf \
        pulseaudio.service  99-ignore-modemmanager.rules \
        -C VOIP \
        voip_call_monitor_tcp.py voip_call_monitor.service voip_config.sh \
        interfaces \
        -C baresip \
        accounts config \
        -C ../asterisk \
         pjsip.conf extensions.conf \
        -C ../pulseaudio \
        default.pa

vpkgpush: pkgvoip
    scp GW-VoIP-Setup.tgz {{nuser}}@{{target}}:/mnt/data/.
