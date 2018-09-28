#!/bin/bash

# Adapter to monitor mode
iw phy `iw dev wlan0 info | gawk '/wiphy/ {printf "phy" $2}'` interface add mon0 type monitor

ifconfig wlan0 down
ifconfig mon0 up
sleep 1
iwconfig mon0 channel 11

python /home/pi/btprongle_server/btprongle_server.py &

