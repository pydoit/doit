from operator import attrgetter
import six

from .exceptions import InvalidDodoFile
from .cmd_base import DoitCmdBase


HELP_TASK = """

Task Dictionary parameters
--------------------------

Tasks are defined by functions starting with the string ``task_``. It must return a dictionary describing the task with the following fields:

actions [required]:
  - type: Python-Task -> callable or tuple (callable, `*args`, `**kwargs`)
  - type: Cmd-Task -> string or list of strings (each item is a different command). to be executed by shell.
  - type: Group-Task -> None.

basename:
  - type: string. if present use it as task name instead of taking name from python function

name [required for sub-task]:
  - type: string. sub-task identifier

file_dep:
  - type: list. items:
    * file (string) path relative to the dodo file

task_dep:
  - type: list. items:
    * task name (string)

targets:
  - type: list of strings
  - each item is file-path relative to the dodo file (accepts both files and folders)

uptodate:
  - type: list. items:
    * None - None values are just ignored
    * bool - False indicates task is not up-to-date
    * callable - returns bool or None. must take 2 positional parameters (task, values)

calc_dep:
  - type: list. items:
    * task name (string)

getargs:
  - type: dictionary
    * key: string with the name of the function parater (used in a python-action)
    * value: tuple of (<task-name>, <variable-name>)

setup:
 - type: list. items:
   * task name (string)

teardown:
 - type: (list) of actions (see above)

doc:
 - type: string -> the description text

clean:
 - type: (True bool) remove target files
 - type: (list) of actions (see above)

params:
 - type: (list) of dictionaries containing:
   - name [required] (string) parameter identifier
   - default [required] default value for parameter
   - short [optional] (string - 1 letter) short option string
   - long [optional] (string) long option string
   - type [optional] the option will be converted to this type

verbosity:
 - type: int
   -  0: capture (do not print) stdout/stderr from task.
   -  1: (default) capture stdout only.
   -  2: do not capture anything (print everything immediately).

title:
 - type: callable taking one parameter as argument (the task reference)

watch:
 - type: list. items:
   * (string) path to be watched when using the `auto` command
"""



class Help(DoitCmdBase):
    doc_purpose = "show help"
    doc_usage = "[TASK] [COMMAND]"
    doc_description = None

    @staticmethod
    def print_usage(cmds):
        """print doit "usage" (basic help) instructions"""
        print("doit -- automation tool")
        print("http://pydoit.org")
        print('')
        print("Commands")
        for cmd in sorted(six.itervalues(cmds), key=attrgetter('name')):
            six.print_("  doit %s \t\t %s" % (cmd.name, cmd.doc_purpose))
        print("")
        print("  doit help              show help / reference")
        print("  doit help task         show help on task dictionary fields")
        print("  doit help <command>    show command usage")
        print("  doit help <task-name>  show task usage")

    @staticmethod
    def print_task_help():
        """print help for 'task' usage """
        print(HELP_TASK)

    def _execute(self, pos_args):
        """execute help for specific task"""
        task_name = pos_args[0]
        tasks = dict([(t.name, t) for t in self.task_list])
        task = tasks.get(task_name, None)
        if not task:
            return False
        six.print_("%s  %s" % (task.name, task.doc))
        for opt in task.taskcmd.options:
            six.print_("\n".join(opt.help_doc()))
        return True

    def execute(self, params, args):
        """execute cmd 'help' """
        cmds = self.doit_app.sub_cmds
        if len(args) != 1:
            self.print_usage(cmds)
        elif args[0] == 'task':
            self.print_task_help()
        # help on command
        elif args[0] in cmds:
            six.print_(cmds[args[0]].help())
        else:
            # help of specific task
            try:
                if not DoitCmdBase.execute(self, params, args):
                    self.print_usage(cmds)
            except InvalidDodoFile:
                self.print_usage(cmds)
        return 0
