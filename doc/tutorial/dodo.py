# execute all dodo.py files used in the tutorial.
# not really tested but if no exception is raised should be good enough.


test_files = [
    # 'calc_dep.py',
    'checker.py',
    'check_timestamp_unchanged.py',
    'compile.py',
    'config_params.py',
    'cproject.py',
    'custom_reporter.py',
    # 'doit_config.py', # task are not defined
    'download.py',
    'folder.py',
    'getargs.py',
    'getargs_dict.py',
    'getargs_group.py',
    'get_var.py',
    'group.py',
    'hello.py',
    'interactiveaction.py',
    'my_dodo.py',
    'my_tasks.py',
    'parameters.py',
    'run_once.py',
    'sample.py',
    'selecttasks.py',
    'settrace.py',
    'subtasks.py',
    'tar.py',
    'task_name.py',
    'task_reusable.py',
    'taskorder.py',
    'timeout.py',
    'title.py',
    'titlewithactions.py',
    'tsetup.py',
    'tutorial_01.py',
    'tutorial_02.py',
    'uptodate_callable.py',
    'verbosity.py',
    ]

def task_sanity():
    for dodo in test_files:
        yield {
            'name': dodo,
            'actions': ['doit -f %(dependencies)s'],
            'file_dep': [dodo],
            'verbosity': 2,
            }
