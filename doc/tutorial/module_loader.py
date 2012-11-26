#! /usr/bin/env python

import sys

from doit.cmd_base import ModuleTaskLoader
from doit.doit_cmd import DoitMain

if __name__ == "__main__":
    import my_module_with_tasks
    sys.exit(DoitMain(ModuleTaskLoader(my_module_with_tasks)).run(sys.argv[1:]))
