#!/usr/bin/env python3
# -*- coding: utf_8 -*-

import os
import base64
import tonutils
import tonutils.client
import tonutils.wallet
from random import randint
from asgiref.sync import async_to_sync

from mypylib import (
	Dict,
	bcolors,
	MyPyClass,
	color_print,
	add2systemd,
	read_config_from_file,
	write_config_to_file,
	get_own_ip,
	get_git_hash,
	get_git_branch,
	get_service_status,
	get_service_uptime,
	time2human,
	check_git_update
)
from adnl_over_tcp import (
	get_messages,
	wait_message,
	get_account
)
from utils import (
	get_module_by_name,
	convert_to_required_decimal,
	fix_git_config,
	get_service_status_color,
	get_check_port_status,
	set_check_data,
	get_check_update_status,
	run_subprocess
)
from decorators import publick
from adnl_over_udp_checker import check_adnl_connection
from addr_and_key import (
	addr_to_bytes,
	get_pubkey_from_privkey,
	split_provider_key
)


class Module():
	def __init__(self, local):
		self.name = "ton-storage-provider"
		self.service_name = self.name
		self.local = local
		self.mandatory = False
		self.local.add_log(f"{self.name} module init done", "debug")

		self.go_package = Dict()
		self.go_package.author = "xssnick"
		self.go_package.repo = "tonutils-storage-provider"
		self.go_package.branch = "master"
		self.go_package.entry_point = "cmd/main.go"
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
	
	def is_enabled_old(self):
		if "ton_storage" in self.local.db:
			if "provider" in self.local.db.ton_storage:
				return True
		return False
	#end define

	@publick
	def get_console_commands(self):
		commands = list()

		register = Dict()
		register.cmd = "register"
		register.func = self.register
		register.desc = self.local.translate("register_cmd")
		commands.append(register)

		import_wallet = Dict()
		import_wallet.cmd = "import_wallet"
		import_wallet.func = self.import_wallet
		import_wallet.desc = self.local.translate("import_wallet_cmd")
		commands.append(import_wallet)

		export_wallet = Dict()
		export_wallet.cmd = "export_wallet"
		export_wallet.func = self.export_wallet
		export_wallet.desc = self.local.translate("export_wallet_cmd")
		commands.append(export_wallet)

		return commands
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
		adnl_pubkey = self.get_adnl_pubkey()
		provider_config = self.get_provider_config()
		listen_ip, provider_port = provider_config.ListenAddr.split(':')
		
		own_ip = get_own_ip()
		if provider_config.ExternalIP != own_ip:
			raise Exception("provider_config.ExternalIP != own_ip")
		result, status = check_adnl_connection(own_ip, provider_port, adnl_pubkey)
		set_check_data(module=self, check_name="port", data=result)
	#end define

	@publick
	@async_to_sync
	async def register(self, args):
		self.local.add_log("start register function")
		if self.local.db.ton_storage.provider.is_already_registered and "--force" not in args:
			text = self.local.translate("provider_already_registered")
			color_print(f"{{green}}{text}{{endc}}")
			return
		#end define

		# Проверить баланс провайдера
		wallet = await self.get_provider_wallet()
		if wallet.balance < 0.03:
			text = self.local.translate("low_provider_balance")
			color_print(f"{{red}}{text}{{endc}}")
			return
		#end if

		# Проверить что кошелек активен
		if wallet.status == "uninit":
			await self.do_deploy(wallet)
		#end if

		# Зарегистрироваться в списке отправив транзакцию
		destination = "0:7777777777777777777777777777777777777777777777777777777777777777"
		provider_pubkey = self.get_provider_pubkey()
		comment = f"tsp-{provider_pubkey.lower()}"
		await self.do_register(wallet, destination, comment)
		color_print("{green}provider regiser - OK{endc}")
	#end define

	async def do_deploy(self, wallet):
		self.local.add_log("start do_deploy function", "debug")
		account, shard_account = await get_account(wallet.addr)
		end_lt = shard_account.last_trans_hash
		end_hash = shard_account.last_trans_hash.hex()

		msg_hash = await wallet.obj.deploy()
		await wait_message(wallet.addr, msg_hash, end_lt, end_hash)
	#end define

	async def do_register(self, wallet, destination, comment):
		self.local.add_log("start do_register function", "debug")
		account, shard_account = await get_account(wallet.addr)
		end_lt = shard_account.last_trans_hash
		end_hash = shard_account.last_trans_hash.hex()

		msg_hash = await wallet.obj.transfer(
			destination = destination, 
			amount = 0.01, 
			body = comment
		)
		await wait_message(wallet.addr, msg_hash, end_lt, end_hash)
		self.local.db.ton_storage.provider.is_already_registered = True
	#end define

	async def get_provider_wallet(self):
		provider_config = self.get_provider_config()
		client = tonutils.client.LiteserverClient(is_testnet=False)
		private_key = base64.b64decode(provider_config.ProviderKey)
		wallet = Dict()
		wallet.obj = tonutils.wallet.WalletV3R2.from_private_key(client, private_key)
		wallet.addr = wallet.obj.address.to_str()
		wallet.account = await client.get_raw_account(wallet.addr)
		wallet.status = wallet.account.status.value
		wallet.balance = wallet.account.balance /10**9
		return wallet
	#end define

	def get_adnl_pubkey(self):
		provider_config = self.get_provider_config()
		adnl_bytes = base64.b64decode(provider_config.ADNLKey)
		adnl_pubkey_bytes = adnl_bytes[32:64]
		adnl_pubkey = adnl_pubkey_bytes.hex().upper()
		return adnl_pubkey
	#end define

	def get_provider_pubkey(self):
		provider_config = self.get_provider_config()
		provider_bytes = base64.b64decode(provider_config.ProviderKey)
		provider_pubkey_bytes = provider_bytes[32:64]
		provider_pubkey = provider_pubkey_bytes.hex().upper()
		return provider_pubkey
	#end define

	def get_provider_maxbagsize(self):
		provider_config = self.get_provider_config()
		return provider_config.MaxBagSizeBytes
	#end define

	@publick
	@async_to_sync
	async def import_wallet(self, args):
		try:
			key = args[0]
		except:
			color_print("{red}Bad args. Usage:{endc} import_wallet <wallet-private-key>")
			return
		self.do_import_wallet(key)
		color_print("import_wallet - {green}OK{endc}")
	#end define

	def do_import_wallet(self, privkey):
		privkey_bytes = base64.b64decode(privkey)
		pubkey_bytes = get_pubkey_from_privkey(privkey_bytes)
		provider_key_bytes = privkey_bytes + pubkey_bytes

		provider_config = self.get_provider_config()
		provider_config.ProviderKey = base64.b64encode(provider_key_bytes).decode("utf-8")
		self.set_provider_config(provider_config)
	#end define

	@publick
	@async_to_sync
	async def export_wallet(self, args):
		provider_config = self.get_provider_config()
		key_b64 = provider_config.ProviderKey
		privkey, pubkey = split_provider_key(key_b64)
		privkey_b64 = base64.b64encode(privkey).decode("utf-8")
		wallet = await self.get_provider_wallet()

		print("Address:", wallet.addr)
		print("Private key:", privkey_b64)
	#end define

	@publick
	@async_to_sync
	async def status(self, args):
		color_print("{cyan}===[ Local provider status ]==={endc}")
		self.print_module_name()
		self.print_provider_pubkey()
		await self.print_provider_wallet()
		self.print_storage_cost()
		self.print_profit()
		self.print_provider_space()
		self.print_port_status()
		self.print_service_status()
		self.print_git_hash()
	#end define

	def print_module_name(self):
		module_name = bcolors.yellow_text(self.name)
		text = self.local.translate("module_name").format(module_name)
		print(text)
	#end define

	def print_provider_pubkey(self):
		provider_pubkey = self.get_provider_pubkey()
		provider_pubkey_text = bcolors.yellow_text(provider_pubkey)
		text = self.local.translate("provider_pubkey").format(provider_pubkey_text)
		print(text)
	#end define

	async def print_provider_wallet(self):
		wallet = await self.get_provider_wallet()
		addr = bcolors.yellow_text(wallet.addr)
		balance = bcolors.green_text(wallet.balance)
		addr_text = self.local.translate("provider_wallet").format(addr)
		balance_text = self.local.translate("provider_balance").format(balance)
		print(addr_text)
		print(balance_text)
	#end define

	def print_storage_cost(self):
		storage_cost = self.get_storage_cost()
		storage_cost_text = bcolors.yellow_text(storage_cost)
		text = self.local.translate("storage_cost").format(storage_cost_text)
		print(text)
	#end define

	def print_profit(self):
		real_profit, maximum_profit = self.get_profit()
		real_profit_text = bcolors.green_text(real_profit)
		max_profit_text = bcolors.yellow_text(maximum_profit)
		text = self.local.translate("provider_profit").format(real_profit_text, max_profit_text)
		print(text)
	#end define

	def print_provider_space(self):
		used_provider_space = self.get_used_provider_space(decimal_size=3, round_size=2)
		total_provider_space = self.get_total_provider_space(decimal_size=3, round_size=2)
		used_provider_space_text = bcolors.green_text(used_provider_space) # TODO
		total_provider_space_text = bcolors.yellow_text(total_provider_space)
		text = self.local.translate("provider_space").format(used_provider_space_text, total_provider_space_text)
		print(text)
	#end define

	def print_port_status(self):
		provider_config = self.get_provider_config()
		listen_ip, provider_port = provider_config.ListenAddr.split(':')
		port_color = bcolors.yellow_text(provider_port, " udp")
		status = get_check_port_status(module=self)
		text = self.local.translate("port_status").format(port_color, status)
		print(text)
	#end define

	def print_service_status(self):
		service_status = get_service_status(self.service_name)
		service_uptime = get_service_uptime(self.service_name)
		service_status_color = get_service_status_color(service_status)
		service_uptime_color = bcolors.green_text(time2human(service_uptime))
		text = self.local.translate("service_status_and_uptime").format(service_status_color, service_uptime_color)
		print(text)
	#end define

	def print_git_hash(self):
		git_hash, git_branch = self.get_my_git_hash_and_branch()
		git_hash_text = bcolors.yellow_text(git_hash)
		git_branch_text = bcolors.yellow_text(git_branch)
		text = self.local.translate("git_hash").format(git_hash_text, git_branch_text)
		update_status = get_check_update_status(module=self)
		if update_status:
			text += f", {update_status}"
		print(text)
	#end define

	def get_used_provider_space(self, decimal_size, round_size):
		ton_storage_module = get_module_by_name(self.local, "ton-storage")
		api_data = ton_storage_module.get_api_data()
		used_provider_space = ton_storage_module.get_bags_size(api_data, decimal_size, round_size)
		return used_provider_space
	#end define

	def get_total_provider_space(self, decimal_size, round_size):
		# decimal_size: bytes=0, kilobytes=1, megabytes=2, gigabytes=3, terabytes=4
		provider_config = self.get_provider_config()
		result_megabytes = provider_config.Storages[0].SpaceToProvideMegabytes
		result_int = result_megabytes *1024**2
		result = convert_to_required_decimal(result_int, decimal_size, round_size)
		return result
	#end define

	def get_provider_config(self):
		provider = self.local.db.ton_storage.provider
		return read_config_from_file(provider.config_path)
	#en define

	def set_provider_config(self, provider_config):
		provider = self.local.db.ton_storage.provider
		write_config_to_file(config_path=provider.config_path, data=provider_config)
	#en define

	def get_my_git_hash_and_branch(self):
		git_path = self.get_my_git_path()
		git_hash = get_git_hash(git_path, short=True)
		git_branch = get_git_branch(git_path)
		return git_hash, git_branch
	#end define

	def get_my_git_path(self):
		#provider = self.local.db.ton_storage.provider
		#git_path = f"{provider.src_dir}/{self.go_package.repo}"
		git_path = f"/usr/src/{self.go_package.repo}"
		fix_git_config(git_path)
		return git_path
	#end define

	def get_storage_cost(self):
		# 1_mb_per_day --> 200_gb_per_month
		provider_config = self.get_provider_config()
		min_rate_per_mb_day = float(provider_config.MinRatePerMBDay)
		storage_cost = min_rate_per_mb_day *200 *1024 *30
		return round(storage_cost, 2)
	#end define

	def get_profit(self):
		provider_config = self.get_provider_config()
		used_provider_space = self.get_used_provider_space(decimal_size=2, round_size=0)
		total_provider_space = self.get_total_provider_space(decimal_size=2, round_size=0)
		min_rate_per_mb_day = float(provider_config.MinRatePerMBDay)
		real_profit = round(used_provider_space * min_rate_per_mb_day *30, 2)
		maximum_profit = round(total_provider_space * min_rate_per_mb_day *30, 2)
		return real_profit, maximum_profit
	#end define

	@publick
	def get_update_args(self, restart_service=False, **kwargs):
		# Temporarily. Delete in TODO
		if self.local.db.ton_storage != None:
			provider_config = self.get_provider_config()
			provider_config.MaxSpan = self.calculate_MaxSpan(self.get_storage_cost())
			self.set_provider_config(provider_config)
		#end if

		script_path = f"{self.local.buffer.my_dir}/scripts/install_go_package.sh"
		update_args = [
			"bash",	script_path, 
			"-a", self.go_package.author, 
			"-r", self.go_package.repo, 
			"-b", self.go_package.branch, 
			"-e", self.go_package.entry_point
		]
		if restart_service == True:
			update_args += ["-s", self.service_name]
		return update_args
	#end define

	def install(self, install_args, install_answers):
		# install_args: user, src_dir, bin_dir, venvs_dir, venv_path, src_path
		udp_port = randint(1024, 65000)

		mconfig_dir = f"/home/{install_args.user}/.local/share/mytonprovider"
		mconfig_path = f"{mconfig_dir}/mytonprovider.db"
		provider_path = f"{install_answers.storage_path}/provider"
		db_dir = f"{provider_path}/db"
		provider_config_path = f"{provider_path}/config.json"
		provider_config_path

		# Склонировать исходники и скомпилировать бинарники
		upgrade_args = self.get_update_args(install_args.src_path)
		run_subprocess(upgrade_args, timeout=60 * 5)

		# Подготовить папку
		os.makedirs(provider_path, exist_ok=True)
		chown_args = [
			"chown", 
			install_args.user + ':' + install_args.user, 
			provider_path
		]
		run_subprocess(chown_args, timeout=3)

		# Создать службу
		main_module = get_module_by_name(self.local, "main")
		start_cmd = f"{install_args.bin_dir}/{self.go_package.repo} --db {db_dir} --config {provider_config_path} -network-config {main_module.global_config_path}"
		add2systemd(name=self.service_name, user=install_args.user, start=start_cmd, workdir=provider_path, force=True)

		# Первый запуск - создание конфига
		self.local.start_service(self.service_name, sleep=10)
		self.local.stop_service(self.service_name)

		# read mconfig
		mconfig = read_config_from_file(mconfig_path)

		# read provider config
		provider_config = read_config_from_file(provider_config_path)

		# edit provider config
		api = mconfig.ton_storage.api
		provider_config.ListenAddr = f"0.0.0.0:{udp_port}"
		provider_config.ExternalIP = get_own_ip()
		provider_config.MinSpan = 3600 *24 *7
		provider_config.MaxSpan = self.calculate_MaxSpan(install_answers.storage_cost)
		provider_config.MinRatePerMBDay = self.calculate_MinRatePerMBDay(install_answers.storage_cost)
		provider_config.MaxBagSizeBytes = 40 * 1024**3 # 40GB
		provider_config.Storages[0].BaseURL = f"http://{api.host}:{api.port}"
		provider_config.Storages[0].SpaceToProvideMegabytes = self.calculate_space_to_provide(install_answers.space_to_provide_gigabytes)
		provider_config.CRON.Enabled = True

		# write provider config
		write_config_to_file(config_path=provider_config_path, data=provider_config)

		# edit mytoncore config
		provider = Dict()
		provider.config_path = provider_config_path
		provider.src_dir = install_args.src_dir
		mconfig.ton_storage.provider = provider

		# write mconfig
		write_config_to_file(config_path=mconfig_path, data=mconfig)

		# start provider
		self.local.start_service(self.service_name)
	#end define

	def calculate_space_to_provide(self, input_space):
		# convert gigabytes to megabytes
		input_space_int = int(input_space)
		result = input_space_int *1024
		return result
	#end define

	def calculate_MaxSpan(self, storage_cost):
		min_proof_cost = 0.05
		min_span = 3600 *24 *30
		min_bag_size = 400
		# 200_gb_per_month --> 1_mb_per_sec
		data = float(storage_cost) /200 /1024 /30 /24 /3600
		max_span = int(min_proof_cost /(data *min_bag_size))
		if max_span < min_span:
			return min_span
		if max_span > 4294967290:
			max_span = 4294967290
		return max_span
	#end define

	def calculate_MinRatePerMBDay(self, storage_cost):
		# 200_gb_per_month --> 1_mb_per_day
		data = float(storage_cost) /200 /1024 /30
		return f"{data:.9f}"
	#end define
#end class
