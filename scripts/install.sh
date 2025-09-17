#!/bin/bash
set -e

# Set default arguments
author="igroman787"
repo="mytonprovider"
branch="master"
ignore=false

# Colors
COLOR='\033[92m'
ENDC='\033[0m'

modules=""
storage_path=""
storage_cost=""
space_to_provide=""

# functions
show_help_and_exit() {
	echo 'Supported arguments:'
	echo ' -u  USER         Specify the user to be used for MyTonProvider installation'
	echo ' -a               Set MyTonProvider git repo author'
	echo ' -r               Set MyTonProvider git repo'
	echo ' -b               Set MyTonProvider git repo branch'
	echo ' -m               Comma-separated modules list'
	echo ' -p               Storage path'
	echo ' -c               Storage cost per GB'
	echo ' -s               Space to provide in GB'
	echo ' -i               Ignore non-root user checking'
	echo ' -h               Show this help'
	exit
}

restart_yourself_via_root() {
  if [[ -n "${input_user}" ]]; then
    return
  fi

  user=$(whoami)
  user_id=$(id -u)
  user_groups=$(groups "${user}")

  if [[ ${user_id} == 0 ]] && [[ ${ignore} == false ]]; then
    echo "Please run script as non-root user. You can create a new non-root user with command 'sudo adduser'. Or use flag '-i' to ignore this check."
    exit 1
  fi

  cmd=(bash "$0" -u "$user" "$@")
  if [[ ${user_groups} == *"sudo"* ]]; then
    sudo "${cmd[@]}"
    exit
  else
    su root -c "${cmd[*]}"
    exit
  fi
}

# Show help for --help
if [[ "${1-}" =~ ^-*h(elp)?$ ]]; then
	show_help_and_exit
fi

# Input args
while getopts "u:a:r:b:m:p:c:s:ih" flag; do
	case "${flag}" in
		u) input_user=${OPTARG};;
		a) author=${OPTARG};;
		r) repo=${OPTARG};;
		b) branch=${OPTARG};;
		m) modules=${OPTARG};;
		p) storage_path=${OPTARG};;
		c) storage_cost=${OPTARG};;
		s) space_to_provide=${OPTARG};;
		i) ignore=true;;
		h) show_help_and_exit;;
		*) echo "Flag -${flag} is not recognized. Aborting"; exit 1 ;;
	esac
done

# Reboot yourself via root to continue the installation
restart_yourself_via_root "$@"

# Continue the installation
user=${input_user}
echo "Using user: ${user}"

# Install parameters
src_dir="/usr/src"
bin_dir="/usr/bin"
venvs_dir="/home/${user}/.local/venv"
venv_path="${venvs_dir}/${repo}"
src_path="${src_dir}/${repo}"


preparation_for_cloning() {
	apt update
	apt install -y git
}

clone_repository() {
	echo "https://github.com/${author}/${repo}.git -> ${branch}"
	rm -rf ${src_path}
	git clone --branch ${branch} --recursive https://github.com/${author}/${repo}.git ${src_path}
	git config --global --add safe.directory ${src_path}
}

install_apt_dependencies() {
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

launch_installer() {
	cmd="python3 ${src_path}/install.py --user ${user} --src_dir ${src_dir} --bin_dir ${bin_dir} --venvs_dir ${venvs_dir} --venv_path ${venv_path} --src_path ${src_path}"

	if [[ -n "${modules}" ]]; then
		cmd="${cmd} --utils ${modules}"
	fi
	if [[ -n "${storage_path}" ]]; then
		cmd="${cmd} --storage_path ${storage_path}"
	fi
	if [[ -n "${storage_cost}" ]]; then
		cmd="${cmd} --storage_cost ${storage_cost}"
	fi
	if [[ -n "${space_to_provide}" ]]; then
		cmd="${cmd} --space_to_provide_gigabytes ${space_to_provide}"
	fi

	eval ${cmd}
}

mytonprovider_setup() {
	echo -e "${COLOR}[1/6]${ENDC} Cloning MyTonProvider repository"
	preparation_for_cloning
	clone_repository

	echo -e "${COLOR}[2/6]${ENDC} Installing required packages"
	install_apt_dependencies

	echo -e "${COLOR}[3/6]${ENDC} Activating virtual environment"
	activate_venv

	echo -e "${COLOR}[4/6]${ENDC} Installing requirements"
	install_pip_dependencies

	echo -e "${COLOR}[5/6]${ENDC} Launching installer"
	launch_installer

	echo -e "${COLOR}[6/6]${ENDC} MyTonProvider installation completed"
}

mytonprovider_setup
exit 0
