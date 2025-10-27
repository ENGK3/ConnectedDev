cp /mnt/data/99-ignore-modemmanager.rules  /etc/udev/rules.d/99-ignore-modemmanager.rules
cp /mnt/data/switch_mon.service /etc/systemd/system/switch_mon.service

cp /mnt/data/pulse/daemon.conf /etc/pulse/daemon.conf

mkdir -p /home/kuser/.config/systemd/user
cp /mnt/data/pulse/pulseaudio.service /home/kuser/.config/systemd/user/pulseaudio.service
# Everything under kuser needs to be owned by kuser.
# IF not when doing the "systemctl --user enable pulseaudio.service" it will fail.
chown -R kuser:kuser /home/kuser/.config

touch /mnt/data/calls.log
chmod ugo+w /mnt/data/calls.log

loginctl enable-linger kuser

systemctl daemon-reload
systemctl enable switch_mon.service

# This must be done a kuser.
#systemctl --user enable pulseaudio.service
