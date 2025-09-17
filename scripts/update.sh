#!/bin/bash
set -e

# Check superuser
if [ "$(id -u)" != "0" ]; then
	echo "Please run script as root"
	exit 1
fi

# Input args
while getopts "u:d:" flag; do
	case "${flag}" in
		u) user=${OPTARG};;
		d) venvs_dir=${OPTARG};;
	esac
done

# Colors
COLOR='\033[95m'
ENDC='\033[0m'

# Set default arguments
author="igroman787"
repo="mytonprovider"
branch="master"

# Install parameters
src_dir="/usr/src"
bin_dir="/usr/bin"
venv_path="${venvs_dir}/${repo}"
src_path="${src_dir}/${repo}"

clone_repository() {
	echo "https://github.com/${author}/${repo}.git -> ${branch}"
	rm -rf ${src_path}_tmp
	git clone --branch ${branch} --recursive https://github.com/${author}/${repo}.git ${src_path}_tmp
	rm -rf ${src_path}
	mv ${src_path}_tmp ${src_path}
}

install_apt_dependencies() {
	apt update
	apt install -y $(cat ${src_path}/resources/pkglist.txt)
}

activate_venv() {
	virtualenv ${venv_path}
	source ${venv_path}/bin/activate
}

install_pip_dependencies() {
	pip3 install -r ${src_path}/resources/requirements.txt
	pip3 install -r ${src_path}/mypylib/requirements.txt
}

download_global_config() {
	mkdir -p /var/ton
	wget https://igroman787.github.io/global.config.json -O /var/ton/global.config.json
	chown ${user}:${user} /var/ton/global.config.json
}

service_restart() {
	systemctl restart mytonproviderd
}


# Start update
clone_repository
install_apt_dependencies
activate_venv
install_pip_dependencies
download_global_config
service_restart
exit 0
