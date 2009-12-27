import os

import py.test

from doit.task import InvalidTask, Task
from doit.main import InvalidDodoFile, InvalidCommand
from doit.main import isgenerator, get_module
from doit.main import load_task_generators, generate_tasks, TaskSetup



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


class TestDodoDefaultTasks(object):
    # to avoid creating many files for testing i am modifying the module
    # dynamically. but it is tricky because python optmizes it and loads
    # it just once. so need to clean up variables that i messed up.

    def pytest_funcarg__dodo(self, request):
        def get_dodo_module():
            fileName = os.path.join(os.path.dirname(__file__),
                                    "loader_sample.py")
            return get_module(fileName)
        def remove_dodo(dodo):
            if hasattr(dodo, 'DEFAULT_TASKS'):
                del dodo.DEFAULT_TASKS
        return request.cached_setup(
            setup=get_dodo_module,
            teardown=remove_dodo,
            scope="function")


    def testDefaultTasks_None(self, dodo):
        dodo_dict = load_task_generators(dodo)
        assert None == dodo_dict['default_tasks']

    def testDefaultTasks_Error(self, dodo):
        dodo.DEFAULT_TASKS = "abcd"
        py.test.raises(InvalidDodoFile, load_task_generators, dodo)

    def testDefaultTasks_Ok(self, dodo):
        dodo.DEFAULT_TASKS = ["abcd", "add"]
        dodo_dict = load_task_generators(dodo)
        assert ["abcd", "add"] == dodo_dict['default_tasks']


class TestTaskSetupInit(object):

    def test_addTask(self):
        t1 = Task("taskX", None)
        t2 = Task("taskY", None)
        ts = TaskSetup([t1, t2])
        assert 2 == len(ts.tasks)

    def test_targetDependency(self):
        t1 = Task("taskX", None,[],['intermediate'])
        t2 = Task("taskY", None,['intermediate'],[])
        TaskSetup([t1,t2])
        assert ['taskX'] == t2.task_dep

    # 2 tasks can not have the same name
    def test_addTaskSameName(self):
        t1 = Task("taskX", None)
        t2 = Task("taskX", None)
        py.test.raises(InvalidDodoFile, TaskSetup, [t1, t2])

    def test_addInvalidTask(self):
        py.test.raises(InvalidTask, TaskSetup, [666])

    def test_userErrorTaskDependency(self):
        tasks = [Task('wrong', None,[":typo"])]
        py.test.raises(InvalidTask, TaskSetup, tasks)

    def test_sameTarget(self):
        tasks = [Task('t1',None,[],["fileX"]),
                 Task('t2',None,[],["fileX"])]
        py.test.raises(InvalidTask, TaskSetup, tasks)



TASKS_SAMPLE = [Task("t1", [""], doc="t1 doc string"),
                Task("t2", [""], doc="t2 doc string"),
                Task("g1", None, doc="g1 doc string"),
                Task("g1.a", [""], doc="g1.a doc string", is_subtask=True),
                Task("g1.b", [""], doc="g1.b doc string", is_subtask=True),
                Task("t3", [""], doc="t3 doc string",
                     params=[{'name':'opt1','long':'message','default':''}])]


class TestTaskSetupCmdOptions(object):
    def testFilter(self):
        filter_ = ['t2', 't3']
        ts = TaskSetup(TASKS_SAMPLE, filter_)
        assert filter_ == ts._filter_tasks()

    def testFilterSubtask(self):
        filter_ = ["t1", "g1.b"]
        ts =  TaskSetup(TASKS_SAMPLE, filter_)
        assert filter_ == ts._filter_tasks()

    def testFilterTarget(self):
        tasks = list(TASKS_SAMPLE)
        tasks.append(Task("tX", [""],[],["targetX"]))
        ts =  TaskSetup(tasks, ["targetX"])
        assert ['tX'] == ts._filter_tasks()

    # filter a non-existent task raises an error
    def testFilterWrongName(self):
        ts =  TaskSetup(TASKS_SAMPLE, ['no'])
        py.test.raises(InvalidCommand, ts._filter_tasks)

    def testFilterEmptyList(self):
        filter_ = []
        ts = TaskSetup(TASKS_SAMPLE, filter_)
        assert filter_ == ts.process()

    def testOptions(self):
        options = ["t3", "--message", "hello option!", "t1"]
        ts = TaskSetup(TASKS_SAMPLE, options)
        assert ['t3', 't1'] == ts.filter
        assert "hello option!" == ts.tasks['t3'].options['opt1']


class TestOrderTasks(object):
    # same task is not added twice
    def testAddJustOnce(self):
        ts = TaskSetup([Task("taskX", None)])
        result = ts._order_tasks(["taskX"]*2)
        assert 1 == len(result)

    def testDetectCyclicReference(self):
        tasks = [Task("taskX",None,[":taskY"]),
                 Task("taskY",None,[":taskX"])]
        ts = TaskSetup(tasks)
        py.test.raises(InvalidDodoFile, ts._order_tasks,
                                 ["taskX", "taskY"])

