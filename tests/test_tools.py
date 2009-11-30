import os

from doit import tools
from doit import task

def test_create_folder():
    def rm_dir():
        if os.path.exists(DIR_DEP):
            os.removedirs(DIR_DEP)

    DIR_DEP = os.path.join(os.path.dirname(__file__),"parent/child/")
    rm_dir()
    assert True == tools.create_folder(DIR_DEP)
    assert os.path.exists(DIR_DEP)
    rm_dir()

def test_title():
    t = task.Task("MyName",["MyAction"], title=tools.title_with_actions)
    assert "MyName => %s"%str(t) == t.title(), t.title()
