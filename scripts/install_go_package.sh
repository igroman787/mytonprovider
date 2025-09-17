#!/bin/bash
set -e

# Check superuser
if [ "$(id -u)" != "0" ]; then
	echo "Please run script as root"
	exit 1
fi

# Colors
COLOR='\033[95m'
ENDC='\033[0m'

# functions
show_help_and_exit() {
	echo 'Supported arguments:'
	echo ' -a               Set git author'
	echo ' -r               Set git repo'
	echo ' -b               Set git branch'
	echo ' -e               Set entry point for compilation'
	echo ' -s               Service name for restart'
	echo ' -h               Show this help'
	exit
}

# Show help for --help
if [[ "${1-}" =~ ^-*h(elp)?$ ]]; then
	show_help_and_exit
fi

# Input args
while getopts "a:r:b:e:s:h" flag; do
	case "${flag}" in
		a) author=${OPTARG};;
		r) repo=${OPTARG};;
		b) branch=${OPTARG};;
		e) entry_point=${OPTARG};;
		s) service_name=${OPTARG};;
		h) show_help_and_exit;;
		*)
			echo "Flag -${flag} is not recognized. Aborting"
		exit 1 ;;
	esac
done

# Install parameters
src_dir="/usr/src"
bin_dir="/usr/bin"
src_path="${src_dir}/${repo}"
bin_path="${bin_dir}/${repo}"
go_path="/usr/local/go/bin/go"

# functions
check_go_version() {
	go_mod_path=${1}
	go_path=${2}
	if [ ! -f ${go_path} ]; then
		install_go
		return
	fi

	go_mod_text=$(cat ${go_mod_path}) || exit 1
	need_version_text=$(echo "${go_mod_text}" | grep "go " | head -n 1 | awk '{print $2}')
	current_version_text=$(${go_path} version | awk '{print $3}' | sed 's\go\\g')
	echo "start check_go_version function"
	echo "need_version: ${need_version_text}, current_version: ${current_version_text}"
	current_version_1=$(echo ${current_version_text} | cut -d "." -f 1)
	current_version_2=$(echo ${current_version_text} | cut -d "." -f 2)
	current_version_3=$(echo ${current_version_text} | cut -d "." -f 3)
	need_version_1=$(echo ${need_version_text} | cut -d "." -f 1)
	need_version_2=$(echo ${need_version_text} | cut -d "." -f 2)
	need_version_3=$(echo ${need_version_text} | cut -d "." -f 3)
	if (( current_version_1 > need_version_1 )); then
		return
	elif (( current_version_2 > need_version_2 )); then
		return
	elif (( current_version_3 >= need_version_3 )); then
		return
	else
		install_go
	fi
}

install_go() {
	echo "start install_go function"
	arc=$(dpkg --print-architecture)
	go_version_url="https://go.dev/VERSION?m=text"
	go_version=$(curl -s ${go_version_url} | head -n 1)
	go_url=https://go.dev/dl/${go_version}.linux-${arc}.tar.gz
	rm -rf /usr/local/go
	wget -c ${go_url} -O - | tar -C /usr/local -xz
}

clone_repository() {
	echo "https://github.com/${author}/${repo}.git -> ${branch}"
	rm -rf ${src_path}_tmp
	git clone --branch ${branch} --recursive https://github.com/${author}/${repo}.git ${src_path}_tmp
	rm -rf ${src_path}
	mv ${src_path}_tmp ${src_path}
}

install_required() {
	check_go_version "${src_path}/go.mod" ${go_path}
}

compilation() {
	echo "${src_path} -> ${bin_path}"
	cd ${src_path}
	#entry_point=$(find ${package_src_path} -name "main.go" | head -n 1)
	CGO_ENABLED=1 ${go_path} build -o ${bin_path} ${src_path}/${entry_point}
}

service_restart() {
	if [ -n "${service_name}" ]; then
		systemctl restart ${service_name}
	fi
}

setup_go_package(){
	echo -e "${COLOR}[1/4]${ENDC} Cloning ${repo} repository"
	clone_repository

	echo -e "${COLOR}[2/4]${ENDC} Installing required packages"
	install_required

	echo -e "${COLOR}[3/4]${ENDC} Source compilation"
	compilation
	service_restart

	echo -e "${COLOR}[4/4]${ENDC} ${repo} installation complete"
}

setup_go_package
exit 0
