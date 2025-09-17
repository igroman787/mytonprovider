#!/usr/bin/env python3
# -*- coding: utf_8 -*-

import shutil
import random
from string import digits, ascii_letters
from functools import lru_cache
from pathlib import Path
import importlib
from os import listdir
from os.path import normpath, isdir
import sys
from mypylib import (
	Dict,
	bcolors,
	get_timestamp
)
import subprocess


def init_localization(local):
	translate_path = f"{local.buffer.my_dir}/resources/translate.json"
	local.init_translator(translate_path)
#end define

def get_disk_space(disk_path, decimal_size, round_size):
	# decimal_size: bytes=0, kilobytes=1, megabytes=2, gigabytes=3, terabytes=4
	total, used, free = shutil.disk_usage(disk_path)
	total_space = convert_to_required_decimal(total, decimal_size, round_size)
	used_space = convert_to_required_decimal(used, decimal_size, round_size)
	free_space = convert_to_required_decimal(free, decimal_size, round_size)
	return total_space, used_space, free_space
#end define

def convert_to_required_decimal(input_int, decimal_size, round_size):
	result_int = input_int /1024**decimal_size
	result = round(result_int, round_size)
	return result
#end define

def fix_git_config(git_path):
	git_path = normpath(git_path)
	if not isdir(git_path):
		#print(f"fix_git_config warning: dir not found: {git_path}")
		return
	args = ["git", "status"]
	try:
		process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=git_path, timeout=3)
		err = process.stderr.decode("utf-8")
	except Exception as ex:
		err = str(ex)
	if err:
		if 'git config --global --add safe.directory' in err:
			args = ["git", "config", "--global", "--add", "safe.directory", git_path]
			subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
		else:
			raise Exception(f'Failed to check git status: {err}')
# end define

@lru_cache
def get_package_path():
	cwd = str(Path(__file__).resolve())
	return cwd.split("mytonprovider")[0] + "mytonprovider"
#end define

def generate_login() -> str:
	return r''.join(random.choices(population=ascii_letters, k=10))
#end define

def generate_password() -> str:
	# punctuation = r"""!#$%&()*+,-./:;<=>?@[\]^_{|}~"""
	symbols = ascii_letters + digits #+ punctuation
	return r''.join(random.choices(population=symbols, k=10))
#end define

def parse_input_args():
	input_args: list = sys.argv[1:]
	args = Dict()
	for i in range(0, len(input_args), 2):
		if input_args[i].startswith("--"):
			key = input_args[i].lstrip("--")
			args[key] = input_args[i+1]
		else:
			print("Unknown schema of args")
			sys.exit(1)
	return args
#end define

def reduct(text):
	if text is None:
		return
	if len(text) < 16:
		return text
	end = len(text)
	result = text[0:6] + "..." + text[end - 6:end]
	return result
#end define

def get_color_int(data, borderline_value, logic, ending=None):
	if data is None:
		result = "n/a"
	elif logic == "more":
		if data >= borderline_value:
			result = bcolors.green_text(data, ending)
		else:
			result = bcolors.red_text(data, ending)
	elif logic == "less":
		if data <= borderline_value:
			result = bcolors.green_text(data, ending)
		else:
			result = bcolors.red_text(data, ending)
	return result
#end define

def get_service_status_color(input):
	if input == True:
		result = bcolors.green_text("working")
	else:
		result = bcolors.red_text("not working")
	return result
#end define

def set_check_data(module, check_name, data):
	timestamp = get_timestamp()
	if module.name not in module.local.buffer:
		module.local.buffer[module.name] = Dict()
	module.local.buffer[module.name][check_name] = (timestamp, data)
#end define

def get_check_data(module, check_name):
	if (module.name not in module.local.buffer or 
		check_name not in module.local.buffer[module.name]):
		return
	timestamp, data = module.local.buffer[module.name][check_name]
	#if get_timestamp() > timestamp + 300:
	#	result = None
	#	error = "The data is out of date. Re-running the check"
	#	module.local.start_thread(module.check_thread)
	return data
#end define

def get_check_port_status(module):
	result = get_check_data(module, check_name="port")
	if result is None:
		status = "Clarification"
	elif result is True:
		status = bcolors.green_text("Open")
	elif result is False:
		status = bcolors.red_text("Close")
	else:
		status = "Unknown"
	return status
#end define

def get_check_update_status(module):
	result = get_check_data(module, check_name="update")
	if result is None:
		status = "Clarification"
	elif result is True:
		status = bcolors.magenta_text("Update available")
	elif result is False:
		status = None
	else:
		status = "Unknown"
	return status
#end define

def run_subprocess(args, timeout):
	is_shell = type(args) == str
	process = subprocess.run(
		args, 
		stdin=subprocess.PIPE, 
		stdout=subprocess.PIPE, 
		stderr=subprocess.PIPE, 
		timeout=timeout, 
		shell=is_shell
	)
	stdout = process.stdout.decode("utf-8")
	stderr = process.stderr.decode("utf-8")
	if process.returncode != 0:
		raise Exception(f"run_subprocess error: {stderr}")
	return stdout
#end define

def get_module_type(module):
	module_type_list = list()
	if None != getattr(module, "service_name", None):
		module_type_list.append("service")
	if None != getattr(module, "daemon", None):
		module_type_list.append("daemon")
	if None != getattr(module, "get_my_git_path", None):
		module_type_list.append("git")
	if None != getattr(module, "pre_up", None):
		module_type_list.append("checkable")
	if None != getattr(module, "status", None):
		module_type_list.append("statusable")
	if None != getattr(module, "get_update_args", None):
		module_type_list.append("updatable")
	if None != getattr(module, "install", None):
		module_type_list.append("installable")
	module_type = ", ".join(module_type_list)
	return module_type
#end define


###
### Для работы с модулями
###

def import_commands(local, console):
	for module in local.buffer.modules:
		method = getattr(module, "get_console_commands", None)
		if method == None:
			continue
		commands = module.get_console_commands()
		do_import_commands(console, commands)
#end define

def do_import_commands(console, commands):
	for command in commands:
		console.AddItem(command.cmd, command.func, command.desc)
#end define

def import_modules(local):
	local.buffer.modules = list()
	modules_dir = f"{local.buffer.my_dir}/modules"
	sys.path.append(modules_dir)
	modules_names = get_modules_names_from_dir(modules_dir)
	for module_name in modules_names:
		file_module = importlib.import_module(module_name)
		if "Module" not in file_module.__dict__:
			#print(module_name, "not_module")
			continue
		module = file_module.Module(local)
		local.buffer.modules.append(module)
#end define

def get_modules(local, check_is_enabled=True):
	result = list()
	for module in local.buffer.modules:
		is_enabled = is_module_enabled(module)
		if check_is_enabled and is_enabled == False:
			#print(module_name, "not_enabled")
			continue
		result.append(module)
	return result
#end define

def is_module_enabled(module, default=True):
	is_enabled_func = getattr(module, "is_enabled", None)
	if is_enabled_func == None:
		return default
	return module.is_enabled()
#end define

def get_modules_names_from_dir(search_dir):
	modules_names = list()
	for item in listdir(search_dir):
		if not item.endswith(".py"):
			continue
		module_name, file_type = item.split('.')
		modules_names.append(module_name)
	modules_names.sort()
	return modules_names
#end define

def get_modules_names(local, mandatory=False):
	result = list()
	for module in local.buffer.modules:
		module_name = getattr(module, "name", None)
		is_mandatory = getattr(module, "mandatory", False)
		if module_name != None and is_mandatory == mandatory:
			result.append(module_name)
	return result
#end define

def get_module_by_name(local, input_module_name):
	for module in local.buffer.modules:
		module_name = getattr(module, "name", None)
		if module_name == input_module_name:
			return module
	raise Exception(f"get_module_by_name error: module {input_module_name} not found")
#end define

def run_module_method_if_exist(local, module, method_name, *args, **kwargs):
	method = getattr(module, method_name, None)
	if method == None:
		return
	return method(*args, **kwargs)
#end define
