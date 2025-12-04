#target := "172.20.10.123"
#target := "172.20.10.137"
#target := "172.27.17.9"
#target := "172.20.10.141"
#target := "172.20.10.93"
target := "172.20.10.223"   # Gateworks Target
#target := "172.27.17.41"

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

modem: k3_config
    scp place_call.py {{nuser}}@{{target}}:/mnt/data/place_call.py
    scp check_reg.py {{nuser}}@{{target}}:/mnt/data/check_reg.py
    scp modem_utils.py {{nuser}}@{{target}}:/mnt/data/modem_utils.py
    scp manage_modem.py {{nuser}}@{{target}}:/mnt/data/manage_modem.py
    scp modem_manager_client.py {{nuser}}@{{target}}:/mnt/data/modem_manager_client.py
    scp manage_modem.service {{nuser}}@{{target}}:/mnt/data/manage_modem.service
    scp VOIP/voip_call_monitor_tcp.py {{nuser}}@{{target}}:/mnt/data/voip_call_monitor_tcp.py
    scp send_EDC_info.py {{nuser}}@{{target}}:/mnt/data/send_EDC_info.py
    scp K3_config_settings {{nuser}}@{{target}}:/mnt/data/K3_config_settings

voip:
    scp VOIP/voip_call_monitor_tcp.py {{nuser}}@{{target}}:/mnt/data/voip_call_monitor_tcp.py
    scp VOIP/voip_call_monitor.service {{nuser}}@{{target}}:/mnt/data/voip_call_monitor.service
    scp VOIP/baresip/config {{nuser}}@{{target}}:/mnt/data/baresip.config
    scp VOIP/baresip/accounts {{nuser}}@{{target}}:/mnt/data/accounts
    scp 99-ignore-modemmanager.rules {{nuser}}@{{target}}:/mnt/data/99-ignore-modemmanager.rules

conf:
    scp VOIP/asterisk/extensions.conf {{nuser}}@{{target}}:/mnt/data/extensions.conf
    scp VOIP/asterisk/confbridge.conf {{nuser}}@{{target}}:/mnt/data/confbridge.conf
    scp VOIP/asterisk/pjsip.conf {{nuser}}@{{target}}:/mnt/data/pjsip.conf
    scp VOIP/asterisk/http.conf {{nuser}}@{{target}}:/mnt/data/http.conf
    scp VOIP/asterisk/ari.conf {{nuser}}@{{target}}:/mnt/data/ari.conf

pullconf:
    scp {{nuser}}@{{target}}:/etc/asterisk/extensions.conf ./VOIP/asterisk/extensions.conf.pull
    scp {{nuser}}@{{target}}:/etc/asterisk/confbridge.conf ./VOIP/asterisk/confbridge.conf.pull
    scp {{nuser}}@{{target}}:/etc/asterisk/pjsip.conf ./VOIP/asterisk/pjsip.conf.pull
    scp {{nuser}}@{{target}}:/etc/asterisk/http.conf ./VOIP/asterisk/http.conf.pull
    scp {{nuser}}@{{target}}:/etc/asterisk/ari.conf ./VOIP/asterisk/ari.conf.pull
    scp {{nuser}}@{{target}}:/etc/asterisk/features.conf ./VOIP/asterisk/features.conf.pull

ari:
    scp VOIP/asterisk/ari-mon-conf.py {{nuser}}@{{target}}:/mnt/data/ari-mon-conf.py
    scp VOIP/voip_ari_conference.service {{nuser}}@{{target}}:/mnt/data/voip_ari_conference.service

asterisk: ari conf
    scp VOIP/interfaces {{nuser}}@{{target}}:/mnt/data/interfaces
    scp VOIP/voip_config.sh {{nuser}}@{{target}}:/mnt/data/voip_config.sh

# Generate version information from Git
version:
    ./generate_version.sh

# Show version information
show-version:
    ./show_version.sh

push: modem switch leds service sounds boot pulse voip asterisk

vpush: asterisk voip modem pulse modem

my_version := `grep '^VERSION=' VERSION_INFO | cut -d= -f2`

pkg:
    rm -f GW-Pool-Setup*.tgz
    tar -zcvf GW-Pool-Setup.tgz sounds/* *.py *.sh *.service \
        *.dtbo *.conf 99* *.alias


k3_config:
    cat K3_config_settings.in > K3_config_settings
    echo 'APP="{{my_version}}"' >> K3_config_settings

pkgvoip: k3_config
    rm -f GW-VoIP-Setup*.tgz
    tar -zcvf GW-VoIP-Setup-{{my_version}}.tgz \
       place_call.py modem_utils.py send_EDC_info.py \
       manage_modem.py manage_modem.service modem_manager_client.py \
       daemon.conf pulseaudio.service K3_config_settings \
       99-ignore-modemmanager.rules CHANGELOG.md \
       get_sensor_data.py get_sensor_data.service get_sensor_data.timer \
       -C VOIP \
       voip_call_monitor_tcp.py voip_call_monitor.service \
       voip_config.sh voip_ari_conference.service interfaces \
       -C baresip \
       accounts config \
       -C ../asterisk \
       pjsip.conf extensions.conf ari.conf http.conf confbridge.conf \
       ari-mon-conf.py modules.conf \
       -C ../pulseaudio default.pa

vpkgpush: pkgvoip
    scp GW-VoIP-Setup*.tgz {{nuser}}@{{target}}:/mnt/data/.

my_save_path := "/mnt/c/Users/AlanHasty/Exponential Technology Group, Inc/C_KingsIII-QSeries - Documents/sw"

pdf:
    docker run --rm --volume "$(pwd):/data" --user $(id -u):$(id -g) pandoc/latex CHANGELOG.md -o CHANGELOG.{{my_version}}.pdf
    docker run --rm --volume "$(pwd):/data" --user $(id -u):$(id -g) pandoc/latex GateworkVOIPProgramming.md -o GateworkVOIPProgramming.{{my_version}}.pdf


save: pkgvoip pdf
    mkdir "{{my_save_path}}/{{my_version}}"
    zip GW-VoIP-Pkg-{{my_version}}.zip GW-VoIP-Setup-{{my_version}}.tgz CHANGELOG.{{my_version}}.pdf GateworkVOIPProgramming.{{my_version}}.pdf
    cp GW-VoIP-Setup-{{my_version}}.tgz "{{my_save_path}}/{{my_version}}/."
    cp CHANGELOG.{{my_version}}.pdf "{{my_save_path}}/{{my_version}}/."
    cp GateworkVOIPProgramming.{{my_version}}.pdf "{{my_save_path}}/{{my_version}}/."
    cp GW-VoIP-Pkg-{{my_version}}.zip "{{my_save_path}}/{{my_version}}/."

ans:
    scp answer_phone.py {{nuser}}@{{target}}:/mnt/data/answer_phone.py

menu:
    scp CONF_ADDING/confbridge.conf {{nuser}}@{{target}}:/mnt/data/addExten/confbridge.conf
    scp CONF_ADDING/extensions.conf {{nuser}}@{{target}}:/mnt/data/addExten/extensions.conf
