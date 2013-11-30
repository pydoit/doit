"""Definition of stuff that can be used directly by a user in a dodo.py file."""

import sys

from doit.cmd_base import ModuleTaskLoader
from doit.doit_cmd import DoitMain

def run(task_creators):
    """run doit using task_creators

    @param task_creators: module or dict containing task creators
    """
    sys.exit(DoitMain(ModuleTaskLoader(task_creators)).run(sys.argv[1:]))
