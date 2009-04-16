===============
Reference
===============

Command line
------------

.. program :: doit

.. describe:: doit [options] [task] [task] ...

options
^^^^^^^

.. cmdoption:: -h, --help            

show this help message and exit

.. cmdoption:: -f FILE, --file FILE

load task from dodo FILE 
[default: dodo.py]

.. cmdoption:: -v VERBOSITY, --verbosity VERBOSITY 

* 0 capture (do not print) stdout/stderr from task. 
* 1 capture stdout only. 
* 2 dont capture anything (print everything immediately)
[default: 0]

.. cmdoption:: -a, --always-execute  

always execute tasks even if up-to-date 
[default: False]

.. cmdoption:: -l, --list
list tasks from dodo file 

.. cmdoption:: --list-all
list all tasks and sub-tasks from dodo file


Task Dictionary parameters
--------------------------

Tasks are defined by functions starting with the string ``task_``. It must return a dictionary describing the task with the following fields:

action:
  - Required field
  - type: Python-Task -> function(callable) reference. 
  - type: Cmd-Task -> string to be executed by shell.
  - type: Group-Task -> None.

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
  - type: list. items:
    * file (string) path relative to the dodo file
    * folder (string) must end with "/"
    * task (string) ":<task_name>"
    * True (bool) run once

targets:
  - Optional field
  - type: list of strings
  - each item is file-path relative to the dodo file


