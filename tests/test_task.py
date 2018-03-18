import os, shutil
import tempfile
from io import StringIO
from pathlib import Path, PurePath
from sys import executable

import pytest

from doit.exceptions import TaskError
from doit.exceptions import CatchedException
from doit import action
from doit import task
from doit.task import Stream

#path to test folder
TEST_PATH = os.path.dirname(__file__)
PROGRAM = "%s %s/sample_process.py" % (executable, TEST_PATH)




class TestStream():

    def test_from_task(self):
        # use value from task, not global from Stream
        v0 = Stream(0)
        assert v0.effective_verbosity(1) == 1
        assert v0.effective_verbosity(2) == 2
        v2 = Stream(2)
        assert v2.effective_verbosity(0) == 0
        assert v2.effective_verbosity(1) == 1

    def test_force_global(self):
        # use value from task, not global from Stream
        v0 = Stream(0, force_global=True)
        assert v0.effective_verbosity(2) == 0
        v2 = Stream(2, force_global=True)
        assert v2.effective_verbosity(0) == 2

    def test_task_verbosity_not_specified(self):
        # default
        v0 = Stream(None)
        assert v0.effective_verbosity(None) == 1

        v2 = Stream(2)
        assert v2.effective_verbosity(None) == 2



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



class TestTaskCompare(object):
    def test_equal(self):
        # only task name is used to compare for equality
        t1 = task.Task("foo", None)
        t2 = task.Task("bar", None)
        t3 = task.Task("foo", None)
        assert t1 != t2
        assert t1 == t3


    def test_lt(self):
        # task name is used to compare/sort tasks
        t1 = task.Task("foo", None)
        t2 = task.Task("bar", None)
        t3 = task.Task("gee", None)
        assert t1 > t2
        sorted_names = sorted(t.name for t in (t1,t2,t3))
        assert sorted_names == ['bar', 'foo', 'gee']



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
        t = task.Task("MyName", None, params=[p1, p2], pos_arg='pos')
        t.execute(Stream(0))
        assert 'p1-default' == t.options['p1']
        assert '' == t.options['p2']
        assert 'pos' == t.pos_arg
        assert None == t.pos_arg_val # always unitialized

    def test_setup(self):
        t = task.Task("task5", ['action'], setup=["task2"])
        assert ["task2"] == t.setup_tasks

    def test_forbid_equal_sign_on_name(self):
        pytest.raises(task.InvalidTask,
                      task.Task, "a=1", ["taskcmd"])


class TestTaskValueSavers(object):
    def test_execute_value_savers(self):
        t = task.Task("Task X", ["taskcmd"])
        t.value_savers.append(lambda: {'v1':1})
        t.save_extra_values()
        assert 1 == t.values['v1']



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
            def check(self): return True
        base = Base()
        t = task.Task("Task X", ["taskcmd"], uptodate=[base.check])
        assert t.uptodate[0] == (base.check, [], {})

    def test_tuple(self):
        def custom_check(pos_arg, xxx=None): return True
        t = task.Task("Task X", ["taskcmd"],
                      uptodate=[(custom_check, [123], {'xxx':'yyy'})])
        assert t.uptodate[0] == (custom_check, [123], {'xxx':'yyy'})

    def test_str(self):
        t = task.Task("Task X", ["taskcmd"], uptodate=['my-cmd xxx'])
        assert t.uptodate[0] == ('my-cmd xxx', [], {})

    def test_object_with_configure(self):
        class Check(object):
            def __call__(self): return True
            def configure_task(self, task):
                task.task_dep.append('y1')
        check = Check()
        t = task.Task("Task X", ["taskcmd"], uptodate=[check])
        assert (check, [], {}) == t.uptodate[0]
        assert ['y1'] == t.task_dep

    def test_invalid(self):
        pytest.raises(task.InvalidTask,
                      task.Task, "Task X", ["taskcmd"], uptodate=[{'x':'y'}])


class TestTaskExpandFileDep(object):

    def test_dependencyStringIsFile(self):
        my_task = task.Task("Task X", ["taskcmd"], file_dep=["123","456"])
        assert set(["123","456"]) == my_task.file_dep

    def test_file_dep_path(self):
        my_task = task.Task("Task X", ["taskcmd"],
                            file_dep=["123", Path("456"), PurePath("789")])
        assert {"123", "456", "789"} == my_task.file_dep

    def test_file_dep_str(self):
        pytest.raises(task.InvalidTask, task.Task, "Task X", ["taskcmd"],
                      file_dep=[['aaaa']])

    def test_file_dep_unicode(self):
        unicode_name = "中文"
        my_task = task.Task("Task X", ["taskcmd"], file_dep=[unicode_name])
        assert unicode_name in my_task.file_dep


class TestTaskDeps(object):

    def test_task_dep(self):
        my_task = task.Task("Task X", ["taskcmd"], task_dep=["123","4*56"])
        assert ["123"] == my_task.task_dep
        assert ["4*56"] == my_task.wild_dep

    def test_calc_dep(self):
        my_task = task.Task("Task X", ["taskcmd"], calc_dep=["123"])
        assert set(["123"]) == my_task.calc_dep

    def test_update_deps(self):
        my_task = task.Task("Task X", ["taskcmd"], file_dep=["fileX"],
                            calc_dep=["calcX"], uptodate=[None])
        my_task.update_deps({'file_dep': ['fileY'],
                             'task_dep': ['taskY'],
                             'calc_dep': ['calcX', 'calcY'],
                             'uptodate': [True],
                             'to_be_ignored': 'asdf',
                             })
        assert set(['fileX', 'fileY']) == my_task.file_dep
        assert ['taskY'] == my_task.task_dep
        assert set(['calcX', 'calcY']) == my_task.calc_dep
        assert [(None, None, None), (True, None, None)] == my_task.uptodate


class TestTaskTargets(object):
    def test_targets_can_be_path(self):
        my_task = task.Task("Task X", ["taskcmd"],
                            targets=["123", Path("456"), PurePath("789")])
        assert ["123", "456", "789"] == my_task.targets

    def test_targets_should_be_string_or_path(self):
        assert pytest.raises(task.InvalidTask, task.Task, "Task X", ["taskcmd"],
                             targets=["123", Path("456"), 789])


class TestTask_Loader(object):
    def test_delayed_after_execution(self):
        # after `executed` creates an implicit task_dep
        delayed = task.DelayedLoader(lambda: None, executed='foo')
        t1 = task.Task('bar', None, loader=delayed)
        assert t1.task_dep == ['foo']


class TestTask_Getargs(object):
    def test_ok(self):
        getargs = {'x' : ('t1','x'), 'y': ('t2','z')}
        t = task.Task('t3', None, getargs=getargs)
        assert len(t.uptodate) == 2
        assert ['t1', 't2'] == sorted([t.uptodate[0][0].dep_name,
                                       t.uptodate[1][0].dep_name])

    def test_invalid_desc(self):
        getargs = {'x' : 't1'}
        assert pytest.raises(task.InvalidTask, task.Task,
                              't3', None, getargs=getargs)

    def test_invalid_desc_tuple(self):
        getargs = {'x' : ('t1',)}
        assert pytest.raises(task.InvalidTask, task.Task,
                              't3', None, getargs=getargs)


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
        t.execute(Stream(0))


    def test_result(self):
        # task.result is the value of last action
        t = task.Task('t1', ["%s hi_list hi1" % PROGRAM,
                             "%s hi_list hi2" % PROGRAM])
        t.dep_changed = []
        t.execute(Stream(0))
        assert "hi_listhi2" == t.result

    def test_values(self):
        def return_dict(d): return d
        # task.result is the value of last action
        t = task.Task('t1', [(return_dict, [{'x':5}]),
                             (return_dict, [{'y':10}]),])
        t.execute(Stream(0))
        assert {'x':5, 'y':10} == t.values

    def test_failure(self):
        t = task.Task("taskX", ["%s 1 2 3" % PROGRAM])
        got = t.execute(Stream(0))
        assert isinstance(got, TaskError)

    # make sure all cmds are being executed.
    def test_many(self):
        t = task.Task("taskX",["%s hi_stdout hi2" % PROGRAM,
                               "%s hi_list hi6" % PROGRAM])
        t.dep_changed = []
        t.execute(Stream(0))
        got = "".join([a.out for a in t.actions])
        assert "hi_stdouthi_list" == got, repr(got)


    def test_fail_first(self):
        t = task.Task("taskX", ["%s 1 2 3" % PROGRAM, PROGRAM])
        got = t.execute(Stream(0))
        assert isinstance(got, TaskError)

    def test_fail_second(self):
        t = task.Task("taskX", ["%s 1 2" % PROGRAM, "%s 1 2 3" % PROGRAM])
        got = t.execute(Stream(0))
        assert isinstance(got, TaskError)


    # python and commands mixed on same task
    def test_mixed(self):
        def my_print(msg):
            print(msg, end='')
        t = task.Task("taskX",["%s hi_stdout hi2" % PROGRAM,
                               (my_print,['_PY_']),
                               "%s hi_list hi6" % PROGRAM])
        t.dep_changed = []
        t.execute(Stream(0))
        got = "".join([a.out for a in t.actions])
        assert "hi_stdout_PY_hi_list" == got, repr(got)


class TestTaskTeardown(object):
    def test_ok(self):
        got = []
        def put(x):
            got.append(x)
        t = task.Task('t1', [], teardown=[(put, [1]), (put, [2])])
        t.execute(Stream(0))
        assert None == t.execute_teardown(Stream(0))
        assert [1,2] == got

    def test_fail(self):
        def my_raise():
            raise Exception('hoho')
        t = task.Task('t1', [], teardown=[(my_raise,)])
        t.execute(Stream(0))
        got = t.execute_teardown(Stream(0))
        assert isinstance(got, CatchedException)


class TestTaskClean(object):

    @pytest.fixture
    def tmpdir(self, request):
        tmpdir = {}
        tmpdir['dir'] = tempfile.mkdtemp(prefix='doit-')
        files = [os.path.join(tmpdir['dir'], fname)
                 for fname in ['a.txt', 'b.txt']]
        tmpdir['files'] = files
        # create empty files
        for filename in tmpdir['files']:
            open(filename, 'a').close()

        def remove_tmpdir():
            if os.path.exists(tmpdir['dir']):
                shutil.rmtree(tmpdir['dir'])
        request.addfinalizer(remove_tmpdir)

        return tmpdir


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

    def test_clean_action_error(self, capsys):
        def fail_clean():
            5/0
        t = task.Task("xxx", None, clean=[(fail_clean,)])
        assert 1 == len(t.clean_actions)
        t.clean(StringIO(), dryrun=False)
        err = capsys.readouterr()[1]
        assert "PythonAction Error" in err

    def test_clean_action_kwargs(self):
        def fail_clean(dryrun):
            print('hello %s' % dryrun)
        t = task.Task("xxx", None, clean=[(fail_clean,)])
        assert 1 == len(t.clean_actions)
        out = StringIO()
        t.clean(out, dryrun=False)
        assert "hello False" in out.getvalue()

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

    def test_dryrun_actions_not_executed(self, tmpdir):
        # clean action is not executed at all if it does not contain
        # a `dryrun` parameter
        self.executed = False
        def say_hello(): self.executed = True
        t = task.Task("xxx", None, targets=tmpdir['files'],
                      clean=[(say_hello,)])
        assert False == t._remove_targets
        assert 1 == len(t.clean_actions)
        t.clean(StringIO(), True)
        assert not self.executed

    def test_dryrun_actions_with_param_true(self, tmpdir):
        # clean action is not executed at all if it does not contain
        # a `dryrun` parameter
        self.executed = False
        self.dryrun_val = None
        def say_hello(dryrun):
            self.executed = True
            self.dryrun_val = dryrun
        t = task.Task("xxx", None, targets=tmpdir['files'],
                      clean=[(say_hello,)])
        assert False == t._remove_targets
        assert 1 == len(t.clean_actions)
        t.clean(StringIO(), dryrun=True)
        assert self.executed is True
        assert self.dryrun_val is True

    def test_dryrun_actions_with_param_false(self, tmpdir):
        # clean action is not executed at all if it does not contain
        # a `dryrun` parameter
        self.executed = False
        self.dryrun_val = None
        def say_hello(dryrun):
            self.executed = True
            self.dryrun_val = dryrun
        t = task.Task("xxx", None, targets=tmpdir['files'],
                      clean=[(say_hello,)])
        assert False == t._remove_targets
        assert 1 == len(t.clean_actions)
        t.clean(StringIO(), dryrun=False)
        assert self.executed is True
        assert self.dryrun_val is False


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

class TestTaskPickle(object):
    def test_geststate(self):
        t = task.Task("my_name", ["action"])
        pd = t.__getstate__()
        assert None == pd['uptodate']
        assert None == pd['_action_instances']

    def test_safedict(self):
        t = task.Task("my_name", ["action"])
        pd = t.pickle_safe_dict()
        assert 'uptodate' not in pd
        assert '_action_instances' not in pd
        assert 'value_savers' not in pd
        assert 'clean_actions' not in pd


class TestTaskUpdateFromPickle(object):
    def test_change_value(self):
        t = task.Task("my_name", ["action"])
        assert {} == t.values
        class FakePickle():
            def __init__(self):
                self.values = [1,2,3]
        t.update_from_pickle(FakePickle().__dict__)
        assert [1,2,3] == t.values
        assert 'my_name' == t.name

class TestDictToTask(object):
    def testDictOkMinimum(self):
        dict_ = {'name':'simple','actions':['xpto 14']}
        assert isinstance(task.dict_to_task(dict_), task.Task)

    def testDictFieldTypo(self):
        dict_ = {'name':'z','actions':['xpto 14'],'typo_here':['xxx']}
        pytest.raises(action.InvalidTask, task.dict_to_task, dict_)

    def testDictMissingFieldAction(self):
        pytest.raises(action.InvalidTask, task.dict_to_task, {'name':'xpto 14'})



class TestResultDep(object):
    def test_single(self, dep_manager):
        tasks = {'t1': task.Task("t1", None, uptodate=[task.result_dep('t2')]),
                 't2': task.Task("t2", None),
                 }
        # _config_task was executed and t2 added as task_dep
        assert ['t2'] == tasks['t1'].task_dep

        # first t2 result
        tasks['t2'].result = 'yes'
        dep_manager.save_success(tasks['t2'])
        assert 'run' == dep_manager.get_status(tasks['t1'], tasks).status  # first time

        tasks['t1'].save_extra_values()
        dep_manager.save_success(tasks['t1'])
        assert 'up-to-date' == dep_manager.get_status(tasks['t1'], tasks).status

        # t2 result changed
        tasks['t2'].result = '222'
        dep_manager.save_success(tasks['t2'])

        tasks['t1'].save_extra_values()
        dep_manager.save_success(tasks['t1'])
        assert 'run' == dep_manager.get_status(tasks['t1'], tasks).status

        tasks['t1'].save_extra_values()
        dep_manager.save_success(tasks['t1'])
        assert 'up-to-date' == dep_manager.get_status(tasks['t1'], tasks).status


    def test_group(self, dep_manager):
        tasks = {'t1': task.Task("t1", None, uptodate=[task.result_dep('t2')]),
                 't2': task.Task("t2", None, task_dep=['t2:a', 't2:b'],
                                 has_subtask=True),
                 't2:a': task.Task("t2:a", None),
                 't2:b': task.Task("t2:b", None),
                 }
        # _config_task was executed and t2 added as task_dep
        assert ['t2'] == tasks['t1'].task_dep

        # first t2 result
        tasks['t2:a'].result = 'yes1'
        dep_manager.save_success(tasks['t2:a'])
        tasks['t2:b'].result = 'yes2'
        dep_manager.save_success(tasks['t2:b'])
        assert 'run' == dep_manager.get_status(tasks['t1'], tasks).status  # first time

        tasks['t1'].save_extra_values()
        dep_manager.save_success(tasks['t1'])
        assert 'up-to-date' == dep_manager.get_status(tasks['t1'], tasks).status

        # t2 result changed
        tasks['t2:a'].result = '222'
        dep_manager.save_success(tasks['t2:a'])

        tasks['t1'].save_extra_values()
        dep_manager.save_success(tasks['t1'])
        assert 'run' == dep_manager.get_status(tasks['t1'], tasks).status

        tasks['t1'].save_extra_values()
        dep_manager.save_success(tasks['t1'])
        assert 'up-to-date' == dep_manager.get_status(tasks['t1'], tasks).status
