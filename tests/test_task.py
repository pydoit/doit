# coding=UTF-8

import os, shutil
import tempfile
from StringIO import StringIO

import pytest

from doit.exceptions import TaskError
from doit.exceptions import CatchedException
from doit import action
from doit import task

#path to test folder
TEST_PATH = os.path.dirname(__file__)
PROGRAM = "python %s/sample_process.py" % TEST_PATH




class TestTaskCheckInput(object):

    def testOkType(self):
        task.Task.check_attr('xxx', 'attr', [], ([int, list],[]))

    def testOkValue(self):
        task.Task.check_attr('xxx', 'attr', None, ([list], [None]))

    def testFailType(self):
        pytest.raises(task.InvalidTask, task.Task.check_attr, 'xxx',
                      'attr', int, ([list], [False]))

    def testFailValue(self):
        pytest.raises(task.InvalidTask, task.Task.check_attr, 'xxx',
                      'attr', True, ([list], [False]))



class TestTaskInit(object):

    def test_groupTask(self):
        # group tasks have no action
        t = task.Task("taskX", None)
        assert t.actions == []

    def test_dependencySequenceIsValid(self):
        task.Task("Task X", ["taskcmd"], file_dep=["123","456"])

    # dependency must be a sequence or bool.
    # give proper error message when anything else is used.
    def test_dependencyNotSequence(self):
        filePath = "data/dependency1"
        pytest.raises(task.InvalidTask, task.Task,
                      "Task X",["taskcmd"], file_dep=filePath)

    def test_options(self):
        # when task is created, options contain the default values
        p1 = {'name':'p1', 'default':'p1-default'}
        p2 = {'name':'p2', 'default':'', 'short':'m'}
        t = task.Task("MyName", None, params=[p1, p2])
        t._init_options()
        assert 'p1-default' == t.options['p1']
        assert '' == t.options['p2']

    def test_setup(self):
        t = task.Task("task5", ['action'], setup=["task2"])
        assert ["task2"] == t.setup_tasks

    def test_run_status(self):
        t = task.Task("t", ["q"])
        assert t.run_status is None


class TestTaskInsertAction(object):
    def test_insert_action(self):
        t = task.Task("Task X", ["taskcmd"])
        def void(task, values, (my_arg1,)): pass
        t.insert_action((void, [1]))
        assert 2 == len(t.actions)


class TestTaskUpToDate(object):

    def test_FalseRunalways(self):
        t = task.Task("Task X", ["taskcmd"], uptodate=[False])
        assert t.uptodate == [(False, None, None)]

    def test_NoneIgnored(self):
        t = task.Task("Task X", ["taskcmd"], uptodate=[None])
        assert t.uptodate == [(None, None, None)]

    def test_callable_function(self):
        def custom_check(): return True
        t = task.Task("Task X", ["taskcmd"], uptodate=[custom_check])
        assert t.uptodate[0] == (custom_check, [], {})

    def test_callable_instance_method(self):
        class Base(object):
            def check(): return True
        base = Base()
        t = task.Task("Task X", ["taskcmd"], uptodate=[base.check])
        assert t.uptodate[0] == (base.check, [], {})

    def test_tuple(self):
        def custom_check(pos_arg, xxx=None): return True
        t = task.Task("Task X", ["taskcmd"],
                      uptodate=[(custom_check, [123], {'xxx':'yyy'})])
        assert t.uptodate[0] == (custom_check, [123], {'xxx':'yyy'})

    def test_invalid(self):
        pytest.raises(task.InvalidTask,
                      task.Task, "Task X", ["taskcmd"], uptodate=[{'x':'y'}])


class TestTaskExpandFileDep(object):

    def test_dependencyStringIsFile(self):
        my_task = task.Task("Task X", ["taskcmd"], file_dep=["123","456"])
        assert set(["123","456"]) == my_task.file_dep

    def test_file_dep_must_be_string(self):
        pytest.raises(task.InvalidTask, task.Task, "Task X", ["taskcmd"],
                       file_dep=[['aaaa']])

    def test_file_dep_unicode(self):
        unicode_name = u"中文"
        my_task = task.Task("Task X", ["taskcmd"], file_dep=[unicode_name])
        assert unicode_name in my_task.file_dep


class TestTaskDeps(object):

    def test_task_dep(self):
        my_task = task.Task("Task X", ["taskcmd"], task_dep=["123","4*56"])
        assert ["123"] == my_task.task_dep
        assert ["4*56"] == my_task.wild_dep

    def test_expand_result(self):
        my_task = task.Task("Task X", ["taskcmd"], result_dep=["123"])
        assert ["123"] == my_task.result_dep
        assert ["123"] == my_task.task_dep

    def test_calc_dep(self):
        my_task = task.Task("Task X", ["taskcmd"], calc_dep=["123"])
        assert set(["123"]) == my_task.calc_dep
        assert ["123"] == my_task.calc_dep_stack

    def test_update_deps(self):
        my_task = task.Task("Task X", ["taskcmd"], file_dep=["fileX"],
                            calc_dep=["calcX"], result_dep=["resultX"],
                            uptodate=[None])
        my_task.update_deps({'file_dep': ['fileY'],
                             'task_dep': ['taskY'],
                             'calc_dep': ['calcX', 'calcY'],
                             'result_dep': ['resultY'],
                             'uptodate': [True],
                             })
        assert set(['fileX', 'fileY']) == my_task.file_dep
        assert ['resultX', 'taskY', 'resultY'] == my_task.task_dep
        assert set(['calcX', 'calcY']) == my_task.calc_dep
        assert ['resultX', 'resultY'] == my_task.result_dep
        assert [(None, None, None), (True, None, None)] == my_task.uptodate


class TestTask_Getargs(object):
    def test_ok(self):
        getargs = {'x' : 't1.x', 'y': 't2.z'}
        t = task.Task('t3', None, getargs=getargs)
        assert 't1' in t.setup_tasks
        assert 't2' in t.setup_tasks

    def test_invalid_desc(self):
        getargs = {'x' : 't1'}
        assert pytest.raises(task.InvalidTask, task.Task,
                              't3', None, getargs=getargs)

    def test_many_dots(self):
        getargs = {'x': 't2:file.ext.x'}
        t = task.Task('t1', None, getargs=getargs)
        assert 't2:file.ext' in t.setup_tasks


class TestTaskTitle(object):

    def test_title(self):
        t = task.Task("MyName",["MyAction"])
        assert "MyName" == t.title()


    def test_custom_title(self):
        t = task.Task("MyName",["MyAction"], title=(lambda x: "X%sX" % x.name))
        assert "X%sX"%str(t.name) == t.title(), t.title()



class TestTaskRepr(object):

    def test_repr(self):
        t = task.Task("taskX",None,('t1','t2'))
        assert "<Task: taskX>" == repr(t), repr(t)


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
            import sys # python3 2to3 cant handle print with a trailing comma
            sys.stdout.write(msg)
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
                open(filename, 'a').close()
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
            fh = open(c_path, 'a')
            fh.write("hello!!!")
            fh.close()
        t = task.Task("xxx",None,targets=tmpdir['files'], clean=[(say_hello,)])
        assert False == t._remove_targets
        assert 1 == len(t.clean_actions)
        t.clean(StringIO(), False)
        for filename in tmpdir['files']:
            assert os.path.exists(filename)
        fh = open(c_path, 'r')
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
        pytest.raises(action.InvalidTask, task.dict_to_task, dict_)

    def testDictMissingFieldAction(self):
        pytest.raises(action.InvalidTask, task.dict_to_task, {'name':'xpto 14'})

