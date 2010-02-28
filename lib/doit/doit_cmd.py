import os
import sys
import traceback

import doit
from doit import main
from doit import task
from doit import cmdparse
from doit.cmds import doit_run, doit_clean, doit_list, doit_forget, doit_ignore


## cmd line options
##########################################################
########## run
# print version and exit
opt_version = {'name': 'version',
               'short':'',
               'long': 'version',
               'type': bool,
               'default': False,
               'help': "show version"
               }

# display cmd line usage
opt_help = {'name': 'help',
            'short':'',
            'long': 'help',
            'type': bool,
            'default': False,
            'help':"show help"
            }

# select dodo file containing tasks
opt_dodo = {'name': 'dodoFile',
            'short':'f',
            'long': 'file',
            'type': str,
            'default': 'dodo.py',
            'help':"load task from dodo FILE [default: %(default)s]"
            }

# cwd
opt_cwd = {'name': 'cwdPath',
           'short':'d',
           'long': 'dir',
           'type': str,
           'default': None,
           'help':("set path to be used as cwd directory (file paths on " +
                   "dodo file are relative to dodo.py location.")
           }

# select output file
opt_outfile = {'name': 'outfile',
            'short':'o',
            'long': 'output-file',
            'type': str,
            'default': sys.stdout,
            'help':"write output into file [default: stdout]"
            }


# choose internal dependency file.
opt_depfile = {'name': 'dep_file',
               'short':'',
               'long': '',
               'type': str,
               'default': ".doit.db",
               'help': "file used to save successful runs"
               }

# always execute task
opt_always = {'name': 'always',
              'short': 'a',
              'long': 'always-execute',
              'type': bool,
              'default': False,
              'help': "always execute tasks even if up-to-date [default: "
                      "%(default)s]"
              }

# continue executing tasks even after a failure
opt_continue = {'name': 'continue',
                'short': 'c',
                'long': 'continue',
                'type': bool,
                'default': False,
                'help': "continue executing tasks even after a failure "
                        "[default: %(default)s]"
                }

# verbosity
opt_verbosity = {'name':'verbosity',
                 'short':'v',
                 'long':'verbosity',
                 'type':int,
                 'default': None,
                 'help':
"""0 capture (do not print) stdout/stderr from task.
1 capture stdout only.
2 do not capture anything (print everything immediately).
[default: 1]"""
                 }

# reporter
opt_reporter = {'name':'reporter',
                 'short':'r',
                 'long':'reporter',
                 'type':str, #TODO type choice
                 'default': 'default',
                 'help':
"""Choose output reporter. Available:
'default': report output on console
'executed-only': no output for skipped (up-to-date) and group tasks
'json': output result in json format
"""
                 }



run_doc = {'purpose': "run tasks",
           'usage': "[TASK/TARGET...]",
           'description': None}

def print_version():
    print ".".join([str(i) for i in doit.__version__])
    print "bin @", os.path.abspath(__file__)
    print "lib @", os.path.dirname(os.path.abspath(doit.__file__))

def print_usage():
    # TODO cmd list should be automatically generated.
    print """
doit -- automation tool
http://python-doit.sourceforge.net/

Commands:
 doit [run]             run tasks
 doit clean             clean action / remove targets
 doit list              list tasks from dodo file
 doit forget            clear successful run status from DB
 doit ignore            ignore task (skip) on subsequent runs

 doit help              show help / reference
 doit help task         show help on task dictionary fields
 doit help <command>    show command usage
"""


def cmd_run(params, args):
    """execute cmd run"""

    # special parameters that dont run anything
    if params["version"]:
        print_version()
        return 0
    if params["help"]:
        print_usage()
        return 0


    # check if command is "run". default command is "run"
    if len(args) == 0 or args[0] not in params['sub']:
        dodo_module = main.get_module(params['dodoFile'], params['cwdPath'])
        command_names = params['sub'].keys()
        dodo_tasks = main.load_task_generators(dodo_module, command_names)
        options = args or dodo_tasks['default_tasks']
        return doit_run(params['dep_file'], dodo_tasks['task_list'],
                        params['outfile'], options, params['verbosity'],
                        params['always'], params['continue'],
                        params['reporter'])

    # sub cmd different from "run" on cmd line. parse arguments again
    commands = params['sub']
    sub_cmd = args.pop(0)
    return commands[sub_cmd](args, **params)



##########################################################
########## list

list_doc = {'purpose': "list tasks from dodo file",
            'usage': "[TASK ...]",
            'description': None}

opt_listall = {'name': 'all',
               'short':'',
               'long': 'all',
               'type': bool,
               'default': False,
               'help': "list include all sub-tasks from dodo file"
               }

opt_list_quiet = {'name': 'quiet',
                  'short': 'q',
                  'long': 'quiet',
                  'type': bool,
                  'default': False,
                  'help': 'print just task name (less verbose than default)'}

opt_list_status = {'name': 'status',
                   'short': 's',
                   'long': 'status',
                   'type': bool,
                   'default': False,
                   'help': 'print task status (R)un, (U)p-to-date, (I)gnored'}

# TODO list should support "args" as a filter.
def cmd_list(params, args):
    dodo_module = main.get_module(params['dodoFile'], params['cwdPath'])
    command_names = params['sub'].keys()
    dodo_tasks = main.load_task_generators(dodo_module, command_names)
    return doit_list(params['dep_file'], dodo_tasks['task_list'], sys.stdout,
                     args, params['all'], params['quiet'], params['status'])

##########################################################
########## clean


clean_doc = {'purpose': "clean action / remove targets",
             'usage': "[TASK ...]",
             'description': None}

opt_clean_dryrun = {'name': 'dryrun',
                    'short': 'n', # like make dry-run
                    'long': 'dry-run',
                    'type': bool,
                    'default': False,
                    'help': 'print actions without really executing them'}

def cmd_clean(params, args):
    dodo_module = main.get_module(params['dodoFile'], params['cwdPath'])
    command_names = params['sub'].keys()
    dodo_tasks = main.load_task_generators(dodo_module, command_names)
    return doit_clean(dodo_tasks['task_list'], sys.stdout, params['dryrun'],
                      args)


##########################################################
########## forget

forget_doc = {'purpose': "clear successful run status from internal DB",
              'usage': "[TASK ...]",
              'description': None}

def cmd_forget(params, args):
    dodo_module = main.get_module(params['dodoFile'], params['cwdPath'])
    command_names = params['sub'].keys()
    dodo_tasks = main.load_task_generators(dodo_module, command_names)
    return doit_forget(params['dep_file'], dodo_tasks['task_list'],
                       sys.stdout, args)


##########################################################
########## ignore

ignore_doc = {'purpose': "ignore task (skip) on subsequent runs",
              'usage': "TASK [TASK ...]",
              'description': None}

def cmd_ignore(params, args):
    dodo_module = main.get_module(params['dodoFile'], params['cwdPath'])
    command_names = params['sub'].keys()
    dodo_tasks = main.load_task_generators(dodo_module, command_names)
    return doit_ignore(params['dep_file'], dodo_tasks['task_list'],
                       sys.stdout, args)


##########################################################
########## help

help_doc = {'purpose': "show help",
            'usage': "",
            'description': None}

def print_task_help():
    print """

Task Dictionary parameters
--------------------------

Tasks are defined by functions starting with the string ``task_``. It must return a dictionary describing the task with the following fields:

action [required]:
  - type: Python-Task -> tuple (callable, `*args`, `**kwargs`)
  - type: Cmd-Task -> string or list of strings (each item is a different command). to be executed by shell.
  - type: Group-Task -> None.

name [required for sub-task]:
  - type: string. sub-task identifier

dependencies:
  - type: list. items:
    * file (string) path relative to the dodo file
    * task (string) ":<task_name>"
    * run-once (True bool)

getargs:
  - type: dictionary
    * key: string with the name of the function parater (used in a python-action)
    * value: string on the format <task-name>.<variable-name>

targets:
  - type: list of strings
  - each item is file-path relative to the dodo file (accepts both files and folders)

setup:
 - type: list of objects with methods 'setup' and 'cleanup'

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
"""

def cmd_help(params, args):
    if len(args) == 1:
        if args[0] in params['sub']:
            print params['sub'][args[0]].help()
            return 0
        elif args[0] == 'task':
            print_task_help()
            return 0
    print_usage()
    return 0


##########################################################



def cmd_main(cmd_args):
    subCmd = {} # all sub-commands

    # help command
    subCmd['help'] = cmdparse.Command('help', (), cmd_help, help_doc)

    # run command
    run_options = (opt_version, opt_help, opt_dodo, opt_cwd, opt_depfile,
                   opt_always, opt_continue, opt_verbosity, opt_reporter,
                   opt_outfile)
    subCmd['run'] = cmdparse.Command('run', run_options, cmd_run, run_doc)

    # clean command
    clean_options = (opt_dodo, opt_cwd, opt_clean_dryrun)
    subCmd['clean'] = cmdparse.Command('clean', clean_options, cmd_clean,
                                       clean_doc)

    # list command
    list_options = (opt_dodo, opt_depfile, opt_cwd, opt_listall,
                    opt_list_quiet, opt_list_status)
    subCmd['list'] = cmdparse.Command('list', list_options, cmd_list, list_doc)

    # forget command
    forget_options = (opt_dodo, opt_cwd, opt_depfile,)
    subCmd['forget'] = cmdparse.Command('forget', forget_options,
                                        cmd_forget, forget_doc)

    # ignore command
    ignore_options = (opt_dodo, opt_cwd, opt_depfile,)
    subCmd['ignore'] = cmdparse.Command('ignore', ignore_options,
                                        cmd_ignore, ignore_doc)


    try:
        return subCmd['run'](cmd_args, sub=subCmd)

    # wrong command line usage. help user
    except cmdparse.CmdParseError, err:
        print str(err)
        return 1

    # in python 2.4 SystemExit and KeyboardInterrupt subclass
    # from Exception.
    # TODO maybe I should do something to help the user find out who
    # is raising SystemExit. because it shouldnt happen...
    except (SystemExit, KeyboardInterrupt):
        raise

    # dont show traceback for user errors.
    except (main.InvalidDodoFile, main.InvalidCommand, task.InvalidTask), err:
        print "ERROR:", str(err)
        return 1

    # make sure exception is printed out. we migth have redirected stderr
    except Exception:
        sys.__stderr__.write(traceback.format_exc())
        return 1

