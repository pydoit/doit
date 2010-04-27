import os, shutil
import tempfile
from StringIO import StringIO

import py.test

from doit.exceptions import TaskError
from doit.exceptions import CatchedException
from doit import action
from doit import task

#path to test folder
TEST_PATH = os.path.dirname(__file__)
PROGRAM = "python %s/sample_process.py" % TEST_PATH




class TestTaskCheckInput(object):

    def testOkType(self):
        task.Task.check_attr_input('xxx', 'attr', [], [int, list])

    def testOkValue(self):
        task.Task.check_attr_input('xxx', 'attr', None, [list, None])

    def testFailType(self):
        py.test.raises(task.InvalidTask, task.Task.check_attr_input, 'xxx',
                      'attr', int, [list, False])

    def testFailValue(self):
        py.test.raises(task.InvalidTask, task.Task.check_attr_input, 'xxx',
                      'attr', True, [list, False])



class TestTask(object):

    def test_groupTask(self):
        # group tasks have no action
        t = task.Task("taskX", None)
        assert t.actions == []

    def test_repr(self):
        t = task.Task("taskX",None,('t1','t2'))
        assert "<Task: taskX>" == repr(t), repr(t)

    def test_dependencySequenceIsValid(self):
        task.Task("Task X", ["taskcmd"], dependencies=["123","456"])

    # dependency must be a sequence or bool.
    # give proper error message when anything else is used.
    def test_dependencyNotSequence(self):
        filePath = "data/dependency1"
        py.test.raises(task.InvalidTask, task.Task,
                      "Task X",["taskcmd"], dependencies=filePath)

    # dependency types going to the write place
    def test_dependencyTypes(self):
        dep = ["file1.txt",":taskX","file2", "?res1", ":stu*"]
        t = task.Task("MyName", ["MyAction"], dep)
        assert t.task_dep == [dep[1][1:], dep[3][1:]]
        assert t.file_dep == [dep[0],dep[2]]
        assert t.result_dep == [dep[3][1:]]
        assert t.wild_dep == [dep[4][1:]]

    def test_dependencyTrueRunonce(self):
        t = task.Task("Task X",["taskcmd"], dependencies=[True])
        assert t.run_once

    def test_dependencyFalseRunalways(self):
        t = task.Task("Task X",["taskcmd"], dependencies=[False])
        assert t.run_always

    def test_dependencyNoneIgnored(self):
        t = task.Task("Task X",["taskcmd"], dependencies=[None])
        assert not t.run_once
        assert not t.run_always

    def test_dependencyValueInvalid(self):
        py.test.raises(task.InvalidTask, task.Task,
                      "Task X",["taskcmd"], dependencies=[123])

    def test_runOnce_or_fileDependency(self):
        py.test.raises(task.InvalidTask, task.Task,
                      "Task X",["taskcmd"], dependencies=[True,"whatever"])


    def test_title(self):
        t = task.Task("MyName",["MyAction"])
        assert "MyName" == t.title()


    def test_custom_title(self):
        t = task.Task("MyName",["MyAction"], title=(lambda x: "X%sX" % x.name))
        assert "X%sX"%str(t.name) == t.title(), t.title()

    def test_options(self):
        # when task is created, options contain the default values
        p1 = {'name':'p1', 'default':'p1-default'}
        p2 = {'name':'p2', 'default':'', 'short':'m'}
        t = task.Task("MyName", None, params=[p1, p2])
        assert 'p1-default' == t.options['p1']
        assert '' == t.options['p2']

    def test_setup(self):
        # 2 kinds of setup: old-object, new-task_name
        class MySetup:pass
        setup_obj = MySetup()
        t = task.Task("task5", ['action'], setup=[setup_obj, "task2"])
        assert [setup_obj] == t.setup
        assert ["task2"] == t.setup_tasks

    def test_run_status(self):
        t = task.Task("t", ["q"])
        assert t.run_status is None


class TestTask_Getargs(object):
    def test_ok(self):
        getargs = {'x' : 't1.x', 'y': 't2.z'}
        t = task.Task('t3', None, getargs=getargs)
        assert 't1' in t.task_dep
        assert 't2' in t.task_dep

    def test_invalid_desc(self):
        getargs = {'x' : 't1'}
        assert py.test.raises(task.InvalidTask, task.Task,
                              't3', None, getargs=getargs)


class TestTaskActions(object):
    def test_success(self):
        t = task.Task("taskX", [PROGRAM])
        t.execute()


    def test_result(self):
        # task.result is the value of last action
        t = task.Task('t1', ["%s hi_list hi1" % PROGRAM,
                             "%s hi_list hi2" % PROGRAM])
        t.execute()
        assert "hi_listhi2" == t.result

    def test_values(self):
        def return_dict(d): return d
        # task.result is the value of last action
        t = task.Task('t1', [(return_dict, [{'x':5}]),
                             (return_dict, [{'y':10}]),])
        t.execute()
        assert {'x':5, 'y':10} == t.values

    def test_failure(self):
        t = task.Task("taskX", ["%s 1 2 3" % PROGRAM])
        got = t.execute()
        assert isinstance(got, TaskError)

    # make sure all cmds are being executed.
    def test_many(self):
        t = task.Task("taskX",["%s hi_stdout hi2" % PROGRAM,
                               "%s hi_list hi6" % PROGRAM])
        t.execute()
        got = "".join([a.out for a in t.actions])
        assert "hi_stdouthi_list" == got, repr(got)


    def test_fail_first(self):
        t = task.Task("taskX", ["%s 1 2 3" % PROGRAM, PROGRAM])
        got = t.execute()
        assert isinstance(got, TaskError)

    def test_fail_second(self):
        t = task.Task("taskX", ["%s 1 2" % PROGRAM, "%s 1 2 3" % PROGRAM])
        got = t.execute()
        assert isinstance(got, TaskError)


    # python and commands mixed on same task
    def test_mixed(self):
        def my_print(msg):
            print msg,
        t = task.Task("taskX",["%s hi_stdout hi2" % PROGRAM,
                               (my_print,['_PY_']),
                               "%s hi_list hi6" % PROGRAM])
        t.execute()
        got = "".join([a.out for a in t.actions])
        assert "hi_stdout_PY_hi_list" == got, repr(got)


class TestTaskTeardown(object):
    def test_ok(self):
        got = []
        def put(x):
            got.append(x)
        t = task.Task('t1', [], teardown=[(put, [1]), (put, [2])])
        assert None == t.execute_teardown()
        assert [1,2] == got

    def test_fail(self):
        def my_raise():
            raise Exception('hoho')
        t = task.Task('t1', [], teardown=[(my_raise,)])
        got = t.execute_teardown()
        assert isinstance(got, CatchedException)


class TestTaskClean(object):

    def pytest_funcarg__tmpdir(self, request):
        def create_tmpdir():
            tmpdir = {}
            tmpdir['dir'] = tempfile.mkdtemp(prefix='doit-')
            files = [os.path.join(tmpdir['dir'], fname)
                     for fname in ['a.txt', 'b.txt']]
            tmpdir['files'] = files
            # create empty files
            for filename in tmpdir['files']:
                file(filename, 'a').close()
            return tmpdir
        def remove_tmpdir(tmpdir):
            if os.path.exists(tmpdir['dir']):
                shutil.rmtree(tmpdir['dir'])
        return request.cached_setup(
            setup=create_tmpdir,
            teardown=remove_tmpdir,
            scope="function")


    def test_clean_nothing(self, tmpdir):
        t = task.Task("xxx", None)
        assert False == t._remove_targets
        assert 0 == len(t.clean_actions)
        t.clean(StringIO(), False)
        for filename in tmpdir['files']:
            assert os.path.exists(filename)

    def test_clean_targets(self, tmpdir):
        t = task.Task("xxx", None, targets=tmpdir['files'], clean=True)
        assert True == t._remove_targets
        assert 0 == len(t.clean_actions)
        t.clean(StringIO(), False)
        for filename in tmpdir['files']:
            assert not os.path.exists(filename), filename

    def test_clean_non_existent_targets(self):
        t = task.Task('xxx', None, targets=["i_dont_exist"], clean=True)
        t.clean(StringIO(), False)
        # nothing is raised

    def test_clean_empty_dirs(self, tmpdir):
        # Remove empty directories listed in targets
        targets = tmpdir['files'] + [tmpdir['dir']]
        t = task.Task("xxx", None, targets=targets, clean=True)
        assert True == t._remove_targets
        assert 0 == len(t.clean_actions)
        t.clean(StringIO(), False)
        for filename in tmpdir['files']:
            assert not os.path.exists(filename)
        assert not os.path.exists(tmpdir['dir'])

    def test_keep_non_empty_dirs(self, tmpdir):
        # Keep non empty directories listed in targets
        targets = [tmpdir['files'][0], tmpdir['dir']]
        t = task.Task("xxx", None, targets=targets, clean=True)
        assert True == t._remove_targets
        assert 0 == len(t.clean_actions)
        t.clean(StringIO(), False)
        for filename in tmpdir['files']:
            expected = not filename in targets
            assert expected == os.path.exists(filename)
        assert os.path.exists(tmpdir['dir'])

    def test_clean_actions(self, tmpdir):
        # a clean action can be anything, it can even not clean anything!
        c_path = tmpdir['files'][0]
        def say_hello():
            fh = file(c_path, 'a')
            fh.write("hello!!!")
            fh.close()
        t = task.Task("xxx",None,targets=tmpdir['files'], clean=[(say_hello,)])
        assert False == t._remove_targets
        assert 1 == len(t.clean_actions)
        t.clean(StringIO(), False)
        for filename in tmpdir['files']:
            assert os.path.exists(filename)
        fh = file(c_path, 'r')
        got = fh.read()
        fh.close()
        assert "hello!!!" == got

    def test_dryrun_file(self, tmpdir):
        t = task.Task("xxx", None, targets=tmpdir['files'], clean=True)
        assert True == t._remove_targets
        assert 0 == len(t.clean_actions)
        t.clean(StringIO(), True)
        # files are NOT removed
        for filename in tmpdir['files']:
            assert os.path.exists(filename), filename

    def test_dryrun_dir(self, tmpdir):
        targets = tmpdir['files'] + [tmpdir['dir']]
        for filename in tmpdir['files']:
            os.remove(filename)
        t = task.Task("xxx", None, targets=targets, clean=True)
        assert True == t._remove_targets
        assert 0 == len(t.clean_actions)
        t.clean(StringIO(), True)
        assert os.path.exists(tmpdir['dir'])

    def test_dryrun_actions(self, tmpdir):
        # a clean action can be anything, it can even not clean anything!
        self.executed = False
        def say_hello(): self.executed = True
        t = task.Task("xxx",None,targets=tmpdir['files'], clean=[(say_hello,)])
        assert False == t._remove_targets
        assert 1 == len(t.clean_actions)
        t.clean(StringIO(), True)
        assert not self.executed



class TestTaskDoc(object):
    def test_no_doc(self):
        t = task.Task("name", ["action"])
        assert '' == t.doc

    def test_single_line(self):
        t = task.Task("name", ["action"], doc="  i am doc")
        assert "i am doc" == t.doc

    def test_multiple_lines(self):
        t = task.Task("name", ["action"], doc="i am doc  \n with many lines\n")
        assert "i am doc" == t.doc

    def test_start_with_empty_lines(self):
        t = task.Task("name", ["action"], doc="\n\n i am doc \n")
        assert "i am doc" == t.doc

    def test_just_new_line(self):
        t = task.Task("name", ["action"], doc="  \n  \n\n")
        assert "" == t.doc


class TestDictToTask(object):
    def testDictOkMinimum(self):
        dict_ = {'name':'simple','actions':['xpto 14']}
        assert isinstance(task.dict_to_task(dict_), task.Task)

    def testDictFieldTypo(self):
        dict_ = {'name':'z','actions':['xpto 14'],'typo_here':['xxx']}
        py.test.raises(action.InvalidTask, task.dict_to_task, dict_)

    def testDictMissingFieldAction(self):
        py.test.raises(action.InvalidTask, task.dict_to_task, {'name':'xpto 14'})


class TestCmdExpandAction(object):

    def test_task_meta_reference(self):
        cmd = "python %s/myecho.py" % TEST_PATH
        cmd += " %(dependencies)s - %(changed)s - %(targets)s"
        dependencies = ["data/dependency1", "data/dependency2", ":dep_on_task"]
        targets = ["data/target", "data/targetXXX"]
        t = task.Task('formating', [cmd], dependencies, targets)
        t.dep_changed = ["data/dependency1"]
        t.execute()

        got = t.actions[0].out.split('-')
        assert t.file_dep == got[0].split(), got[0]
        assert t.dep_changed == got[1].split(), got[1]
        assert targets == got[2].split(), got[2]

    def test_task_options(self):
        cmd = "python %s/myecho.py" % TEST_PATH
        cmd += " %(opt1)s - %(opt2)s"
        t = task.Task('with_options', [cmd])
        t.options = {'opt1':'3', 'opt2':'abc def'}
        t.execute()
        got = t.actions[0].out.strip()
        assert "3 - abc def" == got, repr(got)



class TestPythonActionPrepareKwargsMeta(object):

    def pytest_funcarg__task_depchanged(self, request):
        def create_task_depchanged():
            t_depchanged = task.Task('name',None,['dependencies'],['targets'])
            t_depchanged.dep_changed = ['changed']
            return t_depchanged
        return request.cached_setup(
            setup=create_task_depchanged,
            scope="function")

    def test_no_extra_args(self, task_depchanged):
        def py_callable():
            return True
        my_action = action.PythonAction(py_callable)
        my_action.task = task_depchanged
        my_action.execute()

    def test_keyword_extra_args(self, task_depchanged):
        got = []
        def py_callable(arg=None, **kwargs):
            got.append(kwargs['targets'])
            got.append(kwargs['dependencies'])
            got.append(kwargs['changed'])
        my_action = action.PythonAction(py_callable)
        my_action.task = task_depchanged
        my_action.execute()
        assert got == [['targets'], ['dependencies'], ['changed']], got

    def test_named_extra_args(self, task_depchanged):
        got = []
        def py_callable(targets, dependencies, changed):
            got.append(targets)
            got.append(dependencies)
            got.append(changed)
        my_action = action.PythonAction(py_callable)
        my_action.task = task_depchanged
        my_action.execute()
        assert got == [['targets'], ['dependencies'], ['changed']]

    def test_mixed_args(self, task_depchanged):
        got = []
        def py_callable(a, b, changed):
            got.append(a)
            got.append(b)
            got.append(changed)
        my_action = action.PythonAction(py_callable, ('a', 'b'))
        my_action.task = task_depchanged
        my_action.execute()
        assert got == ['a', 'b', ['changed']]

    def test_extra_arg_overwritten(self, task_depchanged):
        got = []
        def py_callable(a, b, changed):
            got.append(a)
            got.append(b)
            got.append(changed)
        my_action = action.PythonAction(py_callable, ('a', 'b', 'c'))
        my_action.task = task_depchanged
        my_action.execute()
        assert got == ['a', 'b', 'c']

    def test_extra_kwarg_overwritten(self, task_depchanged):
        got = []
        def py_callable(a, b, **kwargs):
            got.append(a)
            got.append(b)
            got.append(kwargs['changed'])
        my_action = action.PythonAction(py_callable, ('a', 'b'), {'changed': 'c'})
        my_action.task = task_depchanged
        my_action.execute()
        assert got == ['a', 'b', 'c']

    def test_extra_arg_default_disallowed(self, task_depchanged):
        def py_callable(a, b, changed=None): pass
        my_action = action.PythonAction(py_callable, ('a', 'b'))
        my_action.task = task_depchanged
        py.test.raises(task.InvalidTask, my_action.execute)

class TestPythonActionOptions(object):
    def test_task_options(self):
        got = []
        def py_callable(opt1, opt3):
            got.append(opt1)
            got.append(opt3)
        t = task.Task('with_options', [py_callable])
        t.options = {'opt1':'1', 'opt2':'abc def', 'opt3':3}
        t.execute()
        assert ['1',3] == got, repr(got)

