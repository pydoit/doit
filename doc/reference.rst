===============
Reference
===============

Task Dictionary parameters
--------------------------

Tasks are defined by functions starting with the string ``task_``. It must return a dictionary describing the task with the following fields:

action:
  - Required field
  - type: Python-Task -> function(callable) reference.
  - type: Cmd-Task -> string or list of strings (each item is a different command). to be executed by shell.
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
  - each item is file-path relative to the dodo file (accepts both files and folders)

setup:
 - Optional field
 - type: object with methods 'setup' and 'cleanup'