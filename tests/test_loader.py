import os,inspect

from doit.loader import Loader

class TestLoader(object):
    def setUp(self):
        # this test can be executed from any path
        self.fileName = os.path.abspath(__file__+"/../loader_sample.py")

    def testImport(self):
        loaded = Loader(self.fileName)
        assert inspect.ismodule(loaded.module)

    def testGetTaskGenerators(self):
        loaded = Loader(self.fileName)
        funcNames =  [f.name for f in loaded.get_task_generators()]
        expected = ["nose","checker"]
        assert expected == funcNames

    def testRelativeImport(self):
        # test relative import but test should still work from any path
        # so change cwd.
        os.chdir(os.path.abspath(__file__+"/../.."))
        self.fileName = "tests/loader_sample.py"
        self.testImport()



