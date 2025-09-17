#!/usr/bin/env python3
# -*- coding: utf_8 -*-

import os
import time
import json
import subprocess
from mypylib import (
	MyPyClass,
	Dict,
	bcolors,
	run_as_root,
	color_print,
	print_table,
	get_timestamp,
	timestamp2datetime,
	timeago
)
from speedtest import Speedtest
from decorators import publick
from utils import run_subprocess


class Module():
	def __init__(self, local):
		self.name = "benchmark"
		self.local = local
		self.mandatory = True
		self.daemon_interval = 60
		self.local.add_log(f"{self.name} module init done", "debug")
	#end define

	@publick
	def get_console_commands(self):
		commands = list()

		benchmark = Dict()
		benchmark.cmd = "benchmark"
		benchmark.func = self.run_benchmark
		benchmark.desc = self.local.translate("benchmark_cmd")
		commands.append(benchmark)

		return commands
	#end define

	@publick
	def run_benchmark(self, args):
		if self.is_benchmark_done() and "--force" not in args:
			benchmark = self.local.db.benchmark
			print("last benchmark time:", timeago(benchmark.timestamp))
			print()
			disk = benchmark.disk
			network = benchmark.network
		else:
			disk, network = self.do_benchmark()
		table = list()
		table += [["Test type", "Read speed", "Write speed", "Read iops", "Write iops"]]
		table += [["RND-4K-QD64", disk.qd64.read, disk.qd64.write, disk.qd64.read_iops, disk.qd64.write_iops]]
		table += [["RND-4K-QD1", disk.qd1.read, disk.qd1.write, disk.qd1.read_iops, disk.qd1.write_iops]]
		print_table(table)
		print()
		table = list()
		table += [["Test type", "Download (Mbit/s)", "Upload (Mbit/s)"]]
		table += [["Speedtest", network.download //1024**2, network.upload //1024**2]]
		print_table(table)
	#end define

	def do_benchmark(self):
		self.local.add_log(f"Benchmark is running, it may take about two minutes")
		disk = self.disk_benchmark()
		network = self.network_benchmark()
		self.save_benchmark(disk, network)
		return disk, network
	#end define

	def is_benchmark_done(self):
		life_time = 3600 *24 *7
		if self.local.db.benchmark == None:
			return False
		if self.local.db.benchmark.timestamp + life_time < get_timestamp():
			return False
		return True
	#end define

	@publick
	def daemon(self):
		if self.is_benchmark_done():
			return
		time.sleep(60)
		self.do_benchmark()
	#end define

	def save_benchmark(self, disk, network):
		self.local.add_log("start save_benchmark function", "debug")
		self.local.db.benchmark = Dict()
		self.local.db.benchmark.disk = disk
		self.local.db.benchmark.network = network
		self.local.db.benchmark.timestamp = get_timestamp()
	#end define

	def network_benchmark(self):
		speedtest = Speedtest()

		self.local.add_log("start Speedtest download test", "debug")
		speedtest.download()

		self.local.add_log("start Speedtest upload test", "debug")
		speedtest.upload()
		return Dict(speedtest.results.dict())
	#end define

	def disk_benchmark(self):
		self.local.add_log("start disk_benchmark function", "debug")
		test_path = self.local.db.ton_storage.storage_path
		test_file = f"{test_path}/test.img"

		fio_args = f"fio --name=test --filename={test_file} --runtime=15 --blocksize=4k \
			--ioengine=libaio --direct=1 --size=4G --randrepeat=1 --gtod_reduce=1"
		read_args = f"{fio_args} --readwrite=randread"
		write_args = f"{fio_args} --readwrite=randwrite"
		qd64_read_args = f"{read_args} --iodepth=64"
		qd64_write_args = f"{write_args} --iodepth=64"
		qd1_read_args = f"{read_args} --iodepth=1"
		qd1_write_args = f"{write_args} --iodepth=1"
		
		result = Dict()
		result.qd64 = Dict()
		result.qd1 = Dict()
		result.qd64.name = "RND-4K-QD64"
		result.qd1.name = "RND-4K-QD1"

		self.local.add_log("start RND-4K-QD64 read test", "debug")
		qd64_read_result = run_subprocess(qd64_read_args, timeout=30)

		self.local.add_log("start RND-4K-QD64 write test", "debug")
		qd64_write_result = run_subprocess(qd64_write_args, timeout=30)

		self.local.add_log("start RND-4K-QD1 read test", "debug")
		qd1_read_result = run_subprocess(qd1_read_args, timeout=30)

		self.local.add_log("start RND-4K-QD1 write test", "debug")
		qd1_write_result = run_subprocess(qd1_write_args, timeout=30)

		result.qd64.read, result.qd64.read_iops = self.parse_fio_result(qd64_read_result, mode="read")
		result.qd64.write, result.qd64.write_iops = self.parse_fio_result(qd64_write_result, mode="write")
		result.qd1.read, result.qd1.read_iops = self.parse_fio_result(qd1_read_result, mode="read")
		result.qd1.write, result.qd1.write_iops = self.parse_fio_result(qd1_write_result, mode="write")
		os.remove(test_file)

		return result
	#end define

	def parse_fio_result(self, fio_result, mode):
		if mode not in ["read", "write"]:
			raise Exception(f"parse_fio_result error: unknown mode {mode}")
		#end if

		find_result = fio_result.find(f"{mode}:")
		if find_result < 0:
			raise Exception(f"parse_fio_result error: {mode} not found")
		#end if

		need_line = fio_result[find_result:]
		null, iops_buff, bw_buff, *null = need_line.split(' ')
		null, iops_text = iops_buff.split('=')
		null, bw = bw_buff.split('=')
		iops = iops_text.replace(',', '')
		return bw, iops
	#end define
#end class
