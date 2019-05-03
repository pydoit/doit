"""ModuleLoadTest uses this file to load tasks from module."""

DOIT_CONFIG = dict(verbose=2)


def task_xxx1():
    return dict(actions=[])


task_no = 'strings are not tasks'


def blabla():
    ...  # pragma: no cover
