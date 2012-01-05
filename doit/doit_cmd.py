"""doit CLI (command line interface)"""

import os
import sys
import traceback

import doit
from .exceptions import InvalidDodoFile, InvalidCommand, InvalidTask
from . import loader
from . import cmdparse
from .cmds import doit_run, doit_clean, doit_list, doit_forget, doit_ignore
from .cmds import doit_auto

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

# seek dodo file on parent folders
opt_seek_file = {'name': 'seek_file',
                 'short': '',
                 'long': 'seek-file',
                 'type': bool,
                 'default': False,
                 'help': ("seek dodo file on parent folders " +
                          "[default: %(default)s]")
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
               'long': 'db-file',
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
                'inverse': 'no-continue',
                'type': bool,
                'default': False,
                'help': "continue executing tasks even after a failure "
                        "[default: %(default)s]"
                }


opt_num_process = {'name': 'num_process',
                   'short': 'n',
                   'long': 'process',
                   'type': int,
                   'default': 0,
                   'help': "number of subprocesses"
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
                 'type':str, #TODO type choice (limit the accepted strings)
                 'default': 'default',
                 'help':
"""Choose output reporter. Available:
'default': report output on console
'executed-only': no output for skipped (up-to-date) and group tasks
'json': output result in json format
"""
                 }


def _path_params(params):
    return (params['dodoFile'], params['cwdPath'], params['seek_file'],
            params['sub'].keys())


run_doc = {'purpose': "run tasks",
           'usage': "[TASK/TARGET...]",
           'description': None}

def print_version():
    """print doit version (includes path location)"""
    print ".".join([str(i) for i in doit.__version__])
    print "bin @", os.path.abspath(__file__)
    print "lib @", os.path.dirname(os.path.abspath(doit.__file__))

def print_usage():
    """print doit "usage" (basic help) instructions"""
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
 doit auto              automatically run doit when a dependency changes

 doit help              show help / reference
 doit help task         show help on task dictionary fields
 doit help <command>    show command usage
"""

def cmd_run(params, args):
    """execute cmd 'run' """

    # special parameters that dont run anything
    if params["version"]:
        print_version()
        return 0
    if params["help"]:
        print_usage()
        return 0

    # check if no sub-command specified. default command is "run"
    if len(args) == 0 or args[0] not in params['sub']:
        dodo_tasks = loader.get_tasks(*_path_params(params))
        params.update_defaults(dodo_tasks['config'])
        default_tasks = args or dodo_tasks['config'].get('default_tasks')
        return doit_run(params['dep_file'], dodo_tasks['task_list'],
                        params['outfile'], default_tasks,
                        params['verbosity'], params['always'],
                        params['continue'], params['reporter'],
                        params['num_process'])

    # explicit sub-cmd. parse arguments again
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

opt_list_private = {'name': 'private',
                    'short': 'p',
                    'long': 'private',
                    'type': bool,
                    'default': False,
                    'help': "print private tasks (start with '_')"}

opt_list_dependencies = {'name': 'list_deps',
                         'short': '',
                         'long': 'deps',
                         'type': bool,
                         'default': False,
                         'help': ("print list of dependencies "
                                  "(file dependencies only)")
}



def cmd_list(params, args):
    """execute cmd 'list' """
    dodo_tasks = loader.get_tasks(*_path_params(params))
    params.update_defaults(dodo_tasks['config'])
    return doit_list(params['dep_file'], dodo_tasks['task_list'], sys.stdout,
                     args, params['all'], not params['quiet'],
                     params['status'], params['private'], params['list_deps'])

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

opt_clean_cleandep = {'name': 'cleandep',
                    'short': 'c', # clean
                    'long': 'clean-dep',
                    'type': bool,
                    'default': False,
                    'help': 'clean task dependencies too'}

def cmd_clean(params, args):
    """execute cmd 'clean' """
    dodo_tasks = loader.get_tasks(*_path_params(params))
    params.update_defaults(dodo_tasks['config'])
    options = args or dodo_tasks['config'].get('default_tasks')
    return doit_clean(dodo_tasks['task_list'], sys.stdout, params['dryrun'],
                      params['cleandep'], options)


##########################################################
########## forget

forget_doc = {'purpose': "clear successful run status from internal DB",
              'usage': "[TASK ...]",
              'description': None}

def cmd_forget(params, args):
    """execute cmd 'forget' """
    dodo_tasks = loader.get_tasks(*_path_params(params))
    params.update_defaults(dodo_tasks['config'])
    options = args or dodo_tasks['config'].get('default_tasks')
    return doit_forget(params['dep_file'], dodo_tasks['task_list'],
                       sys.stdout, options)


##########################################################
########## ignore

ignore_doc = {'purpose': "ignore task (skip) on subsequent runs",
              'usage': "TASK [TASK ...]",
              'description': None}

def cmd_ignore(params, args):
    """execute cmd 'ignore' """
    dodo_tasks = loader.get_tasks(*_path_params(params))
    params.update_defaults(dodo_tasks['config'])
    return doit_ignore(params['dep_file'], dodo_tasks['task_list'],
                       sys.stdout, args)


##########################################################
########## auto

auto_doc = {'purpose': "automatically execute tasks when a dependency changes",
            'usage': "TASK [TASK ...]",
            'description': None}

def cmd_auto(params, args):
    """execute cmd 'auto' """
    dodo_tasks = loader.get_tasks(*_path_params(params))
    params.update_defaults(dodo_tasks['config'])
    filter_tasks = args or dodo_tasks['config'].get('default_tasks')
    return doit_auto(params['dep_file'], dodo_tasks['task_list'], filter_tasks,
                     params['verbosity'])


##########################################################
########## help

help_doc = {'purpose': "show help",
            'usage': "",
            'description': None}


def print_task_help():
    """print help for 'task' usage """
    print """

Task Dictionary parameters
--------------------------

Tasks are defined by functions starting with the string ``task_``. It must return a dictionary describing the task with the following fields:

actions [required]:
  - type: Python-Task -> tuple (callable, `*args`, `**kwargs`)
  - type: Cmd-Task -> string or list of strings (each item is a different command). to be executed by shell.
  - type: Group-Task -> None.

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

result_dep:
  - type: list. items:
    * task name (string)

uptodate:
  - type: list. items:
    * None - None values are just ignored
    * bool
    * callable - returns bool or None. must take 2 positional parameters (task, values)

calc_dep:
  - type: list. items:
    * task name (string)

getargs:
  - type: dictionary
    * key: string with the name of the function parater (used in a python-action)
    * value: string on the format <task-name>.<variable-name>

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
"""

def cmd_help(params, args):
    """execute cmd 'help' """
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
    """entry point for all commands"""
    sub_cmd = {} # all sub-commands

    # help command
    sub_cmd['help'] = cmdparse.Command('help', (), cmd_help, help_doc)

    # run command
    run_options = (opt_version, opt_help, opt_dodo, opt_cwd, opt_depfile,
                   opt_seek_file, opt_always, opt_continue, opt_verbosity,
                   opt_reporter, opt_outfile, opt_num_process)
    sub_cmd['run'] = cmdparse.Command('run', run_options, cmd_run, run_doc)

    # clean command
    clean_options = (opt_dodo, opt_cwd, opt_seek_file, opt_clean_cleandep,
                     opt_clean_dryrun)
    sub_cmd['clean'] = cmdparse.Command('clean', clean_options, cmd_clean,
                                       clean_doc)

    # list command
    list_options = (opt_dodo, opt_depfile, opt_cwd, opt_seek_file , opt_listall,
                    opt_list_quiet, opt_list_status, opt_list_private,
                    opt_list_dependencies)
    sub_cmd['list'] = cmdparse.Command('list', list_options, cmd_list, list_doc)

    # forget command
    forget_options = (opt_dodo, opt_cwd, opt_seek_file, opt_depfile,)
    sub_cmd['forget'] = cmdparse.Command('forget', forget_options,
                                        cmd_forget, forget_doc)

    # ignore command
    ignore_options = (opt_dodo, opt_cwd, opt_seek_file, opt_depfile,)
    sub_cmd['ignore'] = cmdparse.Command('ignore', ignore_options,
                                        cmd_ignore, ignore_doc)

    # auto command
    auto_options = (opt_dodo, opt_cwd, opt_seek_file, opt_depfile,
                    opt_verbosity)
    sub_cmd['auto'] = cmdparse.Command('auto', auto_options,
                                        cmd_auto, auto_doc)

    # get cmdline variables from args
    doit.reset_vars()
    args_no_vars = []
    for arg in cmd_args:
        if (arg[0] != '-') and ('=' in arg):
            name, value = arg.split('=', 1)
            doit.set_var(name, value)
        else:
            args_no_vars.append(arg)

    try:
        return sub_cmd['run'](args_no_vars, sub=sub_cmd)

    # dont show traceback for user errors.
    except (cmdparse.CmdParseError, InvalidDodoFile,
            InvalidCommand, InvalidTask), err:
        sys.stderr.write("ERROR: %s\n" % str(err))
        return 1

    except Exception:
        sys.stderr.write(traceback.format_exc())
        return 1

