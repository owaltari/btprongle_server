#!/bin/bash

# Adapter to monitor mode
iw phy `iw dev wlan0 info | gawk '/wiphy/ {printf "phy" $2}'` interface add mon0 type monitor
iw phy `iw dev wlan0 info | gawk '/wiphy/ {printf "phy" $2}'` interface add mon1 type monitor

ifconfig wlan0 down
ifconfig mon0 up
ifconfig mon1 up
sleep 1
iwconfig mon0 channel 1
iwconfig mon1 channel 1

#python /home/pi/btprongle_server/btprongle_server.py &

screen -dmS btprongle
screen -S btprongle -X stuff 'python /home/pi/btprongle_server/btprongle_server.py\nbash\n'
