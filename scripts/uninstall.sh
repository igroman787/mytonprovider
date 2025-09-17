#!/bin/bash
set -e


# colors
COLOR='\033[92m'
ENDC='\033[0m'


rm -rf /var/storage

rm -rf /usr/src/tonutils-storage
rm -rf /usr/src/tonutils-storage-provider
rm -rf /usr/src/adnl-tunnel

rm -rf /usr/bin/tonutils-storage
rm -rf /usr/bin/tonutils-storage-provider
rm -rf /usr/bin/adnl-tunnel

rm -rf /etc/systemd/system/mytonproviderd.service
rm -rf /etc/systemd/system/mytonprovider-updater.service
rm -rf /etc/systemd/system/ton-storage.service
rm -rf /etc/systemd/system/ton-storage-provider.service
rm -rf /etc/systemd/system/ton-tunnel-provider.service

systemctl daemon-reload

exit 0
