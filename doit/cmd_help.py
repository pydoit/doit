﻿from .exceptions import InvalidDodoFile
from .cmdparse import TaskParse, CmdOption
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

setup:
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
    * key: string with the name of the function argument (used in a python-action)
    * value: tuple of (<task-name>, <variable-name>)

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
   - type [optional] (callable) the option will be converted to this type
   - choices [optional] (list of 2-tuple str) limit option values,
          second tuple element is a help description for value
   - help [optional] (string) description displayed by help command
   - inverse [optional] (string) for a bool parameter set value to False

pos_arg:
 - type: string -> name of the function argument to receive list of positional arguments

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

    def __init__(self, cmds=None, **kwargs):
        self.init_kwargs = kwargs
        super(Help, self).__init__(cmds=cmds, **kwargs)
        self.cmds = cmds.to_dict() # dict name - Command class


    @staticmethod
    def print_usage(cmds):
        """print doit "usage" (basic help) instructions

        :var cmds: dict name -> Command class
        """
        print("doit -- automation tool")
        print("http://pydoit.org")
        print('')
        print("Commands")
        for cmd_name in sorted(cmds.keys()):
            cmd = cmds[cmd_name]
            print("  doit {:16s}  {}".format(
                cmd_name, cmd.doc_purpose))
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
        print("%s  %s" % (task.name, task.doc))
        taskcmd = TaskParse([CmdOption(opt) for opt in task.params])
        for opt in taskcmd.options:
            print("\n".join(opt.help_doc()))
        return True

    def execute(self, params, args):
        """execute cmd 'help' """
        if len(args) != 1:
            self.print_usage(self.cmds)
        elif args[0] == 'task':
            self.print_task_help()
        # help on command
        elif args[0] in self.cmds:
            cmd = self.cmds[args[0]](**self.init_kwargs)
            print(cmd.help())
        else:
            # help of specific task
            try:
                # call base class implementation to execute _execute()
                if not DoitCmdBase.execute(self, params, args):
                    self.print_usage(self.cmds)
            except InvalidDodoFile:
                self.print_usage(self.cmds)
        return 0
