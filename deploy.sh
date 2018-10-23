#!/bin/bash


if [ "$EUID" -ne 0 ]
then echo "Please run this as root."
     exit
fi


# Set the name for this prongle
NAMEFILE=/boot/prongle_name
if [[ -r $NAMEFILE ]]
then
    NAME=`head -n 1 $NAMEFILE`

else
    echo -n "Identifier for this prongle: "
    read NAME
fi

echo "PRETTY_HOSTNAME=$NAME" > /etc/machine-info



exit

# Install required packages
DEPENDS=("tcpdump" "bluetooth" "bluez" "python-bluez" "python-scapy" "bluez-test-scripts")
apt-get install `echo "${DEPENDS[*]}"`

# Remove unnecessary and unfavourable packages
REMOVES=("wpasupplicant")
apt-get remove --purge `echo "${REMOVES[*]}"`



# Make bluetoothd start with --compat
### FIXTHIS: needs escape
# sed -i .bak 's/ExecStart=/usr/lib/bluetooth/bluetoothd/ExecStart=/usr/lib/bluetooth/bluetoothd --compat/' /etc/systemd/system/dbus-org.bluez.service

systemctl daemon-reload
systemctl restart bluetooth

# Bluetooth pairing
hciconfig hci0 piscan
### FIXTHIS: simple-agent from bluez testscripts
