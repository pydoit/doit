import os

from doit.tools import create_folder

def test_create_folder():
    def rm_dir():
        if os.path.exists(DIR_DEP):
            os.removedirs(DIR_DEP)

    DIR_DEP = os.path.join(os.path.dirname(__file__),"parent/child/")
    rm_dir()
    assert True == create_folder(DIR_DEP)
    assert os.path.exists(DIR_DEP)
    rm_dir()

