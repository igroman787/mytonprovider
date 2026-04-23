#!/usr/bin/env python3
# -*- coding: utf_8 -*-

import os
import shutil
import base64
import requests
from random import randint
from mypylib import (
    Dict,
    bcolors,
    color_print,
    add2systemd,
    read_config_from_file,
    write_config_to_file,
    get_own_ip,
    get_git_hash,
    get_git_branch,
    print_table,
    get_service_status,
    get_service_uptime,
    time2human,
    check_git_update,
    get_git_author_and_repo,
    get_timestamp,
    timeago,
)

from utils import (
    get_module_by_name,
    get_disk_space,
    convert_to_required_decimal,
    fix_git_config,
    reduct,
    get_service_status_color,
    get_check_port_status,
    set_check_data,
    get_check_update_status,
    run_subprocess,
    validate_github_repo,
)
from decorators import publick
from adnl_over_udp_checker import check_adnl_connection


class Module:
    def __init__(self, local):
        self.name = "ton-storage"
        self.service_name = self.name
        self.local = local
        self.mandatory = False
        self.local.add_log(f"{self.name} module init done", "debug")

        self.go_package = Dict()
        self.go_package.author = "xssnick"
        self.go_package.repo = "tonutils-storage"
        self.go_package.branch = "master"
        self.go_package.entry_point = "cli/main.go"

        self.daemon_interval = 86400
        self.extra_daemons = [
            Dict(
                name="ton-storage-verify",
                func=self.verify_daemon,
                interval=600,
            ),
        ]

    # end define

    @publick
    def daemon(self):
        """Remove BAGs that the provider process did not removed"""
        api_data = self.get_api_data()
        bags_list = self.get_bags_list(api_data)
        bags_dir = f"{self.local.db.ton_storage.storage_path}/provider"
        for bag_id in os.listdir(bags_dir):
            if len(bag_id) != 64:
                continue
            if bag_id not in bags_list:
                self.local.add_log(
                    f"Cleaning up old BAGs: {bags_dir}/{bag_id}", "warning"
                )
                shutil.rmtree(f"{bags_dir}/{bag_id}")

    # end define

    def verify_daemon(self):
        try:
            bag_id = self.get_next_bag_to_verify()
            if bag_id is None:
                return
            self.local.add_log(f"Verifying BAG: {bag_id}", "debug")
            result = self.do_verify_bag(bag_id)
            self.save_verify_result(bag_id, result)
        except Exception as ex:
            self.local.add_log(f"verify_daemon error: {ex}", "error")

    # end define

    @publick
    def is_enabled(self):
        git_path = self.get_my_git_path()
        try:
            get_git_branch(git_path)
            return True
        except:
            return False

    # end define

    def is_enabled_old(self):
        if "ton_storage" in self.local.db:
            return True
        return False

    # end define

    @publick
    def get_console_commands(self):
        commands = list()
        bags_list = Dict()
        bags_list.cmd = "bags_list"
        bags_list.func = self.print_bags_list
        bags_list.desc = self.local.translate("bags_list_cmd")
        commands.append(bags_list)

        verify_bag = Dict()
        verify_bag.cmd = "verify_bag"
        verify_bag.func = self.cmd_verify_bag
        verify_bag.desc = self.local.translate("verify_bag_cmd")
        commands.append(verify_bag)

        storage_log = Dict()
        storage_log.cmd = "storage_log"
        storage_log.func = self.cmd_storage_log
        storage_log.desc = self.local.translate("storage_log_cmd")
        commands.append(storage_log)

        return commands

    # end define

    @publick
    def pre_up(self):
        self.local.start_thread(self.check_update)
        self.local.start_thread(self.check_port)

    # end define

    def check_update(self):
        git_path = self.get_my_git_path()
        is_update_available = check_git_update(git_path)
        set_check_data(module=self, check_name="update", data=is_update_available)

    # end define

    def check_port(self):
        try:
            ton_storage = self.local.db.ton_storage
            if ton_storage is None:
                return

            storage_config = self.get_storage_config()
            if storage_config is None or not hasattr(storage_config, "Key"):
                return

            storage_pubkey = self.get_storage_pubkey()
            listen_ip, storage_port = storage_config.ListenAddr.split(":")

            own_ip = get_own_ip()
            if storage_config.ExternalIP != own_ip:
                return

            result, status = check_adnl_connection(own_ip, storage_port, storage_pubkey)
            set_check_data(module=self, check_name="port", data=result)
        except Exception:
            pass

    # end define

    def get_storage_config(self):
        ton_storage = self.local.db.ton_storage
        storage_config = read_config_from_file(ton_storage.config_path)
        return storage_config

    # end define

    def get_storage_pubkey(self):
        storage_config = self.get_storage_config()
        storage_bytes = base64.b64decode(storage_config.Key)
        storage_pubkey_bytes = storage_bytes[32:64]
        storage_pubkey = storage_pubkey_bytes.hex().upper()
        return storage_pubkey

    # end define

    @publick
    def status(self, args):
        color_print("{cyan}===[ Local storage status ]==={endc}")
        self.print_module_name()
        self.print_bags_num()
        self.print_disk_space()
        self.print_port_status()
        self.print_service_status()
        self.print_git_hash()

    # end define

    def print_module_name(self):
        module_name = bcolors.yellow_text(self.name)
        text = self.local.translate("module_name").format(module_name)
        print(text)

    # end define

    def print_bags_num(self):
        api_data = self.get_api_data()
        bags_num = self.get_bags_num(api_data)
        used_provider_space = self.get_bags_size(api_data, decimal_size=3, round_size=2)
        bags_num_text = bcolors.green_text(bags_num)
        used_provider_space_text = bcolors.green_text(used_provider_space)  # TODO
        text = self.local.translate("bags_num").format(
            bags_num_text, used_provider_space_text
        )
        print(text)

    # end define

    def print_disk_space(self):
        ton_storage = self.local.db.ton_storage
        total_disk_space, used_disk_space, free_disk_space = get_disk_space(
            ton_storage.storage_path, decimal_size=3, round_size=2
        )
        used_disk_space_text = bcolors.green_text(used_disk_space)  # TODO
        total_disk_space_text = bcolors.yellow_text(total_disk_space)
        text = self.local.translate("disk_space").format(
            used_disk_space_text, total_disk_space_text
        )
        print(text)

    # end define

    def print_port_status(self):
        storage_config = self.get_storage_config()
        listen_ip, storage_port = storage_config.ListenAddr.split(":")
        port_color = bcolors.yellow_text(storage_port, " udp")
        status = get_check_port_status(module=self)
        text = self.local.translate("port_status").format(port_color, status)
        color_print(text)

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

    def get_api_data(self):
        api = self.local.db.ton_storage.api
        api_url = f"http://{api.host}:{api.port}/api/v1/list"
        resp = requests.get(api_url, timeout=0.3)
        if resp.status_code != 200:
            raise Exception(f"Failed to get provider api data from {api_url}")
        return Dict(resp.json())

    # end define

    def get_bags_num(self, api_data):
        if api_data.bags == None:
            return 0
        return len(api_data.bags)

    # end define

    def get_bags_list(self, api_data):
        result = list()
        if api_data.bags == None:
            return result
        for bag in api_data.bags:
            result.append(bag.bag_id)
        return result

    # end define

    def get_bags_size(self, api_data, decimal_size, round_size):
        if api_data.bags == None:
            return 0
        used = 0
        for bag in api_data.bags:
            used += bag.size
        used_space = convert_to_required_decimal(used, decimal_size, round_size)
        return used_space

    # end define

    def get_my_git_hash_and_branch(self):
        git_path = self.get_my_git_path()
        git_hash = get_git_hash(git_path, short=True)
        git_branch = get_git_branch(git_path)
        return git_hash, git_branch

    # end define

    def get_my_git_path(self):
        # ton_storage = self.local.db.ton_storage
        # git_path = f"{ton_storage.src_dir}/{self.go_package.repo}"
        git_path = f"/usr/src/{self.go_package.repo}"
        fix_git_config(git_path)
        return git_path

    # end define

    def get_next_bag_to_verify(self):
        api_data = self.get_api_data()
        bags_list = self.get_bags_list(api_data)
        if not bags_list:
            return None

        bags_verify_state = self.get_bags_verify_state()
        now = get_timestamp()

        oldest_bag_id = None
        oldest_time = now

        for bag_id in bags_list:
            bag_id = bag_id.upper()
            last_verified = bags_verify_state.get(bag_id, 0)
            # Проверяем, что с момента последней проверки прошло ≥ 30 дней
            if now - last_verified >= 30 * 86400:
                if last_verified < oldest_time:
                    oldest_time = last_verified
                    oldest_bag_id = bag_id

        return oldest_bag_id

    # end define

    def get_bags_verify_state(self):
        if self.local.db.ton_storage is None:
            return dict()
        return self.local.db.ton_storage.get("bags_verify_state", dict())

    # end define

    def save_verify_result(self, bag_id, result):
        if self.local.db.ton_storage is None:
            return
        if self.local.db.ton_storage.bags_verify_state is None:
            self.local.db.ton_storage.bags_verify_state = dict()

        now = get_timestamp()
        bag_id = bag_id.upper()
        self.local.db.ton_storage.bags_verify_state[bag_id] = now

        if result:
            self.local.add_log(f"BAG {bag_id} verified OK", "info")
        else:
            self.local.add_log(
                f"BAG {bag_id} verification FAILED, redownload started", "warning"
            )

    # end define

    def do_verify_bag(self, bag_id):
        api = self.local.db.ton_storage.api
        api_url = f"http://{api.host}:{api.port}/api/v1/verify"
        data = {"bag_id": bag_id}
        resp = requests.post(api_url, json=data, timeout=60)
        if resp.status_code != 200:
            try:
                resp_data = resp.json()
                error = resp_data.get("error", "unknown error")
            except:
                error = resp.text
            raise Exception(
                f"Failed to verify bag {bag_id}: HTTP {resp.status_code} ({error})"
            )
        result = resp.json()
        return result.get("ok", False)

    # end define

    def cmd_verify_bag(self, args):
        try:
            bag_id = args[0].upper()
        except:
            color_print("{red}Bad args. Usage:{endc} verify_bag <bag_id>")
            return

        if len(bag_id) != 64:
            color_print("{red}Error: bag_id must be 64 characters{endc}")
            return

        color_print(f"Verifying BAG: {{yellow}}{bag_id}{{endc}}")
        try:
            result = self.do_verify_bag(bag_id)
            self.save_verify_result(bag_id, result)
            if result:
                color_print("{green}BAG verified OK - files are intact{endc}")
            else:
                color_print(
                    "{yellow}BAG verification failed - redownload started{endc}"
                )
        except Exception as ex:
            color_print(f"{{red}}Error: {ex}{{endc}}")

    # end define

    def set_log_level(self, verbosity):
        api = self.local.db.ton_storage.api
        api_url = f"http://{api.host}:{api.port}/api/v1/logger"
        data = {"verbosity": verbosity}
        resp = requests.post(api_url, json=data, timeout=3)
        if resp.status_code != 200:
            raise Exception(f"Failed to set log level: HTTP {resp.status_code}")
        return True

    # end define

    def cmd_storage_log(self, args):
        try:
            verbosity = int(args[0])
        except:
            color_print("{red}Bad args. Usage:{endc} storage_log <verbosity>")
            color_print("Verbosity: 0-1=error, 2=info, 3-10=debug, 11-13=debug+loggers")
            return

        if verbosity < 0 or verbosity > 13:
            color_print("{red}Error: verbosity must be 0-13{endc}")
            return

        try:
            self.set_log_level(verbosity)
            color_print(f"ton-storage log level set to {{green}}{verbosity}{{endc}}")
        except Exception as ex:
            color_print(f"{{red}}Error: {ex}{{endc}}")

    # end define

    @publick
    def print_bags_list(self, args):
        api_data = self.get_api_data()
        if api_data.bags == None:
            print("no data")
            return
        bags_verify_state = self.get_bags_verify_state()
        table = [
            [
                "Bag id",
                "Progress",
                "Size",
                "Files",
                "Peers",
                "Download speed",
                "Upload speed",
                "Last verified",
            ]
        ]
        for bag in api_data.bags:
            bag_id = reduct(bag.bag_id)
            progress = self.get_progress(bag)
            size = convert_to_required_decimal(bag.size, decimal_size=3, round_size=2)
            download_speed = convert_to_required_decimal(
                bag.download_speed, decimal_size=2, round_size=2
            )
            upload_speed = convert_to_required_decimal(
                bag.upload_speed, decimal_size=2, round_size=2
            )
            progress_text = f"{progress}%"
            size_text = f"{size} GB"
            download_speed_text = f"{download_speed} MB/s"
            upload_speed_text = f"{upload_speed} MB/s"
            last_verified = bags_verify_state.get(bag.bag_id.upper(), 0)
            if last_verified == 0:
                last_verified_text = "never"
            else:
                last_verified_text = timeago(last_verified)
            table += [
                [
                    bag_id,
                    progress_text,
                    size_text,
                    bag.files_count,
                    bag.peers,
                    download_speed_text,
                    upload_speed_text,
                    last_verified_text,
                ]
            ]
        print_table(table)

    # end define

    def get_progress(self, bag):
        if bag.size == 0:
            return 0
        progress = round(bag.downloaded / bag.size * 100, 2)
        return progress

    # end define

    @publick
    def get_update_args(
        self,
        user=None,
        author=None,
        repo=None,
        branch=None,
        restart_service=False,
        **kwargs,
    ):
        try:
            git_path = self.get_my_git_path()
            curr_branch = get_git_branch(git_path)
            curr_author, curr_repo = get_git_author_and_repo(git_path)
        except Exception:
            curr_author = curr_repo = curr_branch = None
        # end try

        author = author or curr_author or self.go_package.author
        repo = repo or curr_repo or self.go_package.repo
        branch = branch or curr_branch or self.go_package.branch
        validate_github_repo(author, repo, branch)

        script_path = f"{self.local.buffer.my_dir}/scripts/install_go_package.sh"
        update_args = [
            "bash",
            script_path,
            "-a",
            author,
            "-r",
            repo,
            "-b",
            branch,
            "-e",
            self.go_package.entry_point,
        ]
        if restart_service == True:
            update_args += ["-s", self.service_name]
        return update_args

    # end define

    def install(self, install_args, install_answers):
        # install_args: user, src_dir, bin_dir, venvs_dir, venv_path, src_path
        host = "localhost"
        udp_port = randint(1024, 65000)
        api_port = randint(1024, 65000)

        mconfig_dir = f"/home/{install_args.user}/.local/share/mytonprovider"
        mconfig_path = f"{mconfig_dir}/mytonprovider.db"
        db_dir = f"{install_answers.storage_path}/db"
        storage_config_path = f"{db_dir}/config.json"

        # Склонировать исходники и скомпилировать бинарники
        upgrade_args = self.get_update_args(install_args.src_path)
        run_subprocess(upgrade_args, timeout=600)

        # Подготовить папку
        os.makedirs(install_answers.storage_path, exist_ok=True)
        chown_args = [
            "chown",
            install_args.user + ":" + install_args.user,
            install_answers.storage_path,
        ]
        run_subprocess(chown_args, timeout=3)

        # Создать службу
        main_module = get_module_by_name(self.local, "main")
        bin_path = f"{install_args.bin_dir}/{self.go_package.repo}"
        if not os.path.exists(bin_path):
            bin_path = f"/usr/bin/{self.go_package.repo}"

        start_cmd = f"{bin_path} --db {db_dir} --config {storage_config_path}"
        add2systemd(
            name=self.service_name,
            user=install_args.user,
            start=start_cmd,
            workdir=install_answers.storage_path,
            force=True,
        )
        if not os.path.exists(storage_config_path):
            os.makedirs(os.path.dirname(storage_config_path), exist_ok=True)
            default_config = {
                "ListenAddr": "0.0.0.0:10000",
                "ExternalIP": "127.0.0.1",
                "MinSpan": 3600,
                "MaxSpan": 3600,
                "MinRatePerMBDay": "0.0",
                "MaxBagSizeBytes": 1024,
                "Storages": [
                    {"BaseURL": "http://127.0.0.1", "SpaceToProvideMegabytes": 1024}
                ],
                "CRON": {"Enabled": False},
            }
            write_config_to_file(storage_config_path, default_config)

        # Первый запуск - создание конфига
        self.local.start_service(self.service_name, sleep=10)
        self.local.stop_service(self.service_name)

        # read storage config
        storage_config = read_config_from_file(storage_config_path)

        # edit storage config
        storage_config.ListenAddr = f"0.0.0.0:{udp_port}"
        storage_config.ExternalIP = get_own_ip()

        # write storage config
        write_config_to_file(config_path=storage_config_path, data=storage_config)

        # read mconfig
        mconfig = read_config_from_file(mconfig_path)

        # edit mconfig config
        ton_storage = Dict()
        ton_storage.storage_path = install_answers.storage_path
        ton_storage.src_dir = install_args.src_dir
        if not hasattr(mconfig, "ton_storage") or mconfig.ton_storage is None:
            mconfig.ton_storage = Dict()
        ton_storage.config_path = storage_config_path

        api = Dict()
        api.host = host
        api.port = api_port

        ton_storage.api = api
        mconfig.ton_storage = ton_storage

        # write mconfig
        write_config_to_file(config_path=mconfig_path, data=mconfig)

        # start service
        self.local.start_service(self.service_name)

    # end define


# end class
