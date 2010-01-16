"""extra goodies to be used in dodo files"""

import os

def create_folder(dir_path):
    """create a folder in the given path if it doesnt exist yet."""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return True


def title_with_actions(task):
    """return task name task actions"""
    if task.actions:
        title = "\n\t".join([str(action) for action in task.actions])
    # A task that contains no actions at all
    # is used as group task
    else:
        title = "Group: %s" % ", ".join(task.task_dep)
    return "%s => %s"% (task.name, title)


def set_trace(): # pragma: no cover
    """start debugger, make sure stdout shows pdb output.
    output is not restored.
    """
    import pdb
    import sys
    sys.stdout = sys.__stdout__
    pdb.Pdb().set_trace(sys._getframe().f_back)

