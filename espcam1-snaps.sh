#!/bin/sh

url="http://espcam1/snapshot.jpg"
mkdir -p snapshots

while true; do
    mosquitto_pub -t 'cmnd/espcam1/power' -m 1
    sleep 5
    fname="snapshots/snapshot-espcam1-`date +%y%m%d_%H%M%S`.jpg"
    wget -q -O "$fname" "$url"
    mosquitto_pub -t 'cmnd/espcam1/power' -m 0
    sleep 300
done
