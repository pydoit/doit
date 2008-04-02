===============
Reference
===============


Command line options
--------------------

DoIt Usage::

  ..$doit --help
  Usage: doit [options] [tasks]

  Options:
    -h, --help            show this help message and exit
    -f FILE, --file=FILE  load task from dodo FILE [default: dodo.py]
    -v VERBOSITY, --verbosity=VERBOSITY 0 capture stdout/stderr from task. 1 capture stdout only. 2 don't capture anything. [default: 0]
    -a, --always-execute  always execute tasks even if up-to-date [default: False]
    -l, --list            list tasks from dodo file [default: 0]
    --list-all            list all tasks and sub-tasks from dodo file [default: 0]



Task Dictionary parameters
--------------------------

Tasks are defined by functions starting with the string ``task_``. It must return a dictionary describing the task with the following fields:

action:
  - Required field
  - type: Python-Task -> function(callable) reference. 
  - type: Cmd-Task -> string to be executed by shell.

args:
  - Optional field - Python-Task only
  - type: list of parameters to be passed to passed to "action" function

kwargs:
  - Optional field - Python-Task only
  - type: dictionary of keyword parameters to be passed to "action" function

name:
  - Required field - Sub-tasks only
  - type: string. subtask identifier 

dependencies:
  - Optional field
  - type: list of strings
  - each item is file-path relative to the dodo file
  - or ":<task_name>" for a task-dependency

targets:
  - Optional field
  - type: list of strings
  - each item is file-path relative to the dodo file


