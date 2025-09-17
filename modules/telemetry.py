#!/usr/bin/env python3
# -*- coding: utf_8 -*-

import gzip
import json
import psutil
import hashlib
import requests
from getpass import getpass
from base64 import b64encode
from mypylib import (
	Dict,
	get_load_avg,
	read_config_from_file,
	write_config_to_file,
	get_timestamp,
	get_service_uptime
)
from decorators import publick
from utils import get_module_by_name, get_disk_space
from server_info import (
	get_cpu_name,
	get_product_name,
	is_product_virtual,
	do_beacon_ping,
	get_pings_values,
	get_storage_disk_name,
	get_uname,
	get_ram_info,
	get_swap_info
)


class Module():
	def __init__(self, local):
		self.name = "telemetry"
		self.local = local
		self.mandatory = False
		self.daemon_interval = 60
		self.telemetry_url = "https://mytonprovider.org/api/v1/providers"
		self.benchmark_url = "https://mytonprovider.org/api/v1/benchmarks"
		self.send_benchmark_interval = 86400 # 24 hours
		self.send_benchmark_time = 0
		self.local.add_log(f"{self.name} module init done", "debug")
	#end define

	@publick
	def get_console_commands(self):
		commands = list()
		telemetry_pass = Dict()
		telemetry_pass.cmd = "telemetry_pass"
		telemetry_pass.func = self.set_telemetry_pass
		telemetry_pass.desc = self.local.translate("telemetry_pass_cmd")
		commands.append(telemetry_pass)
		return commands
	#end define

	def set_telemetry_pass(self, args):
		passwd = getpass("Set a new password for the telemetry data: ")
		repasswd = getpass("Repeat password: ")
		if passwd != repasswd:
			print("Error: Password mismatch")
			return
		self.local.db.telemetry_pass = self.generate_password_hash(passwd)
	#end define

	def generate_password_hash(self, passwd):
		if type(passwd) != str:
			raise Exception("generate_password_hash error: passwd type not str")
		#end if

		data = self.telemetry_url + passwd
		data_bytes = data.encode("utf-8")
		hasher = hashlib.sha256(data_bytes)
		hash_bytes = hasher.digest()
		hash_b64 = b64encode(hash_bytes)
		result = hash_b64.decode("utf-8")
		return result
	#end define

	@publick
	def daemon(self):
		send_telemetry = self.local.db.get("send_telemetry")
		if send_telemetry != True:
			return
		#end if

		telemetry_data = self.collect_telemetry_data()
		self.send_telemetry(telemetry_data)
		
		if self.send_benchmark_time + self.send_benchmark_interval < get_timestamp():
			benchmark_data = self.collect_benchmark_data()
			self.send_benchmark(benchmark_data)
		#end if
	#end define

	@publick
	def is_enabled(self):
		send_telemetry = self.local.db.get("send_telemetry")
		return send_telemetry == True
	#end define

	def collect_telemetry_data(self):
		statistics_module = get_module_by_name(self.local, "statistics")
		ton_storage_module = get_module_by_name(self.local, "ton-storage")
		ton_storage_provider_module = get_module_by_name(self.local, "ton-storage-provider")
		total_disk_space, used_disk_space, free_disk_space = get_disk_space(self.local.db.ton_storage.storage_path, decimal_size=3, round_size=2)

		data = Dict()
		data.storage = Dict()
		data.storage.pubkey = ton_storage_module.get_storage_pubkey()
		data.storage.disk_name = self.local.try_function(get_storage_disk_name)
		data.storage.total_disk_space = total_disk_space
		data.storage.used_disk_space = used_disk_space
		data.storage.free_disk_space = free_disk_space
		data.storage.service_uptime = get_service_uptime(ton_storage_module.service_name)

		data.storage.provider = Dict()
		data.storage.provider.pubkey = ton_storage_provider_module.get_provider_pubkey()
		data.storage.provider.used_provider_space = ton_storage_provider_module.get_used_provider_space(decimal_size=3, round_size=2)
		data.storage.provider.total_provider_space = ton_storage_provider_module.get_total_provider_space(decimal_size=3, round_size=2)
		data.storage.provider.max_bag_size_bytes = ton_storage_provider_module.get_provider_maxbagsize()
		data.storage.provider.service_uptime = get_service_uptime(ton_storage_provider_module.service_name)

		data.git_hashes = Dict()
		data.git_hashes = self.get_all_git_hashes()

		data.net_recv = statistics_module.get_statistics_data("net_recv_avg")
		data.net_sent = statistics_module.get_statistics_data("net_sent_avg")
		data.net_load = statistics_module.get_statistics_data("net_load_avg")
		data.bytes_recv = statistics_module.get_statistics_data("bytes_recv")
		data.bytes_sent = statistics_module.get_statistics_data("bytes_sent")
		data.disks_load = statistics_module.get_statistics_data("disks_load_avg")
		data.disks_load_percent = statistics_module.get_statistics_data("disks_load_percent_avg")
		data.iops = statistics_module.get_statistics_data("iops_avg")
		data.pps = statistics_module.get_statistics_data("pps_avg")
		data.ram = get_ram_info()
		data.swap = get_swap_info()
		data.uname = get_uname()

		data.cpu_info = Dict()
		data.cpu_info.cpu_count = psutil.cpu_count()
		data.cpu_info.cpu_load = get_load_avg()
		data.cpu_info.cpu_name = self.local.try_function(get_cpu_name)
		data.cpu_info.product_name = self.local.try_function(get_product_name)
		data.cpu_info.is_virtual = self.local.try_function(is_product_virtual)
		data.pings = self.local.try_function(get_pings_values)
		data.timestamp = get_timestamp()
		data.telemetry_pass = self.local.db.telemetry_pass

		return data
	#end define

	def collect_benchmark_data(self):
		if self.local.db.benchmark is None:
			return
		#end define

		data = Dict()
		ton_storage_provider_module = get_module_by_name(self.local, "ton-storage-provider")
		data.pubkey = ton_storage_provider_module.get_provider_pubkey()
		data.timestamp = get_timestamp()
		for key, value in self.local.db.benchmark.items():
			data[key] = value
		return data
	#end define

	def get_all_git_hashes(self):
		result = Dict()
		for module in self.local.buffer.modules:
			method = getattr(module, "get_my_git_hash_and_branch", None)
			if method == None:
				continue
			git_hash, git_branch = module.get_my_git_hash_and_branch()
			result[module.name] = git_hash
		return result
	#end define

	def send_telemetry(self, data):
		if data is None:
			self.local.add_log("send_telemetry error: data is None", "error")
			return
		#end define

		url = self.local.db.get("telemetry_url", self.telemetry_url)
		resp = self.send_data(url, data)
		#print("send_telemetry:", resp)
	#end define

	def send_benchmark(self, data):
		if data is None:
			self.local.add_log("send_benchmark error: data is None", "error")
			return
		#end define

		url = self.local.db.get("benchmark_url", self.benchmark_url)
		resp = self.send_data(url, data)
		self.send_benchmark_time = get_timestamp()
		#print("send_benchmark:", resp)
	#end define

	def send_data(self, url, data):
		additional_headers = dict()
		additional_headers["Content-Encoding"] = "gzip"
		additional_headers["Content-Type"] = "application/json"
		data_bytes = json.dumps(data).encode("utf-8")
		compressed_data = gzip.compress(data_bytes)
		resp = requests.post(url, data=compressed_data, headers=additional_headers, timeout=3)
		return resp
	#end define

	def install(self, install_args, install_answers):
		# install_args: user, src_dir, bin_dir, venvs_dir, venv_path, src_path
		mconfig_dir = f"/home/{install_args.user}/.local/share/mytonprovider"
		mconfig_path = f"{mconfig_dir}/mytonprovider.db"

		# read mconfig
		mconfig = read_config_from_file(mconfig_path)

		# edit mytoncore config
		mconfig.send_telemetry = True

		# write mconfig
		write_config_to_file(config_path=mconfig_path, data=mconfig)
	#end define
#end class
