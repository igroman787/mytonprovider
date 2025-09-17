#!/usr/bin/env python3
# -*- coding: utf_8 -*-

import threading
from mypylib import MyPyClass
from utils import (
	import_modules,
	get_module_by_name
)


if __name__ == "__main__":
	local = MyPyClass(__file__)
	#local.run()
	import_modules(local)
	auto_updater_module = get_module_by_name(local, "auto-updater")
	local.cycle(func=auto_updater_module.update_modules, sec=86400, args=None)
#end if
