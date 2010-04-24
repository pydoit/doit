import os

import py.test

from doit.task import InvalidTask, Task
from doit.main import InvalidDodoFile, InvalidCommand
from doit.main import isgenerator, get_module
from doit.main import load_task_generators, generate_tasks, TaskControl
from doit.main import get_tasks



class TestIsGenerator(object):
    def testIsGeneratorYes(self):
        def giveme():
            for i in range(3):
                yield i
        g = giveme()
        assert isgenerator(g)
        for i in g: pass # just to get coverage on the givme function

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
        py.test.raises(InvalidTask, generate_tasks, "dict",
                                 {'actions':['xpto 14'],'name':'bla bla'})

    def testInvalidValue(self):
        py.test.raises(InvalidTask, generate_tasks, "dict",'xpto 14')

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
        py.test.raises(InvalidTask, generate_tasks,"xpto",
                                 f_xpto())

    def testGeneratorDictMissingName(self):
        def f_xpto():
            for i in range(3):
                yield {'actions' :["xpto -%d"%i]}
        py.test.raises(InvalidTask, generate_tasks,"xpto",
                                 f_xpto())

    def testGeneratorDictMissingAction(self):
        def f_xpto():
            for i in range(3):
                yield {'name':str(i)}
        py.test.raises(InvalidTask, generate_tasks,"xpto",
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
    def testAbsolutePath(self):
        fileName = os.path.join(os.path.dirname(__file__),"loader_sample.py")
        expected = ["xxx1","yyy2"]
        dodo_module = get_module(fileName)
        dodo = load_task_generators(dodo_module)
        assert expected == [t.name for t in dodo['task_list']]

    def testRelativePath(self):
        # test relative import but test should still work from any path
        # so change cwd.
        os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__),'..')))
        fileName = "tests/loader_sample.py"
        expected = ["xxx1","yyy2"]
        dodo_module = get_module(fileName)
        dodo = load_task_generators(dodo_module)
        assert expected == [t.name for t in dodo['task_list']]

    def testNameInBlacklist(self):
        fileName = os.path.join(os.path.dirname(__file__),"loader_sample.py")
        dodo_module = get_module(fileName)
        py.test.raises(InvalidDodoFile, load_task_generators,
                                 dodo_module, ['yyy2'])

    def testWrongFileName(self):
        fileName = os.path.join(os.path.dirname(__file__),"i_dont_exist.py")
        py.test.raises(InvalidDodoFile, get_module, fileName)


    def testDocString(self):
        fileName = os.path.join(os.path.dirname(__file__),"loader_sample.py")
        dodo_module = get_module(fileName)
        dodo = load_task_generators(dodo_module)
        assert "task doc" == dodo['task_list'][0].doc, dodo['task_list'][0].doc


    def testSetCwd(self):
        fileName = os.path.join(os.path.dirname(__file__),"loader_sample.py")
        cwd = os.path.join(os.path.dirname(__file__), "data")
        get_module(fileName, cwd)
        assert os.getcwd() == cwd, os.getcwd()


    def testInvalidCwd(self):
        fileName = os.path.join(os.path.dirname(__file__),"loader_sample.py")
        cwd = os.path.join(os.path.dirname(__file__), "dataX")
        py.test.raises(InvalidCommand, get_module, fileName, cwd)


class TestGetTasks(object):
    def test(self):
        fileName = os.path.join(os.path.dirname(__file__),"loader_sample.py")
        expected = ["xxx1","yyy2"]
        dodo = get_tasks(fileName, None, [])
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
            if hasattr(dodo, 'DEFAULT_TASKS'):
                del dodo.DEFAULT_TASKS
        return request.cached_setup(
            setup=get_dodo_module,
            teardown=remove_dodo,
            scope="function")


    def testDefaultConfig_Dict(self, dodo):
        dodo_dict = load_task_generators(dodo)
        assert {} == dodo_dict['config']

    def testConfigType_Error(self, dodo):
        dodo.DOIT_CONFIG = "abcd"
        py.test.raises(InvalidDodoFile, load_task_generators, dodo)

    def testConfigDict_Ok(self, dodo):
        dodo.DOIT_CONFIG = {"abcd": "add"}
        dodo_dict = load_task_generators(dodo)
        assert {"abcd": "add"} == dodo_dict['config']

    # default_tasks deprecation
    def testDefaultTasks(self, dodo):
        dodo.DEFAULT_TASKS = ["abcd", "add"]
        dodo_dict = load_task_generators(dodo)
        assert ["abcd", "add"] == dodo_dict['config']['default_tasks']


class TestTaskControlInit(object):

    def test_addTask(self):
        t1 = Task("taskX", None)
        t2 = Task("taskY", None)
        tc = TaskControl([t1, t2])
        assert 2 == len(tc.tasks)

    def test_targetDependency(self):
        t1 = Task("taskX", None,[],['intermediate'])
        t2 = Task("taskY", None,['intermediate'],[])
        TaskControl([t1,t2])
        assert ['taskX'] == t2.task_dep

    # 2 tasks can not have the same name
    def test_addTaskSameName(self):
        t1 = Task("taskX", None)
        t2 = Task("taskX", None)
        py.test.raises(InvalidDodoFile, TaskControl, [t1, t2])

    def test_addInvalidTask(self):
        py.test.raises(InvalidTask, TaskControl, [666])

    def test_userErrorTaskDependency(self):
        tasks = [Task('wrong', None,[":typo"])]
        py.test.raises(InvalidTask, TaskControl, tasks)

    def test_sameTarget(self):
        tasks = [Task('t1',None,[],["fileX"]),
                 Task('t2',None,[],["fileX"])]
        py.test.raises(InvalidTask, TaskControl, tasks)



TASKS_SAMPLE = [Task("t1", [""], doc="t1 doc string"),
                Task("t2", [""], doc="t2 doc string"),
                Task("g1", None, doc="g1 doc string"),
                Task("g1.a", [""], doc="g1.a doc string", is_subtask=True),
                Task("g1.b", [""], doc="g1.b doc string", is_subtask=True),
                Task("t3", [""], doc="t3 doc string",
                     params=[{'name':'opt1','long':'message','default':''}])]


class TestTaskControlCmdOptions(object):
    def testFilter(self):
        filter_ = ['t2', 't3']
        tc = TaskControl(TASKS_SAMPLE)
        assert filter_ == tc.filter_tasks(filter_)

    def testFilterPattern(self):
        tc = TaskControl(TASKS_SAMPLE)
        assert ['t1', 'g1', 'g1.a', 'g1.b'] == tc.filter_tasks(['*1*'])

    def testFilterSubtask(self):
        filter_ = ["t1", "g1.b"]
        tc =  TaskControl(TASKS_SAMPLE)
        assert filter_ == tc.filter_tasks(filter_)

    def testFilterTarget(self):
        tasks = list(TASKS_SAMPLE)
        tasks.append(Task("tX", [""],[],["targetX"]))
        tc =  TaskControl(tasks)
        assert ['tX'] == tc.filter_tasks(["targetX"])

    # filter a non-existent task raises an error
    def testFilterWrongName(self):
        tc =  TaskControl(TASKS_SAMPLE)
        py.test.raises(InvalidCommand, tc.filter_tasks, ['no'])

    def testFilterEmptyList(self):
        filter_ = []
        tc = TaskControl(TASKS_SAMPLE)
        assert filter_ == tc.filter_tasks(filter_)

    def testOptions(self):
        options = ["t3", "--message", "hello option!", "t1"]
        tc = TaskControl(TASKS_SAMPLE)
        assert ['t3', 't1'] == tc.filter_tasks(options)
        assert "hello option!" == tc.tasks['t3'].options['opt1']


class TestGetNext(object):
    def testChangeOrder_AddJustOnce(self):
        tasks = [Task("taskX",None,[":taskY"]),
                 Task("taskY",None,)]
        tc = TaskControl(tasks)
        tc.process(None)
        assert [tasks[1], tasks[0]] == [x for x in tc.get_next_task()]

    def testAddNotSelected(self):
        tasks = [Task("taskX",None,[":taskY"]),
                 Task("taskY",None,)]
        tc = TaskControl(tasks)
        tc.process(['taskX'])
        assert [tasks[1], tasks[0]] == [x for x in tc.get_next_task()]

    def testDetectCyclicReference(self):
        tasks = [Task("taskX",None,[":taskY"]),
                 Task("taskY",None,[":taskX"])]
        tc = TaskControl(tasks)
        tc.process(None)
        gen = tc.get_next_task()
        py.test.raises(InvalidDodoFile, gen.next)

    def testSetupTasksDontRun(self):
        tasks = [Task("taskX",None,setup=["taskY"]),
                 Task("taskY",None,)]
        tc = TaskControl(tasks)
        tc.process(['taskX'])

        gen = tc.get_next_task()
        assert tasks[0] == gen.next()
        # X is up-to-date
        tasks[0].run_status = 'up-to-date'
        py.test.raises(StopIteration, gen.next)

    def testIncludeSetup(self):
        tasks = [Task("taskX",None,setup=["taskY"]),
                 Task("taskY",None,)]
        tc = TaskControl(tasks)
        tc.process(['taskX'])

        task_list = [t for t in tc.get_next_task(True)]
        assert [tasks[0], tasks[1], tasks[0]] == task_list

    def testSetupTasksRun(self):
        tasks = [Task("taskX",None,setup=["taskY"]),
                 Task("taskY",None,)]
        tc = TaskControl(tasks)
        tc.process(['taskX'])

        gen = tc.get_next_task()
        assert tasks[0] == gen.next()
        # X should run
        tasks[0].run_status = 'run'
        # but it was deferred because it has setup tasks
        assert tasks[1] == gen.next()
        # send X again, now it is ready
        assert tasks[0] == gen.next()
        py.test.raises(StopIteration, gen.next)
