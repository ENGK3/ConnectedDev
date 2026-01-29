
target := "172.20.10.223"   # Gateworks Target
#target := "172.27.17.43"

#nuser := "root"
nuser := "kuser"


# Generate version information from Git
version:
    ./generate_version.sh

# Show version information
show-version:
    ./show_version.sh

my_version := `grep '^VERSION=' VERSION_INFO | cut -d= -f2`

k3_config:
    cat K3_config_settings.in > K3_config_settings.default
    echo 'APP="{{my_version}}"' >> K3_config_settings.default

part-pkg: k3_config
    rm -f GW-Setup*.t*
    tar -cvf GW-Setup-{{my_version}}.tar \
       place_call.py check_reg.py modem_utils.py send_EDC_info.py \
       manage_modem.py manage_modem.service modem_manager_client.py \
       daemon.conf pulseaudio.service K3_config_settings.default modem_state.py \
       99-ignore-modemmanager.rules CHANGELOG.md \
       get_sensor_data.py get_sensor_data.service get_sensor_data.timer \
       sstat.sh stop_ss.sh start_ss.sh switch_detect.sh \
       set-governor.service kings3_install.sh switch_mon.service switch_mon.sh \
       sounds/* *.dtbo microcom.alias daemon.conf  dtmf_collector.py \
       led_blue.sh led_green.sh led_red.sh audio_routing.py update_uid.sh \
       events_monitor.py events_monitor.service update_from_SD_card.py \
       VERSION_INFO programming \
       -C VOIP \
       voip_call_monitor_tcp.py voip_call_monitor.service ep.sh \
       voip_ari_conference.service interfaces \
       -C baresip \
       accounts config \
       -C ../asterisk \
       pjsip.conf extensions.conf ari.conf http.conf confbridge.conf \
       ari-mon-conf.py modules.conf \
       -C ../pulseaudio default.pa \
       -C ../../common \
       site_store.py site.pub site_info edit_config.sh \
       RSRP_LUT.csv RSRQ_LUT.csv RSSI_LUT.csv \
       dial_code_utils.py



pkg: part-pkg
    rm -rf cksum_dir
    mkdir -p cksum_dir
    cd cksum_dir; tar -xf ../GW-Setup-{{my_version}}.tar; \
    find . -type f | sed 's|^\./||' |  xargs md5sum > GW-Setup-{{my_version}}.md5; \
    tar -zcf ../GW-Setup-{{my_version}}.tgz *
    rm -rf GW-Setup-{{my_version}}.tar cksum_dir

pkgpush: pkg
    scp GW-Setup*.tgz {{nuser}}@{{target}}:/mnt/data/.

my_save_path := "/mnt/c/Users/AlanHasty/Exponential Technology Group, Inc/C_KingsIII-QSeries - Documents/sw"

pdf:
    just pdf-styled CHANGELOG.md
    just pdf-styled GateworksVOIPProgramming.md
    just pdf-styled GateworksPoolProgrammingInst.md

# Convert Markdown to PDF using HTML/CSS (like VS Code extension)
pdf-html FILE:
    docker run --rm --volume "$(pwd):/data" --user $(id -u):$(id -g) pandoc/latex:latest {{FILE}} -o {{FILE}}.html --css=markdown-pdf.css --standalone
    @echo "HTML generated. Install wkhtmltopdf locally to convert: wkhtmltopdf {{FILE}}.html {{FILE}}.pdf"

# Convert single file with version number using HTML/CSS
pdf-styled FILE:
    docker run --rm --volume "$(pwd):/data" --user $(id -u):$(id -g) pandoc/latex:latest {{FILE}} -o {{replace_regex(FILE, '\.md$', '')}}.{{my_version}}.pdf --standalone -V geometry:margin=0.5in

release: pkg pdf
    zip GW-Pkg-{{my_version}}.zip GW-Setup-{{my_version}}.tgz \
    CHANGELOG.{{my_version}}.pdf GateworksVOIPProgramming.{{my_version}}.pdf \
    GateworksPoolProgrammingInst.{{my_version}}.pdf

save: release
    mkdir "{{my_save_path}}/{{my_version}}"
    cp GW-Setup-{{my_version}}.tgz "{{my_save_path}}/{{my_version}}/."
    cp CHANGELOG.{{my_version}}.pdf "{{my_save_path}}/{{my_version}}/."
    cp GateworksVOIPProgramming.{{my_version}}.pdf "{{my_save_path}}/{{my_version}}/."
    cp GateworksPoolProgrammingInst.{{my_version}}.pdf "{{my_save_path}}/{{my_version}}/."
    cp GW-Pkg-{{my_version}}.zip "{{my_save_path}}/{{my_version}}/."


clean:
     rm -rf *.pdf *.zip *.tgz cksum_dir GW-Setup-*.tar ./modem_test.log \
       ./edc_test.log ./tests/pytest.log
