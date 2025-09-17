#!/usr/bin/env python3
# -*- coding: utf_8 -*-

import os
import psutil
from mypylib import (
	Dict,
	get_timestamp,
	get_internet_interface_name,
	print_table,
	color_print
)
from decorators import publick
from utils import convert_to_required_decimal


class Module():
	def __init__(self, local):
		self.name = "statistics"
		self.local = local
		self.mandatory = True
		self.daemon_interval = 10
		self.init_data()
		self.local.add_log(f"{self.name} module init done", "debug")
	#end define

	def init_data(self):
		self.local.buffer.network = [None]*15*6
		self.local.buffer.diskio = [None]*15*6
	#end define

	def get_statistics_data(self, name):
		life_time = 120 # seconds
		if self.local.db.statistics == None:
			raise Exception("get_statistics_data error: local.db.statistics is None")
		if self.local.db.statistics.timestamp + life_time < get_timestamp():
			raise Exception("get_statistics_data error: local.db.statistics is old")
		#end if

		data = self.local.db.statistics.get(name)
		return data
	#end define

	def get_daily_statistics_data(self, comparing_days):
		if self.local.db.daily_statistics == None:
			raise Exception("get_daily_statistics_data error: local.db.daily_statistics is None")
		#end if

		data = Dict()
		data.bytes_recv = None
		data.bytes_sent = None
		data.bytes_total = None

		days = self.get_days_since_epoch()
		days_str = str(days)
		comparing_days_str = str(days-comparing_days)
		zero_day = self.local.db.daily_statistics.get(days_str)
		comparing_day = self.local.db.daily_statistics.get(comparing_days_str)
		if zero_day == None:
			raise Exception("get_daily_statistics_data error: zero_day is None")
		if comparing_day == None:
			return data
		#end if

		data.recv = convert_to_required_decimal(zero_day.bytes_recv - comparing_day.bytes_recv, decimal_size=3, round_size=2)
		data.sent = convert_to_required_decimal(zero_day.bytes_sent - comparing_day.bytes_sent, decimal_size=3, round_size=2)
		data.total = data.recv + data.sent
		return data
	#end define

	@publick
	def get_console_commands(self):
		commands = list()
		network_status = Dict()
		network_status.cmd = "network_status"
		network_status.func = self.print_network_status
		network_status.desc = self.local.translate("network_status_cmd")
		commands.append(network_status)
		return commands
	#end define

	def print_network_status(self, args):
		net_recv_avg = self.get_statistics_data("net_recv_avg")
		net_sent_avg = self.get_statistics_data("net_sent_avg")
		net_load_avg = self.get_statistics_data("net_load_avg")
		table = [["Network speed", "Download speed", "Upload speed", "Total speed"]]
		table += [["1 minute", f"{net_recv_avg[0]} Mbit/s", f"{net_sent_avg[0]} Mbit/s", f"{net_load_avg[0]} Mbit/s"]]
		table += [["5 minutes", f"{net_recv_avg[1]} Mbit/s", f"{net_sent_avg[1]} Mbit/s", f"{net_load_avg[1]} Mbit/s"]]
		table += [["15 minutes", f"{net_recv_avg[2]} Mbit/s", f"{net_sent_avg[2]} Mbit/s", f"{net_load_avg[2]} Mbit/s"]]
		print_table(table)
		print()

		data1 = self.get_daily_statistics_data(comparing_days=1)
		data7 = self.get_daily_statistics_data(comparing_days=7)
		data30 = self.get_daily_statistics_data(comparing_days=30)
		table = [["Network traffic", "Download bites", "Upload bites", "Total bites"]]
		table += [["1 day", f"{data1.recv} GB", f"{data1.sent} GB", f"{data1.total} GB"]]
		table += [["7 days", f"{data7.recv} GB", f"{data7.sent} GB", f"{data7.total} GB"]]
		table += [["30 days", f"{data30.recv} GB", f"{data30.sent} GB", f"{data30.total} GB"]]
		print_table(table)
	#end define

	@publick
	def daemon(self):
		self.read_network_data()
		self.save_network_statistics()
		self.read_disk_data()
		self.save_disk_statistics()
	#end define

	def read_disk_data(self):
		timestamp = get_timestamp()
		disks = self.get_disks_list()
		buff = psutil.disk_io_counters(perdisk=True)
		data = dict()
		for name in disks:
			data[name] = Dict()
			data[name].timestamp = timestamp
			data[name].busy_time = buff[name].busy_time
			data[name].read_bytes = buff[name].read_bytes
			data[name].write_bytes = buff[name].write_bytes
			data[name].read_count = buff[name].read_count
			data[name].write_count = buff[name].write_count
		#end for

		self.local.buffer.diskio.pop(0)
		self.local.buffer.diskio.append(data)
		#print("read_disk_data:", data)
	#end define

	def save_disk_statistics(self):
		data = self.local.buffer.diskio
		data = data[::-1]
		zerodata = data[0]
		buff1 = data[1*6-1]
		buff5 = data[5*6-1]
		buff15 = data[15*6-1]
		if buff5 is None:
			buff5 = buff1
		if buff15 is None:
			buff15 = buff5
		#end if

		disks_load_avg = dict()
		disks_load_percent_avg = dict()
		iops_avg = dict()
		disks = self.get_disks_list()
		for name in disks:
			if zerodata[name].busy_time == 0:
				continue
			disk_load1, disk_load_percent1, iops1 = self.calculate_disk_statistics(zerodata, buff1, name)
			disk_load5, diskLoadPercent5, iops5 = self.calculate_disk_statistics(zerodata, buff5, name)
			disk_load15, diskLoadPercent15, iops15 = self.calculate_disk_statistics(zerodata, buff15, name)
			disks_load_avg[name] = [disk_load1, disk_load5, disk_load15]
			disks_load_percent_avg[name] = [disk_load_percent1, diskLoadPercent5, diskLoadPercent15]
			iops_avg[name] = [iops1, iops5, iops15]
			#print(name, "disks_load_avg:", disks_load_avg)
			#print(name, "disks_load_percent_avg:", disks_load_percent_avg)
			#print(name, "iops_avg:", iops_avg)
		#end fore

		# save statistics
		statistics = self.local.db.get("statistics", Dict())
		statistics.timestamp = get_timestamp()
		statistics.disks_load_avg = disks_load_avg
		statistics.disks_load_percent_avg = disks_load_percent_avg
		statistics.iops_avg = iops_avg
		self.local.db.statistics = statistics
	#end define

	def calculate_disk_statistics(self, zerodata, data, name):
		if data is None:
			return None, None, None
		data = data[name]
		zerodata = zerodata[name]
		time_diff = zerodata.timestamp - data.timestamp
		busy_time_diff = zerodata.busy_time - data.busy_time
		disk_read_diff = zerodata.read_bytes - data.read_bytes
		disk_write_diff = zerodata.write_bytes - data.write_bytes
		disk_read_count_diff = zerodata.read_count - data.read_count
		disk_write_count_diff = zerodata.write_count - data.write_count
		disk_load_percent = busy_time_diff /1000 /time_diff *100  # /1000 - to second, *100 - to percent
		disk_load_percent = round(disk_load_percent, 2)
		disk_read = disk_read_diff /time_diff
		disk_write = disk_write_diff /time_diff
		disk_read_count = disk_read_count_diff /time_diff
		disk_write_count = disk_write_count_diff /time_diff
		disk_load = convert_to_required_decimal(disk_read + disk_write, decimal_size=2, round_size=2)
		iops = round(disk_read_count + disk_write_count, 2)
		return disk_load, disk_load_percent, iops
	#end define

	def get_disks_list(self):
		data = list()
		buff = os.listdir("/sys/block/")
		for item in buff:
			if "loop" in item:
				continue
			data.append(item)
		#end for
		data.sort()
		return data
	#end define

	def read_network_data(self):
		timestamp = get_timestamp()
		interface_name = get_internet_interface_name()
		buff = psutil.net_io_counters(pernic=True)
		buff = buff[interface_name]
		data = Dict()
		data.timestamp = timestamp
		data.bytes_recv = buff.bytes_recv
		data.bytes_sent = buff.bytes_sent
		data.packets_sent = buff.packets_sent
		data.packets_recv = buff.packets_recv

		self.local.buffer.network.pop(0)
		self.local.buffer.network.append(data)
		#print("read_network_data:", data)
	#end define

	def save_network_statistics(self):
		data = self.local.buffer.network
		data = data[::-1]
		zerodata = data[0]
		buff1 = data[1*6-1]
		buff5 = data[5*6-1]
		buff15 = data[15*6-1]
		if buff5 is None:
			buff5 = buff1
		if buff15 is None:
			buff15 = buff5
		#end if

		net_recv_avg1, net_sent_avg1, networkLoadAvg1, ppsAvg1 = self.calculate_network_statistics(zerodata, buff1)
		net_recv_avg5, net_sent_avg5, networkLoadAvg5, ppsAvg5 = self.calculate_network_statistics(zerodata, buff5)
		net_recv_avg15, net_sent_avg15, networkLoadAvg15, ppsAvg15 = self.calculate_network_statistics(zerodata, buff15)
		net_recv_avg = [net_recv_avg1, net_recv_avg5, net_recv_avg15]
		net_sent_avg = [net_sent_avg1, net_sent_avg5, net_sent_avg15]
		net_load_avg = [networkLoadAvg1, networkLoadAvg5, networkLoadAvg15]
		pps_avg = [ppsAvg1, ppsAvg5, ppsAvg15]

		# save statistics
		statistics = self.local.db.get("statistics", Dict())
		statistics.timestamp = get_timestamp()
		statistics.net_recv_avg = net_recv_avg
		statistics.net_sent_avg = net_sent_avg
		statistics.net_load_avg = net_load_avg
		statistics.pps_avg = pps_avg
		statistics.bytes_recv = zerodata.bytes_recv
		statistics.bytes_sent = zerodata.bytes_sent
		self.local.db.statistics = statistics

		# save daily statistics
		daily_statistics = self.local.db.get("daily_statistics", dict())
		data = Dict()
		data.timestamp = get_timestamp()
		data.bytes_recv = zerodata.bytes_recv
		data.bytes_sent = zerodata.bytes_sent
		days_since_epoch = self.get_days_since_epoch()
		days_since_epoch_str = str(days_since_epoch)
		daily_statistics[days_since_epoch_str] = data
		self.local.db.daily_statistics = daily_statistics

		# delete old daily statistics
		daily_statistics_len = len(self.local.db.daily_statistics)
		if daily_statistics_len > 365:
			for i in range(365, daily_statistics_len):
				i_str = str(i)
				del self.local.db.daily_statistics[i_str]
	#end define

	def get_days_since_epoch(self):
		now = get_timestamp()
		days_since_epoch = now //86400
		return days_since_epoch
	#end define

	def calculate_network_statistics(self, zerodata, data):
		if data is None:
			return None, None, None, None
		time_diff = zerodata.timestamp - data.timestamp
		bytes_recv_diff = zerodata.bytes_recv - data.bytes_recv
		bytes_sent_diff = zerodata.bytes_sent - data.bytes_sent
		packets_recv_diff = zerodata.packets_recv - data.packets_recv
		packets_sent_diff = zerodata.packets_sent - data.packets_sent
		bits_recv_avg = bytes_recv_diff /time_diff *8
		bits_sent_avg = bytes_sent_diff /time_diff *8
		packets_recv_avg = packets_recv_diff /time_diff
		packets_sent_avg = packets_sent_diff /time_diff
		net_recv_avg = convert_to_required_decimal(bits_recv_avg, decimal_size=2, round_size=2)
		net_sent_avg = convert_to_required_decimal(bits_sent_avg, decimal_size=2, round_size=2)
		net_load_avg = convert_to_required_decimal(bits_recv_avg + bits_sent_avg, decimal_size=2, round_size=2)
		pps_avg = round(packets_recv_avg + packets_sent_avg, 2)
		return net_recv_avg, net_sent_avg, net_load_avg, pps_avg
	#end define
#end class
