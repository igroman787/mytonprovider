#!/usr/bin/env python3
# -*- coding: utf_8 -*-

from typing import Any
import inquirer
import sys
import os
from mypylib import (
	Dict,
	MyPyClass,
	read_config_from_file
)
from utils import (
	import_modules,
	get_modules_names,
	get_module_by_name,
	init_localization,
	get_disk_space
)


local = MyPyClass(__file__)
local.db.config.logLevel = "debug"


default_storage_path = "/var/storage"
default_storage_cost = 10
default_traffic_cost = 1



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

def validate_storage(answers, storage_path):
	try:
		os.makedirs(storage_path, exist_ok=True)
		return True
	except:
		return False
#end define

def validate_cost(answers, cost):
	try:
		float(cost)
		return True
	except:
		return False
#end define

def ignore_storage(answers):
	if "ton-storage" in answers["utils"]:
		return False
	return True
#end define

def ignore_provider(answers):
	if "ton-storage-provider" in answers["utils"]:
		return False
	return True
#end define

def ignore_tunnel(answers):
	if "ton-tunnel-provider" in answers["utils"]:
		return False
	return True
#end define

def calculate_space_to_provide(answers):
	save_answers = get_save_answers()
	if save_answers.space_to_provide_gigabytes != None:
		return save_answers.space_to_provide_gigabytes
	storage_path = answers.get("storage_path")
	os.makedirs(storage_path, exist_ok=True)
	total_space, used_space, free_space = get_disk_space(storage_path, decimal_size=3, round_size=0)
	available_space = int(free_space * 0.9)
	return str(available_space)
#end define

def question_space_to_provide(answers):
	storage_path = answers.get("storage_path")
	total_space, used_space, free_space = get_disk_space(storage_path, decimal_size=3, round_size=0)
	text = local.translate("question_space_to_provide").format(total_space, free_space)
	return text
#end define

def calculate_utils(answers):
	save_answers = get_save_answers()
	result = save_answers.utils or list()
	return result
#end define

def calculate_storage_path(answers):
	save_answers = get_save_answers()
	result = save_answers.storage_path or default_storage_path
	return result
#end define

def calculate_storage_cost(answers):
	save_answers = get_save_answers()
	result = save_answers.storage_cost or default_storage_cost
	return str(result)
#end define

def calculate_traffic_cost(answers):
	save_answers = get_save_answers()
	result = save_answers.traffic_cost or default_traffic_cost
	return str(result)
#end define

def get_save_answers():
	save_answers = Dict()
	install_args = parse_input_args()
	file_path = f"/home/{install_args.user}/.local/share/mytonprovider/mytonprovider.db"
	if os.path.isfile(file_path) == False:
		return save_answers
	data = read_config_from_file(file_path)
	save_answers = data.install_answers or Dict()
	return save_answers
#end define

def create_questions():
	questions = [
		inquirer.Checkbox(
			name="utils",
			message=local.translate("question_utils"),
			choices=get_modules_names(local),
			default=calculate_utils
		),
		inquirer.Text(
			name="storage_path",
			message=local.translate("question_storage_path"),
			default=calculate_storage_path,
			ignore=ignore_storage,
			validate=validate_storage
		),
		inquirer.Text(
			name="storage_cost",
			message=local.translate("question_storage_cost"),
			default=calculate_storage_cost,
			ignore=ignore_provider,
			validate=validate_cost
		),
		inquirer.Text(
			name="space_to_provide_gigabytes",
			message=question_space_to_provide,
			default=calculate_space_to_provide,
			ignore=ignore_provider
		),
		inquirer.Text(
			name="traffic_cost",
			message=local.translate("question_traffic_cost"),
			default=calculate_traffic_cost,
			ignore=ignore_tunnel
		)
	]
	return questions
#end define

def main():
	# install_args: user, src_dir, bin_dir, venvs_dir, venv_path, src_path
	install_args = parse_input_args()
	noninteractive_args = ("utils", "storage_path", "storage_cost", "space_to_provide_gigabytes")

	if all(k in install_args for k in noninteractive_args):
		install_answers = Dict({
			"utils": install_args.utils.split(","),
			"storage_path": install_args.storage_path,
			"storage_cost": str(install_args.storage_cost),
			"space_to_provide_gigabytes": str(install_args.space_to_provide_gigabytes),
			"traffic_cost": str(default_traffic_cost),
		})
		for k in noninteractive_args:
			install_args.pop(k, None)
	else:
		questions = create_questions()
		install_answers = Dict(inquirer.prompt(questions))

	need_modules_names = install_answers.get("utils")
	need_modules_names += get_modules_names(local, mandatory=True)
	need_modules_names.sort()
	#print("need_modules_names:", need_modules_names)

	for need_module_name in need_modules_names:
		need_module = get_module_by_name(local, need_module_name)
		method = getattr(need_module, "install", None)
		if method == None:
			continue
		need_module.install(install_args, install_answers)
#end define


if __name__ == "__main__":
	storage_path = calculate_storage_path(None)
	a = validate_storage(None, storage_path)
	print("validate_storage a:", a)

	import_modules(local)
	init_localization(local)
	main()
#end if
