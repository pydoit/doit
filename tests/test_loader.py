import os
import sys

import pytest

from doit.exceptions import InvalidDodoFile, InvalidCommand
from doit.task import InvalidTask, Task
from doit.loader import isgenerator, flat_generator, get_module
from doit.loader import load_tasks, load_doit_config, generate_tasks


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


class TestFlatGenerator(object):
    def test_nested(self):
        def myg(items):
            for x in items:
                yield x
        flat = flat_generator(myg([1, myg([2, myg([3, myg([4, myg([5])])])])]))
        assert [1,2,3,4,5] == [f[0] for f in flat]


class TestGetModule(object):
    def testAbsolutePath(self, cwd):
        fileName = os.path.join(os.path.dirname(__file__),"loader_sample.py")
        dodo_module = get_module(fileName)
        assert hasattr(dodo_module, 'task_xxx1')

    def testRelativePath(self, cwd):
        # test relative import but test should still work from any path
        # so change cwd.
        this_path = os.path.join(os.path.dirname(__file__),'..')
        os.chdir(os.path.abspath(this_path))
        fileName = "tests/loader_sample.py"
        dodo_module = get_module(fileName)
        assert hasattr(dodo_module, 'task_xxx1')

    def testWrongFileName(self):
        fileName = os.path.join(os.path.dirname(__file__),"i_dont_exist.py")
        pytest.raises(InvalidDodoFile, get_module, fileName)

    def testInParentDir(self, cwd):
        os.chdir('data')
        fileName = "loader_sample.py"
        pytest.raises(InvalidDodoFile, get_module, fileName)
        get_module(fileName, seek_parent=True)
        # cwd is changed to location of dodo.py
        assert os.getcwd() == os.path.dirname(os.path.abspath(fileName))

    def testWrongFileNameInParentDir(self, cwd):
        os.chdir('data')
        fileName = os.path.join("i_dont_exist.py")
        pytest.raises(InvalidDodoFile, get_module, fileName, seek_parent=True)

    def testSetCwd(self, cwd):
        fileName = os.path.join(os.path.dirname(__file__),"loader_sample.py")
        cwd = os.path.join(os.path.dirname(__file__), "data")
        get_module(fileName, cwd)
        assert os.getcwd() == cwd, os.getcwd()

    def testInvalidCwd(self, cwd):
        fileName = os.path.join(os.path.dirname(__file__),"loader_sample.py")
        cwd = os.path.join(os.path.dirname(__file__), "dataX")
        pytest.raises(InvalidCommand, get_module, fileName, cwd)


class TestLoadTasks(object):

    @pytest.fixture
    def dodo(self):
        def task_xxx1():
            """task doc"""
            return {'actions':['do nothing']}

        def task_yyy2():
            return {'actions':None}

        def bad_seed(): pass
        task_nono = 5
        task_nono # pyflakes
        return locals()

    def testNormalCase(self, dodo):
        task_list = load_tasks(dodo)
        assert 2 == len(task_list)
        assert 'xxx1' == task_list[0].name
        assert 'yyy2' == task_list[1].name

    def testNameInBlacklist(self):
        dodo_module = {'task_cmd_name': lambda:None}
        pytest.raises(InvalidDodoFile, load_tasks, dodo_module, ['cmd_name'])

    def testDocString(self, dodo):
        task_list = load_tasks(dodo)
        assert "task doc" == task_list[0].doc


class TestDodoConfig(object):

    def testConfigType_Error(self):
        pytest.raises(InvalidDodoFile, load_doit_config, {'DOIT_CONFIG': 'abc'})

    def testConfigDict_Ok(self,):
        config = load_doit_config({'DOIT_CONFIG': {'verbose': 2}})
        assert {'verbose': 2} == config

    def testDefaultConfig_Dict(self):
        config = load_doit_config({'whatever': 2})
        assert {} == config



class TestGenerateTaskInvalid(object):
    def testInvalidValue(self):
        pytest.raises(InvalidTask, generate_tasks, "dict",'xpto 14')


class TestGenerateTasksDict(object):
    def testDict(self):
        tasks = generate_tasks("my_name", {'actions':['xpto 14']})
        assert isinstance(tasks[0], Task)
        assert "my_name" == tasks[0].name

    def testBaseName(self):
        tasks = generate_tasks("function_name", {
                'basename': 'real_task_name',
                'actions':['xpto 14']
                })
        assert isinstance(tasks[0], Task)
        assert "real_task_name" == tasks[0].name

    # name field is only for subtasks.
    def testInvalidNameField(self):
        pytest.raises(InvalidTask, generate_tasks, "my_name",
                                 {'actions':['xpto 14'],'name':'bla bla'})


    def testUseDocstring(self):
        tasks = generate_tasks("dict",{'actions':['xpto 14']}, "my doc")
        assert "my doc" == tasks[0].doc

    def testDocstringNotUsed(self):
        mytask = {'actions':['xpto 14'], 'doc':'from dict'}
        tasks = generate_tasks("dict", mytask, "from docstring")
        assert "from dict" == tasks[0].doc


class TestGenerateTasksGenerator(object):

    def testGenerator(self):
        def f_xpto():
            for i in range(3):
                yield {'name':str(i), 'actions' :["xpto -%d"%i]}
        tasks = sorted(generate_tasks("xpto", f_xpto()))
        assert isinstance(tasks[0], Task)
        assert 4 == len(tasks)
        assert not tasks[0].is_subtask
        assert "xpto:0" == tasks[0].task_dep[0]
        assert "xpto:0" == tasks[1].name
        assert tasks[1].is_subtask

    def testMultiLevelGenerator(self):
        def f_xpto(base_name):
            """second level docstring"""
            for i in range(3):
                name = "%s-%d" % (base_name, i)
                yield {'name':name, 'actions' :["xpto -%d"%i]}
        def f_first_level():
            for i in range(2):
                yield f_xpto(str(i))
        tasks = sorted(generate_tasks("xpto", f_first_level()))
        assert isinstance(tasks[0], Task)
        assert 7 == len(tasks)
        assert not tasks[0].is_subtask
        if sys.version_info >= (2, 6): # not possible on python2.5
            assert f_xpto.__doc__ == tasks[0].doc
        assert tasks[1].is_subtask
        assert "xpto:0-0" == tasks[1].name
        assert "xpto:1-2" == tasks[-1].name


    def testGeneratorDoesntReturnDict(self):
        def f_xpto():
            for i in range(3):
                yield "xpto -%d" % i
        pytest.raises(InvalidTask, generate_tasks, "xpto", f_xpto())

    def testGeneratorDictMissingAction(self):
        def f_xpto():
            for i in range(3):
                yield {'name':str(i)}
        pytest.raises(InvalidTask, generate_tasks, "xpto", f_xpto())


    def testGeneratorDictMissingName(self):
        def f_xpto():
            for i in range(3):
                yield {'actions' :["xpto -%d"%i]}
        pytest.raises(InvalidTask, generate_tasks, "xpto", f_xpto())

    def testGeneratorBasename(self):
        def f_xpto():
            for i in range(3):
                yield {'basename':str(i), 'actions' :["xpto"]}
        tasks = generate_tasks("xpto", f_xpto())
        assert isinstance(tasks[0], Task)
        assert 3 == len(tasks)
        assert "0" == tasks[1].name
        assert not tasks[0].is_subtask
        assert not tasks[1].is_subtask

    def testGeneratorBasenameName(self):
        def f_xpto():
            for i in range(3):
                yield {'basename':'xpto', 'name':str(i), 'actions' :["a"]}
        tasks = sorted(generate_tasks("f_xpto", f_xpto()))
        assert isinstance(tasks[0], Task)
        assert 4 == len(tasks)
        assert "xpto" == tasks[0].name
        assert "xpto:0" == tasks[1].name
        assert not tasks[0].is_subtask
        assert tasks[1].is_subtask

    def testGeneratorBasenameCanNotRepeat(self):
        def f_xpto():
            for i in range(3):
                yield {'basename':'again', 'actions' :["xpto"]}
        pytest.raises(InvalidTask, generate_tasks, "xpto", f_xpto())

    def testGeneratorBasenameCanNotRepeatNonGroup(self):
        def f_xpto():
            yield {'basename': 'xpto', 'actions':["a"]}
            for i in range(3):
                yield {'name': str(i),
                       'actions' :["a"]}
        pytest.raises(InvalidTask, generate_tasks, "xpto", f_xpto())

    def testGeneratorDocString(self):
        def f_xpto():
            "the doc"
            for i in range(3):
                yield {'name':str(i), 'actions' :["xpto -%d"%i]}
        tasks = sorted(generate_tasks("xpto", f_xpto(), f_xpto.__doc__))
        assert "the doc" == tasks[0].doc

    def testGeneratorWithNoTasks(self):
        def f_xpto():
            for x in []: yield x
        tasks = generate_tasks("xpto", f_xpto())
        assert 1 == len(tasks)
        assert "xpto" == tasks[0].name
        assert not tasks[0].is_subtask
