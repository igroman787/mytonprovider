#!/usr/bin/env python3
# -*- coding: utf_8 -*-

from os import stat
from pwd import getpwuid
from mypylib import (
	MyPyClass,
	add2systemd,
	get_git_hash,
	get_git_last_remote_commit,
	get_service_status
)
from utils import (
	get_module_by_name,
	run_module_method_if_exist,
	set_check_data,
	run_subprocess
)
from decorators import publick


class Module():
	def __init__(self, local):
		self.name = "auto-updater"
		self.service_name = "mytonprovider-updater"
		self.local = local
	#end define

	@publick
	def is_enabled(self):
		stdout = run_subprocess(["systemctl", "list-unit-files", "--type=service"], timeout=3)
		result = f"{self.service_name}.service" in stdout
		return result
	#end define

	def update_modules(self):
		for module in self.local.buffer.modules:
			self.local.add_log(f"check module {module.name}")
			self.check_update_module(module)
	#end define

	def check_update_module(self, module):
		git_path = run_module_method_if_exist(self.local, module, "get_my_git_path")
		if git_path is None:
			return
		local_hash = get_git_hash(git_path)
		last_commit_hash, days_ago = get_git_last_remote_commit(git_path, with_days_ago=True)
		#print(module.name, local_hash, last_commit_hash, days_ago)
		if local_hash != last_commit_hash and days_ago > 7:
			self.local.add_log(f"{module.name} module update available")
			self.update_module(module)
	#end define

	def update_module(self, module):
		user = self.get_owner_user()
		update_args = run_module_method_if_exist(self.local, module, "get_update_args", user=user, restart_service=True)
		if update_args is None:
			return
		stdout = run_subprocess(update_args, timeout=60)
		self.local.add_log(f"Update {module.name} - OK")
	#end define

	def get_owner_user(self):
		file_path = "/var/ton/global.config.json"
		owner_uid = stat(file_path).st_uid
		owner_name = getpwuid(owner_uid).pw_name
		return owner_name
	#end define

	def install(self, install_args, install_answers):
		# install_args: user, src_dir, bin_dir, venvs_dir, venv_path, src_path
		# Создать службу
		start_cmd = f"{install_args.venv_path}/bin/python3 {install_args.src_path}/updater.py"
		add2systemd(name=self.service_name, user="root", start=start_cmd, workdir=install_args.src_path, force=True)

		# Запустить службу
		self.local.start_service(self.service_name)
	#end define
#end class
