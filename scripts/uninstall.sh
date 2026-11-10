#!/bin/bash
set -e


# colors
COLOR='\033[92m'
ENDC='\033[0m'

systemctl stop mytonproviderd
systemctl stop ton-storage
systemctl stop ton-storage-provider
systemctl stop dht-server
systemctl stop adnl-tunnel

rm -rf /var/storage

rm -rf /usr/src/tonutils-storage
rm -rf /usr/src/tonutils-storage-provider
rm -rf /usr/src/dht-server
rm -rf /usr/src/adnl-tunnel

rm -rf /usr/bin/tonutils-storage
rm -rf /usr/bin/tonutils-storage-provider
rm -rf /usr/bin/dht-server
rm -rf /usr/bin/adnl-tunnel

rm -rf /etc/systemd/system/mytonproviderd.service
rm -rf /etc/systemd/system/mytonprovider-updater.service
rm -rf /etc/systemd/system/ton-storage.service
rm -rf /etc/systemd/system/ton-storage-provider.service
rm -rf /etc/systemd/system/dht-server.service
rm -rf /etc/systemd/system/ton-tunnel-provider.service

systemctl daemon-reload

exit 0
