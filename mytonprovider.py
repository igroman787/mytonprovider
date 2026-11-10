#!/usr/bin/env python3
# -*- coding: utf_8 -*-

import sys
import json
from getpass import getuser
from itertools import islice

from modules.ls_monitor import LSMonitor
from mypyconsole.mypyconsole import MyPyConsole
from mypylib import (
	MyPyClass,
	run_as_root,
	color_print,
	thr_sleep,
	print_table,
)
from utils import (
	get_modules,
	get_module_by_name,
	import_commands,
	import_modules,
	run_module_method_if_exist,
	is_module_enabled,
	init_localization,
	set_check_data,
	get_module_type,
	parse_github_url,
)


local = MyPyClass(__file__)
console = MyPyConsole()


def init():
	local.run()
	import_modules(local)
	init_localization(local)
	import_commands(local, console)
	
	if "--daemon" in sys.argv:
		init_daemon()
	else:
		init_console()
#end define

def init_daemon():
	main_module = get_module_by_name(local, "main")
	run_module_method_if_exist(local, main_module, "download_global_config")

	#threading.current_thread().name = "daemon"
	for module in get_modules(local):
		# Основной daemon
		method = getattr(module, "daemon", None)
		if method == None:
			continue
		cycle_name = f"{module.name}-daemon"
		local.start_cycle(module.daemon, name=cycle_name, sec=module.daemon_interval)

		# Дополнительные daemons
		extra_daemons = getattr(module, "extra_daemons", None)
		if extra_daemons == None:
			continue
		for extra_daemon in extra_daemons:
			local.start_cycle(extra_daemon.func, name=extra_daemon.name, sec=extra_daemon.interval)
	thr_sleep()
#end define

def init_console():
	console.name = "MyTonProvider"
	console.start_function = pre_up
	console.debug = local.db.debug or False
	console.local = local
	if console.debug == True:
		color_print("{red} Debug mode enabled {endc}")
	#end if

	console.add_item("status", status, local.translate("status_cmd"))
	console.add_item("update", update, local.translate("update_cmd"))
	console.add_item("install", install, local.translate("install_cmd"))
	console.add_item("get", get_settings, local.translate("get_cmd"))
	console.add_item("set", set_settings, local.translate("set_cmd"))
	console.add_item("modules_list", modules_list, local.translate("modules_list_cmd"))
	console.add_item("ls_status", ls_status, local.translate("ls_status_cmd"))
	console.run()
#end define

def pre_up():
	modules = get_modules(local)
	for module in modules:
		run_module_method_if_exist(local, module, "pre_up")
#end define

def status(args):
	count = 1
	modules = get_modules(local)
	for module in modules:
		method = getattr(module, "status", None)
		if method == None:
			continue
		module.status(args)
		if count < len(modules):
			count += 1
			print()
#end define

def update(args):
	try:
		if len(args) < 1 or len(args) > 4:
			raise ValueError
		module_name = args[0]
		branch = next(islice(args, 1, None), None)
		author = next(islice(args, 2, None), None)
		repo = next(islice(args, 3, None), None)
	except:
		color_print("{red}Bad args. Usage:{endc} update <module-name> [<url>] | [<branch>] [<author>] [<repo>]")
		return
	# end try

	if branch is not None and "github.com" in branch:
		author, repo, branch = parse_github_url(branch)

	user = getuser()
	module = get_module_by_name(local, module_name)

	try:
		update_args = run_module_method_if_exist(
			local,
			module,
			"get_update_args",
			user=user,
			author=author,
			repo=repo,
			branch=branch,
			restart_service=True,
		)
	except Exception as e:
		color_print("{red}" + str(e) + "{endc}")
		return
	# end try

	# Запускаем команду обновления от root
	exit_code = run_as_root(update_args)
	if exit_code == 0:
		set_check_data(module, check_name="update", data=False)
		text = f"Update {module_name} - {{green}}OK{{endc}}"
	else:
		text = f"Update {module_name} - {{red}}Error{{endc}}"
	color_print(text)
	if module_name == "main":
		local.exit()
#end define

def install(args):
	try:
		module_name = args[0]
	except:
		color_print("{red}Bad args. Usage:{endc} install <module-name>")
		return
	# end try

	module = get_module_by_name(local, module_name)
	if getattr(module, "mandatory", False) == True:
		color_print(f"{{red}}Module {module_name} is mandatory{{endc}}")
		return
	if run_module_method_if_exist(local, module, "is_enabled") == True:
		color_print(f"{{red}}Module {module_name} is already installed{{endc}}")
		return
	#end if

	for depend_name in getattr(module, "depends_on", list()):
		depend_module = get_module_by_name(local, depend_name)
		if is_module_enabled(depend_module) == False:
			color_print(f"{{red}}Module {module_name} requires {depend_name}{{endc}}")
			return

	install_args = local.db.install_args
	install_cmd = [f"{install_args.venv_path}/bin/python3", f"{install_args.src_path}/install.py"]
	for name, value in install_args.items():
		install_cmd += [f"--{name}", value]
	install_cmd += ["--module", module_name]

	# Запускаем установку от root
	exit_code = run_as_root(install_cmd)
	if exit_code == 0:
		if module_name not in local.db.install_answers.utils:
			local.db.install_answers.utils.append(module_name)
		run_as_root(["systemctl", "restart", "mytonproviderd"])
		text = f"Install {module_name} - {{green}}OK{{endc}}"
	else:
		text = f"Install {module_name} - {{red}}Error{{endc}}"
	color_print(text)
#end define

def get_settings(args):
	try:
		name = args[0]
	except:
		color_print("{red}Bad args. Usage:{endc} get <settings-name>")
		return
	result = local.db.get(name)
	print(json.dumps(result, indent=2))
#end defin

def set_settings(args):
	try:
		name = args[0]
		value = args[1]
	except:
		color_print("{red}Bad args. Usage:{endc} set <settings-name> <settings-value>")
		return
	data = json.loads(value)
	local.db[name] = data
	color_print("SetSettings - {green}OK{endc}")
#end define

def modules_list(args):
	table = [["Name", "Is enabled", "Mandatory", "Type"]]
	for module in get_modules(local, check_is_enabled=False):
		is_mandatory = getattr(module, "mandatory", False)
		if is_mandatory == True:
			is_enabled = ""
		else:
			is_enabled = run_module_method_if_exist(local, module, "is_enabled")
		module_type = get_module_type(module)
		table += [[module.name, is_enabled, is_mandatory, module_type]]
	print_table(table)
#end define

def ls_status(args):
	ls_monitor = LSMonitor(local)
	ls_monitor.run_ls_status(args)
#end define


if __name__ == "__main__":
	init()
#end if
