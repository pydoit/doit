===============
Reference
===============

Task Dictionary parameters
--------------------------

Tasks are defined by functions starting with the string ``task_``. It must return a dictionary describing the task with the following fields:

action:
  - Required field
  - type: Python-Task -> tuple (callable, `*args`, `**kwargs`)
  - type: Cmd-Task -> string or list of strings (each item is a different command). to be executed by shell.
  - type: Group-Task -> None.

name:
  - Required field - Sub-tasks only
  - type: string. sub-task identifier

dependencies:
  - Optional field
  - type: list. items:
    * file (string) path relative to the dodo file
    * task (string) ":<task_name>"
    * run-once (True bool)

targets:
  - Optional field
  - type: list of strings
  - each item is file-path relative to the dodo file (accepts both files and folders)

setup:
 - Optional field
 - type: list of objects with methods 'setup' and 'cleanup'

doc:
 - Optional field
 - type: string -> the description text

clean:
 - Optional field
 - type: (True bool) remove target files
 - type: (list) of actions (see above)

params:
 - Optional field
 - type: (list) of dictionaries containing:
   - name [required] (string) parameter identifier
   - default [required] default value for parameter
   - short [optional] (string - 1 letter) short option string
   - long [optional] (string) long option string
   - type [optional] the option will be converted to this type

verbosity:
 - Optional field (default value 1)
 - type: int
   -  0: capture (do not print) stdout/stderr from task.
   -  1: (default) capture stdout only.
   -  2: do not capture anything (print everything immediately).

title:
 - Optional field
 - type: callable taking one parameter as argument (the task reference)
