#!/usr/bin/env python3
# -*- coding: utf_8 -*-

import os
import base64
from random import randint

import requests
from rich.text import Text

from mypylib import (
	Dict,
	add2systemd,
	read_config_from_file,
	write_config_to_file,
	get_own_ip,
	get_git_hash,
	get_git_branch,
	get_service_status,
	get_service_uptime,
	time2human,
	check_git_update,
	get_git_author_and_repo,
)

from utils import (
	get_module_by_name,
	fix_git_config,
	get_service_status_color,
	get_check_port_status,
	set_check_data,
	get_check_update_status,
	run_subprocess,
	validate_github_repo,
	print_panel,
)
from decorators import publick
from addr_and_key import get_pubkey_from_privkey
from adnl_over_udp_checker import check_adnl_connection
from server_info import get_ram_info


class Module():
	def __init__(self, local):
		self.name = "dht-server"
		self.service_name = self.name
		self.local = local
		self.mandatory = False
		self.depends_on = ["main"]
		self.local.add_log(f"{self.name} module init done", "debug")

		self.go_package = Dict()
		self.go_package.author = "xssnick"
		self.go_package.repo = "dht-server"
		self.go_package.branch = "master"
		self.go_package.entry_point = "cmd/dht-server/main.go"
	#end define

	@publick
	def is_enabled(self):
		git_path = self.get_my_git_path()
		try:
			get_git_branch(git_path)
			return True
		except:
			return False
	#end define

	@publick
	def pre_up(self):
		self.local.start_thread(self.check_update)
		self.local.start_thread(self.check_port)
	#end define

	def check_update(self):
		git_path = self.get_my_git_path()
		is_update_available = check_git_update(git_path)
		set_check_data(module=self, check_name="update", data=is_update_available)
	#end define

	def check_port(self):
		dht_server_config = self.get_dht_server_config()
		server_pubkey = self.get_server_pubkey()
		public_ip, server_port = dht_server_config.public_addr.split(':')
		own_ip = get_own_ip()
		if public_ip != own_ip:
			raise Exception("dht_server_config.public_addr != own_ip")
		result, status = check_adnl_connection(own_ip, server_port, server_pubkey)
		set_check_data(module=self, check_name="port", data=result)
	#end define

	def get_dht_server_config(self):
		dht_server = self.local.db.dht_server
		dht_server_config = read_config_from_file(dht_server.config_path)
		return dht_server_config
	#end define

	def get_server_pubkey(self):
		dht_server_config = self.get_dht_server_config()
		private_key_bytes = base64.b64decode(dht_server_config.private_key_seed)
		server_pubkey = get_pubkey_from_privkey(private_key_bytes).hex().upper()
		return server_pubkey
	#end define

	def get_metrics_data(self):
		dht_server_config = self.get_dht_server_config()
		metrics_url = f"http://{dht_server_config.metrics.listen_addr}/metrics"
		resp = requests.get(metrics_url, timeout=3)
		if resp.status_code != 200:
			raise Exception(f"Failed to get dht-server metrics from {metrics_url}")
		return resp.text
	#end define

	def get_metric(self, metrics_data, metric_name):
		for line in metrics_data.splitlines():
			if line.startswith(metric_name + " "):
				return int(float(line.split()[1]))
		return "N/A"
	#end define

	@publick
	def status(self, args):
		metrics_data = self.get_metrics_data()
		body = [
			self.print_stored_keys(metrics_data),
			self.print_active_peers(metrics_data),
			self.print_port_status(),
			self.print_git_hash(),
		]
		header = self.print_module_name()
		footer = self.print_service_status()
		print_panel(body, header, footer)
	#end define

	def print_module_name(self):
		return Text(self.name, style="cyan")
	#end define

	def print_stored_keys(self, metrics_data):
		dht_server_config = self.get_dht_server_config()
		stored_keys = self.get_metric(metrics_data, "dht_server_stored_values")
		stored_keys_text = Text(str(stored_keys), style="green")
		max_keys_text = Text(str(dht_server_config.max_keys), style="yellow")
		field = self.local.translate("dht_server_stored_keys")
		value = Text.assemble(stored_keys_text, " / ", max_keys_text)
		return field, value
	#end define

	def print_active_peers(self, metrics_data):
		active_peers = self.get_metric(metrics_data, "dht_server_active_peers")
		field = self.local.translate("dht_server_active_peers")
		value = Text(str(active_peers), style="green")
		return field, value
	#end define

	def print_port_status(self):
		dht_server_config = self.get_dht_server_config()
		public_ip, server_port = dht_server_config.public_addr.split(':')
		port_color = Text(f"{server_port} udp", style="yellow")
		status = get_check_port_status(module=self)
		field = self.local.translate("port_status")
		value = Text.assemble(port_color, ", ", status)
		return field, value
	#end define

	def print_service_status(self):
		service_status = get_service_status(self.service_name)
		service_uptime = get_service_uptime(self.service_name)
		service_status_color = get_service_status_color(service_status)
		service_uptime_color = Text(time2human(service_uptime), style="green")
		return Text.assemble(service_status_color, ", ", service_uptime_color)
	#end define

	def print_git_hash(self):
		git_hash, git_branch = self.get_my_git_hash_and_branch()
		git_hash_text = Text(git_hash, style="yellow")
		git_branch_text = Text(f"({git_branch})", style="yellow")
		update_status = get_check_update_status(module=self)
		field = self.local.translate("git_hash")
		parts = [git_hash_text, " ", git_branch_text]
		if update_status:
			parts.append(", ")
			parts.append(update_status)
		value = Text.assemble(*parts)
		return field, value
	#end define

	def get_my_git_hash_and_branch(self):
		git_path = self.get_my_git_path()
		git_hash = get_git_hash(git_path, short=True)
		git_branch = get_git_branch(git_path)
		return git_hash, git_branch
	#end define

	def get_my_git_path(self):
		git_path = f"/usr/src/{self.go_package.repo}"
		fix_git_config(git_path)
		return git_path
	#end define

	@publick
	def get_update_args(self, user=None, author=None, repo=None, branch=None, restart_service=False, **kwargs):
		try:
			git_path = self.get_my_git_path()
			curr_branch = get_git_branch(git_path)
			curr_author, curr_repo = get_git_author_and_repo(git_path)
		except Exception:
			curr_author = curr_repo = curr_branch = None
		#end try

		author = author or curr_author or self.go_package.author
		repo = repo or curr_repo or self.go_package.repo
		branch = branch or curr_branch or self.go_package.branch
		validate_github_repo(author, repo, branch)

		script_path = f"{self.local.buffer.my_dir}/scripts/install_go_package.sh"
		update_args = [
			"bash", script_path,
			"-a", author,
			"-r", repo,
			"-b", branch,
			"-e", self.go_package.entry_point
		]
		if restart_service == True:
			update_args += ["-s", self.service_name]
		return update_args
	#end define

	def install(self, install_args, install_answers):
		if install_answers.storage_path == None:
			raise Exception("install error: storage_path is not set")
		#end if

		metrics_host = "127.0.0.1"
		udp_port = randint(1024, 65000)
		metrics_port = randint(1024, 65000)

		mconfig_dir = f"/home/{install_args.user}/.local/share/mytonprovider"
		mconfig_path = f"{mconfig_dir}/mytonprovider.db"
		dht_server_path = f"{install_answers.storage_path}/dht-server"
		dht_server_db_path = f"{dht_server_path}/db"
		dht_server_config_path = f"{dht_server_path}/config.json"

		# Склонировать исходники и скомпилировать бинарники
		upgrade_args = self.get_update_args(install_args.src_path)
		run_subprocess(upgrade_args, timeout=2 * 60)

		# Подготовить папку
		os.makedirs(dht_server_path, exist_ok=True)

		# Создать службу
		start_cmd = f"{install_args.bin_dir}/{self.go_package.repo} --config {dht_server_config_path}"
		add2systemd(name=self.service_name, user=install_args.user, start=start_cmd, workdir=dht_server_path, force=True)

		# Первый запуск - создание конфига
		if not os.path.exists(dht_server_config_path):
			run_subprocess([f"{install_args.bin_dir}/{self.go_package.repo}", "--config", dht_server_config_path], timeout=30)

		# read dht server config
		dht_server_config = read_config_from_file(dht_server_config_path)

		main_module = get_module_by_name(self.local, "main")

		# edit dht server config
		public_ip = get_own_ip()
		ram_gigabytes = round(get_ram_info().total *10**9 /1024**3)

		dht_server_config.listen_addr = f"0.0.0.0:{udp_port}"
		dht_server_config.public_addr = f"{public_ip}:{udp_port}"
		dht_server_config.global_config_path = main_module.global_config_path
		dht_server_config.max_keys = max(100000, ram_gigabytes *100000)
		dht_server_config.storage.path = dht_server_db_path

		dht_server_config.metrics.enabled = True
		dht_server_config.metrics.listen_addr = f"{metrics_host}:{metrics_port}"

		# write dht server config
		write_config_to_file(config_path=dht_server_config_path, data=dht_server_config)

		# read mconfig
		mconfig = read_config_from_file(mconfig_path)

		# edit mconfig config
		dht_server = Dict()
		dht_server.config_path = dht_server_config_path
		dht_server.src_dir = install_args.src_dir
		mconfig.dht_server = dht_server

		# write mconfig
		write_config_to_file(config_path=mconfig_path, data=mconfig)

		chown_args = [
			"chown",
			"-R",
			install_args.user + ':' + install_args.user,
			dht_server_path
		]
		run_subprocess(chown_args, timeout=3)

		# start service
		self.local.start_service(self.service_name)
	#end define
#end class
