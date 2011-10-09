import os

import pytest

from doit.exceptions import InvalidDodoFile, InvalidCommand
from doit.task import InvalidTask, Task
from doit.loader import load_task_generators, generate_tasks, get_tasks
from doit.loader import isgenerator, get_module


class TestIsGenerator(object):
    def testIsGeneratorYes(self):
        def giveme(): # pragma: no cover
            for i in range(3):
                yield i
        g = giveme()
        assert isgenerator(g)

    def testIsGeneratorNo(self):
        def giveme():
            return 5
        assert not isgenerator(giveme())


class TestGenerateTasks(object):

    def testDict(self):
        tasks = generate_tasks("dict",{'actions':['xpto 14']})
        assert isinstance(tasks[0],Task)

    # name field is only for subtasks.
    def testInvalidNameField(self):
        pytest.raises(InvalidTask, generate_tasks, "dict",
                                 {'actions':['xpto 14'],'name':'bla bla'})

    def testInvalidValue(self):
        pytest.raises(InvalidTask, generate_tasks, "dict",'xpto 14')

    def testGenerator(self):
        def f_xpto():
            for i in range(3):
                yield {'name':str(i), 'actions' :["xpto -%d"%i]}
        tasks = generate_tasks("xpto", f_xpto())
        assert isinstance(tasks[0], Task)
        assert 4 == len(tasks)
        assert "xpto:0" == tasks[1].name
        assert not tasks[0].is_subtask
        assert tasks[1].is_subtask

    def testGeneratorDoesntReturnDict(self):
        def f_xpto():
            for i in range(3):
                yield "xpto -%d"%i
        pytest.raises(InvalidTask, generate_tasks,"xpto",
                                 f_xpto())

    def testGeneratorDictMissingName(self):
        def f_xpto():
            for i in range(3):
                yield {'actions' :["xpto -%d"%i]}
        pytest.raises(InvalidTask, generate_tasks,"xpto",
                                 f_xpto())

    def testGeneratorDictMissingAction(self):
        def f_xpto():
            for i in range(3):
                yield {'name':str(i)}
        pytest.raises(InvalidTask, generate_tasks,"xpto",
                                 f_xpto())

    def testUseDocstring(self):
        tasks = generate_tasks("dict",{'actions':['xpto 14']}, "my doc")
        assert "my doc" == tasks[0].doc

    def testDocstringNotUsed(self):
        mytask = {'actions':['xpto 14'], 'doc':'from dict'}
        tasks = generate_tasks("dict", mytask, "from docstring")
        assert "from dict" == tasks[0].doc

    def testGeneratorDocString(self):
        def f_xpto():
            "the doc"
            for i in range(3):
                yield {'name':str(i), 'actions' :["xpto -%d"%i]}
        tasks = generate_tasks("xpto", f_xpto(), f_xpto.__doc__)
        assert "the doc" == tasks[0].doc




class TestLoadTaskGenerators(object):
    def testAbsolutePath(self, cwd): #FIXME funcarg should be for loader_sample
        fileName = os.path.join(os.path.dirname(__file__),"loader_sample.py")
        expected = ["xxx1","yyy2"]
        dodo_module = get_module(fileName)
        dodo = load_task_generators(dodo_module)
        assert expected == [t.name for t in dodo['task_list']]

    def testRelativePath(self, cwd):
        # test relative import but test should still work from any path
        # so change cwd.
        this_path = os.path.join(os.path.dirname(__file__),'..')
        os.chdir(os.path.abspath(this_path))
        fileName = "tests/loader_sample.py"
        expected = ["xxx1","yyy2"]
        dodo_module = get_module(fileName)
        dodo = load_task_generators(dodo_module)
        assert expected == [t.name for t in dodo['task_list']]

    def testInParentDir(self, cwd):
        os.chdir('data')
        fileName = "loader_sample.py"
        pytest.raises(InvalidDodoFile, get_module, fileName)
        get_module(fileName, seek_parent=True)
        # cwd is changed to location of dodo.py
        assert os.getcwd() == os.path.dirname(os.path.abspath(fileName))

    def testNameInBlacklist(self, cwd):
        fileName = os.path.join(os.path.dirname(__file__),"loader_sample.py")
        dodo_module = get_module(fileName)
        pytest.raises(InvalidDodoFile, load_task_generators,
                                 dodo_module, ['yyy2'])

    def testWrongFileName(self):
        fileName = os.path.join(os.path.dirname(__file__),"i_dont_exist.py")
        pytest.raises(InvalidDodoFile, get_module, fileName)

    def testWrongFileNameInParentDir(self, cwd):
        os.chdir('data')
        fileName = os.path.join("i_dont_exist.py")
        pytest.raises(InvalidDodoFile, get_module, fileName, seek_parent=True)

    def testDocString(self, cwd):
        fileName = os.path.join(os.path.dirname(__file__),"loader_sample.py")
        dodo_module = get_module(fileName)
        dodo = load_task_generators(dodo_module)
        assert "task doc" == dodo['task_list'][0].doc, dodo['task_list'][0].doc


    def testSetCwd(self, cwd):
        fileName = os.path.join(os.path.dirname(__file__),"loader_sample.py")
        cwd = os.path.join(os.path.dirname(__file__), "data")
        get_module(fileName, cwd)
        assert os.getcwd() == cwd, os.getcwd()


    def testInvalidCwd(self, cwd):
        fileName = os.path.join(os.path.dirname(__file__),"loader_sample.py")
        cwd = os.path.join(os.path.dirname(__file__), "dataX")
        pytest.raises(InvalidCommand, get_module, fileName, cwd)


class TestGetTasks(object):
    def test(self, cwd):
        fileName = os.path.join(os.path.dirname(__file__),"loader_sample.py")
        expected = ["xxx1","yyy2"]
        dodo = get_tasks(fileName, None, False, [])
        assert expected == [t.name for t in dodo['task_list']]


class TestDodoConfig(object):
    # to avoid creating many files for testing i am modifying the module
    # dynamically. but it is tricky because python optmizes it and loads
    # it just once. so need to clean up variables that i messed up.

    def pytest_funcarg__dodo(self, request):
        def get_dodo_module():
            fileName = os.path.join(os.path.dirname(__file__),
                                    "loader_sample.py")
            return get_module(fileName)
        def remove_dodo(dodo):
            if hasattr(dodo, 'DOIT_CONFIG'):
                del dodo.DOIT_CONFIG
        return request.cached_setup(
            setup=get_dodo_module,
            teardown=remove_dodo,
            scope="function")


    def testDefaultConfig_Dict(self, cwd, dodo):
        dodo_dict = load_task_generators(dodo)
        assert {} == dodo_dict['config']

    def testConfigType_Error(self, cwd, dodo):
        dodo.DOIT_CONFIG = "abcd"
        pytest.raises(InvalidDodoFile, load_task_generators, dodo)

    def testConfigDict_Ok(self, cwd, dodo):
        dodo.DOIT_CONFIG = {"abcd": "add"}
        dodo_dict = load_task_generators(dodo)
        assert {"abcd": "add"} == dodo_dict['config']


