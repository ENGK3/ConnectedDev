cp /mnt/data/extensions.conf /etc/asterisk/extensions.conf
cp /mnt/data/confbridge.conf /etc/asterisk/confbridge.conf
cp /mnt/data/pjsip.conf /etc/asterisk/pjsip.conf
chown asterisk:asterisk /etc/asterisk/extensions.conf /etc/asterisk/confbridge.conf \
     /etc/asterisk/pjsip.conf

cp /mnt/data/accounts /home/kuser/.baresip/accounts
cp /mnt/data/baresip.config /home/kuser/.baresip/config
chown kuser:kuser /home/kuser/.baresip/config /home/kuser/.baresip/accounts
