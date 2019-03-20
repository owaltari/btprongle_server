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


# Install required packages
apt-get update
DEPENDS=("git" "gawk" "tcpdump" "bluetooth" "bluez" "python-bluez" "python-scapy" "bluez-test-scripts")
apt-get install -y `echo "${DEPENDS[*]}"`

# Remove unnecessary and unfavourable packages
REMOVES=("wpasupplicant")
apt-get remove -y --purge `echo "${REMOVES[*]}"`



# Make bluetoothd start with --compat
### FIXTHIS: needs escape
sed --in-place=.bak 's/\/bluetoothd$/\/bluetoothd --compat/' /etc/systemd/system/dbus-org.bluez.service


systemctl daemon-reload
systemctl restart bluetooth

# Add serial port profile for Bluetooth
sdptool add SP

# Bluetooth pairing
hciconfig hci0 piscan
### FIXTHIS: simple-agent from bluez testscripts
