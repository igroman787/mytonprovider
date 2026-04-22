#!/usr/bin/env python3
# -*- coding: utf_8 -*-

import os
import psutil
import subprocess
from mypylib import (
    Dict,
    bcolors,
    color_print,
    add2systemd,
    write_config_to_file,
    get_git_hash,
    get_git_branch,
    get_git_author_and_repo,
    get_service_status,
    get_service_uptime,
    time2human,
    check_git_update,
    get_load_avg,
)
from utils import (
    get_module_by_name,
    fix_git_config,
    get_service_status_color,
    set_check_data,
    get_check_update_status,
    get_color_int,
    validate_github_repo,
)
from server_info import (
    get_ram_info,
    get_swap_info,
)
from decorators import publick


class Module:
    def __init__(self, local):
        self.name = "main"
        self.service_name = "mytonproviderd"
        self.local = local
        self.mandatory = True
        self.local.add_log(f"{self.name} module init done", "debug")

        self.py_package = Dict()
        self.py_package.author = "igroman787"
        self.py_package.repo = "mytonprovider"
        self.py_package.branch = "master"

        self.global_config_name = "global.config.json"
        self.global_config_dir = f"{self.local.buffer.my_dir}/config"
        self.global_config_path = f"{self.global_config_dir}/{self.global_config_name}"
        self.global_config_url = (
            f"https://igroman787.github.io/{self.global_config_name}"
        )

    # end define

    @publick
    def pre_up(self):
        self.local.start_thread(self.check_update)

    # end define

    @publick
    def check_update(self):
        git_path = self.get_my_git_path()
        is_update_available = check_git_update(git_path)
        set_check_data(module=self, check_name="update", data=is_update_available)

    # end define

    @publick
    def status(self, args):
        color_print("{cyan}===[ Main status ]==={endc}")
        self.print_module_name()
        self.print_cpu_load()
        self.print_network_load()
        self.print_disks_load()
        self.print_memory_load()
        self.print_service_status()
        self.print_git_hash()

    # end define

    def print_module_name(self):
        module_name = bcolors.yellow_text(self.name)
        text = self.local.translate("module_name").format(module_name)
        print(text)

    # end define

    def print_cpu_load(self):
        cpu_count = psutil.cpu_count()
        cpu_load1, cpu_load5, cpu_load15 = get_load_avg()
        cpu_count_text = bcolors.yellow_text(cpu_count)
        cpu_load1_text = get_color_int(cpu_load1, cpu_count, logic="less")
        cpu_load5_text = get_color_int(cpu_load5, cpu_count, logic="less")
        cpu_load15_text = get_color_int(cpu_load15, cpu_count, logic="less")
        text = self.local.translate("cpu_load").format(
            cpu_count_text, cpu_load1_text, cpu_load5_text, cpu_load15_text
        )
        print(text)

    # end define

    def print_memory_load(self):
        ram = get_ram_info()
        swap = get_swap_info()
        ram_usage_text = get_color_int(ram.usage, 100, logic="less", ending=" Gb")
        ram_usage_percent_text = get_color_int(
            ram.usage_percent, 90, logic="less", ending="%"
        )
        swap_usage_text = get_color_int(swap.usage, 100, logic="less", ending=" Gb")
        swap_usage_percent_text = get_color_int(
            swap.usage_percent, 90, logic="less", ending="%"
        )
        ram_load_text = f"{bcolors.cyan}ram:[{bcolors.default}{ram_usage_text}, {ram_usage_percent_text}{bcolors.cyan}]{bcolors.endc}"
        swap_load_text = f"{bcolors.cyan}swap:[{bcolors.default}{swap_usage_text}, {swap_usage_percent_text}{bcolors.cyan}]{bcolors.endc}"
        text = self.local.translate("memory_load").format(ram_load_text, swap_load_text)
        print(text)

    # end define

    def print_network_load(self):
        borderline_value = 300  # 300 Mbit/s
        statistics_module = get_module_by_name(self.local, "statistics")
        net_load1, net_load5, net_load15 = statistics_module.get_statistics_data(
            "net_load_avg"
        )
        net_load1_text = get_color_int(net_load1, borderline_value, logic="less")
        net_load5_text = get_color_int(net_load5, borderline_value, logic="less")
        net_load15_text = get_color_int(net_load15, borderline_value, logic="less")
        text = self.local.translate("net_load").format(
            net_load1_text, net_load5_text, net_load15_text
        )
        print(text)

    # end define

    def print_disks_load(self):
        borderline_value = 80  # 80%
        statistics_module = get_module_by_name(self.local, "statistics")
        disks_load_avg = statistics_module.get_statistics_data("disks_load_avg")
        disks_load_percent_avg = statistics_module.get_statistics_data(
            "disks_load_percent_avg"
        )

        # Disks status
        disks_load_list = list()
        for name, data in disks_load_avg.items():
            disk_load_text = bcolors.green_text(
                data[2]
            )  # data = 1 minute, 5 minute, 15 minute
            disk_load_percent_text = get_color_int(
                disks_load_percent_avg[name][2],
                borderline_value,
                logic="less",
                ending="%",
            )
            buff = "{}, {}"
            buff = "{}{}:[{}{}{}]{}".format(
                bcolors.cyan, name, bcolors.default, buff, bcolors.cyan, bcolors.endc
            )
            disks_load_buff = buff.format(disk_load_text, disk_load_percent_text)
            disks_load_list.append(disks_load_buff)
        disks_load_data = ", ".join(disks_load_list)
        text = self.local.translate("disks_load").format(disks_load_data)
        print(text)

    # end define

    def print_service_status(self):
        service_status = get_service_status(self.service_name)
        service_uptime = get_service_uptime(self.service_name)
        service_status_color = get_service_status_color(service_status)
        service_uptime_color = bcolors.green_text(time2human(service_uptime))
        text = self.local.translate("service_status_and_uptime").format(
            service_status_color, service_uptime_color
        )
        color_print(text)

    # end define

    def print_git_hash(self):
        git_hash, git_branch = self.get_my_git_hash_and_branch()
        git_hash_text = bcolors.yellow_text(git_hash)
        git_branch_text = bcolors.yellow_text(git_branch)
        text = self.local.translate("git_hash").format(git_hash_text, git_branch_text)
        update_status = get_check_update_status(module=self)
        if update_status:
            text += f", {update_status}"
        print(text)

    # end define

    def get_my_git_hash_and_branch(self):
        git_path = self.get_my_git_path()
        git_hash = get_git_hash(git_path, short=True)
        git_branch = get_git_branch(git_path)
        return git_hash, git_branch

    # end define

    def get_my_git_path(self):
        git_path = self.local.buffer.my_dir
        fix_git_config(git_path)
        return git_path

    # end define

    @publick
    def get_update_args(self, user=None, author=None, repo=None, branch=None, **kwargs):
        try:
            git_path = self.get_my_git_path()
            curr_branch = get_git_branch(git_path)
            curr_author, curr_repo = get_git_author_and_repo(git_path)
        except Exception:
            curr_author = curr_repo = curr_branch = None
        # end try

        author = author or curr_author or self.py_package.author
        repo = repo or curr_repo or self.py_package.repo
        branch = branch or curr_branch or self.py_package.branch
        validate_github_repo(author, repo, branch)

        script_path = f"{self.local.buffer.my_dir}/scripts/update.sh"
        update_args = [
            "bash",
            script_path,
            "-u",
            user,
            "-a",
            author,
            "-r",
            repo,
            "-b",
            branch,
        ]
        return update_args

    # end define

    def install(self, install_args, install_answers):
        # ИЗМЕНЕНО: Используем папку db внутри проекта для базы данных
        mconfig_dir = f"{install_args.src_path}/db"
        mconfig_path = f"{mconfig_dir}/mytonprovider.db"

        # Подготовить папки
        os.makedirs(mconfig_dir, exist_ok=True)
        os.makedirs(self.global_config_dir, exist_ok=True)

        # Скачать глобал конфиг
        subprocess.run(["wget", self.global_config_url, "-O", self.global_config_path])

        # Создать конфиг
        mconfig = Dict()
        mconfig.config = Dict()
        mconfig.config.logLevel = "debug"
        mconfig.config.isLocaldbSaving = True
        mconfig.config.isStartOnlyOneProcess = False
        mconfig.install_args = install_args
        mconfig.install_answers = install_answers

        # Записать конфиг
        write_config_to_file(config_path=mconfig_path, data=mconfig)

        # ИЗМЕНЕНО: Выполняем системные действия только если есть права root
        if os.getuid() == 0:
            subprocess.run(
                [
                    "chown",
                    "-R",
                    install_args.user + ":" + install_args.user,
                    install_args.venv_path,
                    mconfig_dir,
                    self.global_config_dir,
                ]
            )

            start_cmd = f"{install_args.venv_path}/bin/python3 -u {install_args.src_path}/mytonprovider.py"
            start_daemon_cmd = f"{start_cmd} --daemon"
            add2systemd(
                name=self.service_name,
                user=install_args.user,
                start=start_daemon_cmd,
                force=True,
            )

            # Пытаемся создать ссылку в /usr/bin только если это возможно
            file_path = "/usr/bin/mytonprovider"
            file_text = f"{start_cmd} $@"
            try:
                with open(file_path, "wt") as file:
                    file.write(file_text)
                subprocess.run(["chmod", "+x", file_path])
            except PermissionError:
                print(f"Warning: Could not create {file_path}. Skipping.")

    # end define


# end class
