
=======
Changes
=======


0.31.1 (*2018-03-18*)
=====================

 - Fix #249 reporter bug when using `--continue` option
 - Fix #248 test failures of debian when using GDBM
 - Fix #164 `get_var` fails on multiprocess execution on Windows
 - Fix #245 custom `clean` action takes `dry-run` into account


0.31.0 (*2018-02-25*)
=====================

 - BACKWARD INCOMPATIBLE: Drop Python 3.3 support
 - Fix #171 Passing environment variables to CmdAction
 - Fix #184 parametrize script name
 - CmdParse now support getting values from OS environment variables
 - option `seek_file` control by ENV var `DOIT_SEEK_FILE`
 - #192 ipython extension uses `load_ipython_extension`
 - #218 clean with option `--forget` can be used to also forget about cleaned tasks
 - Fix strace command (seems strace output was modified)
 - Fix #224: use `mock` from stdlib
 - #227: enhancements to `info` command
 - Fix #197: improve error message for invalid `clean` and `teardown` task params
 - Fix #211: do not display traceback for error when missing `file_dep`
 - Task `verbosity` has precedence over `verbosity` from config
 - Fix #140: add `failure-verbosity`. ConsoleReporter, by default,
   do not print stderr twice.
 - Fix #155: pass `selected_tasks` to `Reporter.initialize()`
 - Fix #221: do not leak meta arguments to actions `kwargs`
 - Fix #202: help command display option's name used on config
 - Fix #209: fix `clean` ordering, and following implicit task_deps
 - Fix: list of sub-tasks do not include non-related `task_dep`
 - Internal: Removed `Task.is_subtask` use `Task.subtask_of` instead


0.30.3 (*2017-02-20*)
=====================

 - Revert usage of setuptools environment markers (feature too new)


0.30.2 (*2017-02-16*)
=====================

 - Fix dependency on `pathlib` from PyPi


0.30.1 (*2017-02-16*)
=====================

 - Fix GH-#159 KeyError on doit list --status when missing file dependency
 - add python3.6 support


0.30.0 (*2016-11-22*)
=====================

 - BACKWARD INCOMPATIBLE: #112 drop python2 compatibility
 - GH-#94: option to read output from CmdAction line or byte buffered
 - GH-#114: `file_dep`, `targets` and `CmdAction` support pathlib.
 - fix GH-#100: make cmd `completion` output deterministic
 - fix GH-#99: positional argument on tasks not specified from cmd-line
 - fix GH-#97: `list` command does not display task-doc for `DelayedTask`
                when `creates` is specified
 - fix GH-#131: race condition in doit.tools.create_folder
 - fix `auto` command on OS-X systems
 - fix GH-#117: Give error when user tries to use equal sign on task name



0.29.0 (*2015-08-16*)
=====================

 - BACKWARD INCOMPATIBLE: revert - `result_dep` to create an implicit `task_dep`
 - fix GH-#59: command `list` issue with unicode names
 - fix GH-#72: cmd `completion` escaping of apostrophes in zsh
 - fix GH-#74: Task action's handle python3 callables with keyword only args
 - fix GH-#50: Executing tasks in parallel (multi-process) fails on Windows
 - fix GH-#71 #92: Better error messages for invalid command line tasks/commands
 - fix issue with `--always-execute` and `setup` tasks
 - GH-#67: multiprocess runner handles closures in tasks (using cloudpickle)
 - GH-#58: add `DelayedLoader` parameter `target_regex`
 - GH-#30: add `DelayedLoader` parameter `creates`
 - GH-#58: cmd `Run` add option `--auto-delayed-regex`
 - GH-#24: cmd `info` add option `--status` show reason a task is not up-to-date
 - GH-#66: cmd `auto` support custom ( user specified ) commands to be executed
   after each task execution
 - GH-#61: speed up sqlite3 backend (use internal memory cache)


0.28.0 (*2015-04-22*)
=====================

 - BACKWARD INCOMPATIBLE: signature for custom DB backend changed
 - BACKWARD INCOMPATIBLE: `DoitMain` API change
 - BACKWARD INCOMPATIBLE: `Command` API change
 - BACKWARD INCOMPATIBLE: `default` reporter renamed to `console`
 - GH-#25: Add a `reset-dep` command to recompute dependencies state
 - GH-#22: Allow to customize how file_dep are checked
 - GH-#31: Add IPython `%doit` magic-function loading tasks from its global
   namespace
 - read configuration options from INI files
 - GH-#32 plugin system
 - plugin support: COMMAND - add new commands
 - plugin support: LOADER - add custom task loaders
 - plugin support: REPORTER - add custom reporter for `run` command
 - plugin support: BACKEND - add custom DB persistence backend
 - GH-#36 PythonAction recognizes returned TaskError or TaskFailed
 - GH-#37 CmdParse support for arguments of type list
 - GH-#47 CmdParse support for choices
 - fix issue when using unicode strings to specify `minversion` on python 2
 - fix GH-#27 auto command in conjunction with task arguments
 - fix GH-#44 Fix the list -s command when result_dep is used
 - fix GH-#45 make sure all `uptodate` checks are executed (no short-circuit)


0.27.0 (*2015-01-30*)
======================

 - BACKWARD INCOMPATIBLE: drop python 2.6 support
 - BACKWARD INCOMPATIBLE: removed unmaintained genstandalone script
 - BACKWARD INCOMPATIBLE: removed runtests.py script and support to run
                          tests through setup.py
 - BACKWARD INCOMPATIBLE: `result_dep` creates an implicit `setup`
                          (was `task_dep`)
 - BACKWARD INCOMPATIBLE: GH-#9 `getargs` creates an implicit `result_dep`
 - BACKWARD INCOMPATIBLE: `CmdAction` would always decode process output
                          using `errors='strict'` default changed to `replace`
 - allow task-creators to return/yield Task instances
 - fix GH-#14: add support for delayed task creation
 - fix GH-#15: `auto` (linux) inotify also listen for `MOVE_TO` events
 - GH-#4 `CmdAction` added parameters `encoding` and `decode_error`
 - GH-#6: `loader.task_loader()` accepts methods as *task creators*


0.26.0 (*2014-08-30*)
======================

 - moved development to git/github
 - `uptodate` callable "magic" arguments `task` and `values` are now optional
 - added command `info` to display task metadata
 - command `clean` smarter execution order
 - remove `strace` short option `-k` because it conflicts with `run` option
 - fix zsh tab-completion script when not `doit` script
 - fix #79. Use setuptools and `entry_points`
 - order of yielded tasks is preserved
 - #68. pass positional args to tasks
 - fix tab-completion on BASH for sub-commands that take file arguments

0.25.0 (*2014-03-26*)
======================

 - BACKWARD INCOMPATIBLE: use function `doit.get_initial_workdir()`
   instead of variable `doit.initial_workdir`
 - DEPRECATED `tools.InteractiveAction` renamed to `tools.LongRunning`
 - fix: `strace` raises `InvalidCommand` instead of using `assert`
 - #28: task `uptodate` support string to be executed as shell command
 - added `tools.Interactive` for use with interactive commands
 - #69: added doit.run() to make it easier to turn a dodo file into executable
 - #70: added option "--pdb" to command `run`
 - added option "--single" to command `run`
 - include list of file_dep as an implicit dependency


0.24.0 (*2013-11-24*)
======================

 - reporter added `initialize()`
 - cmd `list`: added option `--template`
 - dodo.py can specify minimum required doit version with DOIT_CONFIG['minversion']
 - #62: added the absolute path from which doit is invoked `doit.initial_workdir`
 - fix #36: added method `isatty()` to `action.Writer`
 - added command `tabcompletion` for bash and zsh
 - fix #56: allow python actions to have default values for task parameters


0.23.0 (*2013-09-20*)
======================

 - support definition of group tasks using basename without any task
 - added task property `watch` to specific extra files/folders in auto command
 - CmdAction support for all arguments of subprocess.Popen, but stdout and stderr
 - added command option `-k` as short for `--seek-file`
 - task action can be specified as a list of strings (executed using subprocess.Popen shell=False)
 - fix #60: result of calc_dep only considered if not run yet
 - fix #61: test failures involving DBM
 - fix: do not allow duplicate task names


0.22.1 (*2013-08-04*)
======================

 - fix reporter output in py3 was being displayed as bytes instead of string
 - fix pr#12 read file in chunks when calculating MD5
 - fix #54 - remove distribute bootstrapping during installation


0.22.0 (*2013-07-05*)
======================

- fix #49: skip unicode tests on systems with non utf8 locale
- fix #51: bash completion does not mess up with global COMP_WORDBREAKS
- fix docs spelling and added task to check spelling
- fix #47: Task.options can always be accessed from `uptodate` code
- fix #45: cmd forget, added option -s/--follow-sub to forget task_dep too


0.21.1 (*2013-05-21*)
======================

- fix tests on python3.3.1
- fix race condition on CmdAction (affected only python>=3.3.1)


0.21.0 (*2013-04-29*)
======================

- fix #38: `doit.tools.create_folder()` raise error if file exists in path
- `create_doit_tasks` not called for unbound methods
- support execution using "python -m doit"
- fix #33: Failing to clean a group of task(s) with sub-tasks
- python-actions can take a magic "task" parameter as reference to task
- expose task.clean_targets
- tools.PythonInteractiveAction saves "result" and "values"
- fix #40. added option to use threads for parallel running of tasks
- same code base for python 2 & 3 (no need to use tool `2to3`)
- add sqlite3 DB backend
- added option to select backend


0.20.0 (*2013-01-09*)
======================

- added command `dumpdb`
- added `CmdAction.save_out` param
- `CmdAction` support for callable that returns a command string
- BACKWARD INCOMPATIBLE `getargs` for a group task gets a dict where
  each key is the name of subtasks (previously it was a list)
- added command `strace`
- cmd `auto` run tasks on separate process
- support unicode for task name


0.19.0 (*2012-12-18*)
======================

- support for `doit help <task-name>`
- added support to load tasks using `create_doit_tasks`
- dropped python 2.5 support


0.18.1 (*2012-12-03*)
=======================

- fix bug cmd option --continue not being recognized


0.18.0 (*2012-11-27*)
=======================

- remove DEPRECATED `Task.insert_action`, `result_dep` and `getargs` using strings
- fix #10 --continue does not execute tasks that have failed dependencies
- fix --always-execute does not execute "ignored" tasks
- fix #29 python3 cmd-actions issue
- fix #30 tests pass on all dbm backends
- API to add new sub-commands to doit
- API to modify task loader
- API to make dodo.py executable
- added ZeroReporter


0.17.0 (*2012-09-20*)
======================

- fix #12 Action.out and Action.err not set when using multiprocessing
- fix #16 fix `forget` command on gdbm backend
- fix #14 improve parallel execution (better process utilization)
- fix #9 calc_dep create implicit task_dep if a file_dep returned is a also a target
- added tools.result_dep
- fix #15 tools.result_dep supports group-tasks
- DEPRECATE task attribute `result_dep` (use tools.result_dep)
- DEPRECATE `getargs` specification using strings (must use 2-element tuple)
- several changes on `uptodate`
- DEPRECATE `Task.insert_action` (replaced by `Task.value_savers`)
- fix #8 `clean` cleans all subtasks from a group-task
- fix #8 `clean` added flag `--all` to clean all tasks
- fix #8 `clean` when no task is specified set --clean-dep and clean default tasks


0.16.1 (*2012-05-13*)
======================

- fix multiprocessing/parallel bug
- fix unicode bug on tools.config_changed
- convert tools uptodate stuff to a class, so it can be used with multi-processing


0.16.0 (*2012-04-23*)
=======================

- added task parameter ``basename``
- added support for task generators yield nested python generators
- ``doit`` process return value ``3`` in case tasks do start executing (reporter is not used)
- task parameter ``getargs`` take a tuple with 2 values (task_id, key_name)
- DEPRECATE ``getargs`` being specified as <task_id>.<key_name>
- ``getargs`` can take all values from task if specified as (task_id, None)
- ``getargs`` will pass values from all sub-tasks if specified task is a group task
- result_dep on PythonAction support checking for dict values
- added ``doit.tools.PythonInteractiveAction``


0.15.0 (*2012-01-10*)
=======================

- added option --db-file (#909520)
- added option --no-continue (#586651)
- added genstandalone.py to create a standalone ``doit`` script (#891935)
- fix doit.tools.set_trace to not modify sys.stdout


0.14.0 (*2011-11-05*)
========================

- added tools.InteractiveAction (#865290)
- bash completion script
- sub-command list: tasks on alphabetical order, better formatting (#872829)
- fix ``uptodate`` to accept instance methods callables (#871967)
- added command line option ``--seek-file``
- added ``tools.check_unchanged_timestamp`` (#862606)
- fix bug subclasses of BaseAction should get a task reference


0.13.0 (*2011-07-18*)
========================

- performance speed improvements
- fix bug on unicode output when task fails
- ConsoleReporter does not output task's title for successful tasks that start with an ``_``
- added ``tools.config_changed`` (to be used with ``uptodate``)
- ``teardown`` actions are executed in reverse order they were registered
- added ``doit.get_var`` to get variables passed from command line
- getargs creates implicit "setup" task not a "task_dep"


0.12.0 (*2011-05-29*)
=======================

- fix bug #770150 - error on task dependency from target
- fix bug #773579 - unicode output problems
- task parameter ``uptodate`` accepts callables
- deprecate task attribute run_once. use tools.run_once on uptodate instead
- added doit.tools.timeout


0.11.0 (*2011-04-20*)
========================

- no more support for python2.4
- support for python 3.2
- fix bug on unicode filenames & unicode output (#737904)
- fix bug when using getargs together with multiprocess (#742953)
- fix for dumbdbm backend
- fix task execution order when using "auto" command
- fix getargs when used with sub-tasks
- fix calc_dep when used with "auto" command
- "auto" command now support verbosity control option

0.10.0 (*2011-01-24*)
======================

- add task parameter "uptodate"
- add task parameter "run_once"
- deprecate file_dep bool values and None
- fix issues with error reporting for JSON Reporter
- "Reporter" API changes
- ".doit.db" now uses a DBM file format by default (speed optimization)

0.9.0 (*2010-06-08*)
=====================

- support for dynamic calculated dependencies "calc_dep"
- support for user defined reporters
- support "auto" command on mac
- fix installer on mac. installer aware of different python versions
- deprecate 'dependencies'. use file_dep, task_dep, result_dep.

0.8.0 (*2010-05-16*)
=======================

- parallel execution of tasks (multi-process support)
- sub-command "list" option "--deps", show list of file dependencies
- select task by wildcard (fnmatch) i.e. test:folderXXX/*
- task-setup can be another task
- task property "teardown" substitute of setup-objects cleanup
- deprecate setup-objects


0.7.0 (*2010-04-08*)
=====================

- configure options on dodo file (deprecate DEFAULT_TASKS)(#524387)
- clean and forget act only on default tasks (not all tasks) (#444243)
- sub-command "clean" option "clean-dep" to follow dependencies (#444247)
- task dependency "False" means never up-to-date, "None" ignored
- sub-command "list" by default do not show tasks starting with an underscore, added option (-p/--private)
- new sub-command "auto"


0.6.0 (*2010-01-25*)
=====================

- improve (speed optimization) of check if file modified (#370920)
- sub-command "clean" dry-run option (-n/--dry-run) (#444246)
- sub-command "clean" has a more verbose output (#444245)
- sub-command "list" option to show task status (-s/--status) (#497661)
- sub-command "list" filter tasks passed as positional parameters
- tools.set_trace, PDB with stdout redirection (#494903)
- accept command line optional parameters passed before sub-command (#494901)
- give a clear error message if .doit.db file is corrupted (#500269)
- added task option "getargs". actions can use computed values from other tasks (#486569)
- python-action might return a dictionary on success


0.5.1 (*2009-12-03*)
=====================

- fix. task-result-dependencies should be also added as task-dependency to force its execution.


0.5.0 (*2009-11-30*)
=====================

- task parameter 'clean' == True, cleans empty folders, and display warning for non-empty folders
- added command line option --continue. Execute all tasks even if tasks fails
- added command line option --reporter to select result output reporter
- added executed-only reporter
- added json reporter
- support for task-result dependency #438174
- added sub-command ignore task
- added command line option --outfile. write output to specified file path
- added support for passing arguments to tasks on cmd line
- added command line option --dir (-d) to set current working directory
- removed dodo-sample sub-command
- added task field 'verbosity'
- added task field 'title'
- modified default way a task is printed on console (just show ".  name"), old way added to doit.tools.task_title_with_actions


0.4.0 (*2009-10-05*)
====================

- deprecate anything other than a boolean values as return of python actions
- sub-cmd clean (#421450)
- remove support for task generators returning action (not documented behavior)
- setup parameter for a task should be a list - single value deprecated (#437225)
- PythonAction support 'dependencies', 'targets', 'changed' parameters
- added tools.create_folder (#421453)
- deprecate folder-dependency
- CmdActions reference to dependencies, targets and changed dependencies (#434327)
- print task description when printing through doit list (#425811)
- action as list of commands/python (#421445)
- deprecate "action" use "actions"


0.3.0 (*2009-08-30*)
=====================

- added subcommand "forget" to clear successful runs status (#370911)
- save run results in text file using JSON. (removed dbm)
- added support for DEFAULT_TASKS in dodo file
- targets md5 is not checked anymore. if target exist, task is up-to-date. it also supports folders
- cmd line sub-commands (#370909)
- remove hashlib dependency on python 2.4
- sub-cmd to create dodo template
- cmd-task supports a list of shell commands
- setup/cleanup for task (#370905)


0.2.0 (*2009-04-16*)
====================

- docs generated using sphinx
- execute once (dependency = True)
- group task
- support python 2.4 and 2.6
- folder dependency


0.1.0 (*2008-04-14*)
====================

- initial release

