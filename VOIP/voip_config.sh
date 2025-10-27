cp /mnt/data/extensions.conf /etc/asterisk/extensions.conf
#cp /mnt/data/confbridge.conf /etc/asterisk/confbridge.conf
cp /mnt/data/pjsip.conf /etc/asterisk/pjsip.conf
chown asterisk:asterisk /etc/asterisk/extensions.conf  \
     /etc/asterisk/pjsip.conf
# /etc/asterisk/confbridge.conf

# Baresip setup
mkdir -p /home/kuser/.baresip


cp /mnt/data/accounts /home/kuser/.baresip/accounts
cp /mnt/data/config /home/kuser/.baresip/config
chown -R kuser:kuser /home/kuser/.baresip

# Network interfaces setup
cp /mnt/data/interfaces /etc/network/interfaces

# PulseAudio setup
cp /mnt/data/default.pa /etc/pulse/default.pa
cp /mnt/data/daemon.conf /etc/pulse/daemon.conf

mkdir -p /home/kuser/.config/systemd/user
cp /mnt/data/pulseaudio.service /home/kuser/.config/systemd/user/pulseaudio.service
# Everything under kuser needs to be owned by kuser.
# IF not when doing the "systemctl --user enable pulseaudio.service" it will fail.
chown -R kuser:kuser /home/kuser/.config


# Turn off the modem manager attempting to manage the cellular modem.
cp /mnt/data/99-ignore-modemmanager.rules  /etc/udev/rules.d/99-ignore-modemmanager.rules


cp /mnt/data/voip_call_monitor.service /etc/systemd/system/.
systemctl daemon-reload
systemctl enable voip_call_monitor.service
systemctl start voip_call_monitor.service
