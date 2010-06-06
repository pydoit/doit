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


class TestTitleWithActions:
    def test_actions(self):
        t = task.Task("MyName",["MyAction"], title=tools.title_with_actions)
        assert "MyName => Cmd: MyAction" == t.title()

    def test_group(self):
        t = task.Task("MyName", None, file_dep=['file_foo'],
                      task_dep=['t1','t2'], title=tools.title_with_actions)
        assert "MyName => Group: t1, t2" == t.title()


