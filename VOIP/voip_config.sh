cp /mnt/data/extensions.conf /etc/asterisk/extensions.conf
cp /mnt/data/confbridge.conf /etc/asterisk/confbridge.conf
cp /mnt/data/pjsip.conf /etc/asterisk/pjsip.conf
cp /mnt/data/modules.conf /etc/asterisk/modules.conf
cp /mnt/data/ari.conf /etc/asterisk/ari.conf
cp /mnt/data/http.conf /etc/asterisk/http.conf
chown asterisk:asterisk /etc/asterisk/extensions.conf  \
     /etc/asterisk/pjsip.conf /etc/asterisk/modules.conf \
     /etc/asterisk/confbridge.conf /etc/asterisk/ari.conf \
     /etc/asterisk/http.conf


# Create call log file and change ownership.
touch /mnt/data/calls.log
chown kuser:kuser /mnt/data/calls.log

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


# Start the service that monitors the Ext 200 VOIP line for calls.
cp /mnt/data/voip_call_monitor.service /etc/systemd/system/.
systemctl daemon-reload
systemctl enable voip_call_monitor.service
systemctl start voip_call_monitor.service


# Start the service that monitors the connections to the 'elevator_conference' ARI
# conference bridge.
cp /mnt/data/voip_ari_conference.service /etc/systemd/system/.
systemctl daemon-reload
systemctl enable voip_ari_conference.service
systemctl start voip_ari_conference.service


cp /mnt/data/manage_modem.service /etc/systemd/system/.
systemctl daemon-reload
systemctl enable manage_modem.service
systemctl start manage_modem.service

cp get_sensor_data.service get_sensor_data.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable get_sensor_data.timer
systemctl start get_sensor_data.timer

#systemctl status get_sensor_data.timer
#systemctl list-timers get_sensor_data.timer