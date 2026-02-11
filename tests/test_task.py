import contextlib
import os
import shutil
import tempfile
import unittest
from io import StringIO
from pathlib import Path, PurePath
from sys import executable
from collections.abc import Iterable

from doit.exceptions import TaskError
from doit.exceptions import BaseFail
from doit import action
from doit import task
from doit.task import Stream

from tests.support import DepManagerMixin

# path to test folder (sample_process.py lives in tests/)
TEST_PATH = os.path.join(os.path.dirname(__file__), '..', 'tests')
PROGRAM = "%s %s/sample_process.py" % (executable, TEST_PATH)


class TestStream(unittest.TestCase):
    def test_from_task(self):
        # use value from task, not global from Stream
        v0 = Stream(0)
        self.assertEqual(v0.effective_verbosity(1), 1)
        self.assertEqual(v0.effective_verbosity(2), 2)
        v2 = Stream(2)
        self.assertEqual(v2.effective_verbosity(0), 0)
        self.assertEqual(v2.effective_verbosity(1), 1)

    def test_force_global(self):
        # use value from task, not global from Stream
        v0 = Stream(0, force_global=True)
        self.assertEqual(v0.effective_verbosity(2), 0)
        v2 = Stream(2, force_global=True)
        self.assertEqual(v2.effective_verbosity(0), 2)

    def test_task_verbosity_not_specified(self):
        # default
        v0 = Stream(None)
        self.assertEqual(v0.effective_verbosity(None), 1)

        v2 = Stream(2)
        self.assertEqual(v2.effective_verbosity(None), 2)


class TestTaskCheckInput(unittest.TestCase):
    def testOkType(self):
        task.Task.check_attr('xxx', 'attr', [], ((int, list), ()))

    def testOkTypeABC(self):
        task.Task.check_attr('xxx', 'attr', {}, ((Iterable,), ()))

    def testOkValue(self):
        task.Task.check_attr('xxx', 'attr', None, ((list,), (None,)))

    def testFailType(self):
        self.assertRaises(task.InvalidTask, task.Task.check_attr, 'xxx',
                          'attr', int, ((list,), (False,)))

    def testFailValue(self):
        self.assertRaises(task.InvalidTask, task.Task.check_attr, 'xxx',
                          'attr', True, ((list,), (False,)))


class TestTaskCompare(unittest.TestCase):
    def test_equal(self):
        # only task name is used to compare for equality
        t1 = task.Task("foo", None)
        t2 = task.Task("bar", None)
        t3 = task.Task("foo", None)
        self.assertNotEqual(t1, t2)
        self.assertEqual(t1, t3)

    def test_lt(self):
        # task name is used to compare/sort tasks
        t1 = task.Task("foo", None)
        t2 = task.Task("bar", None)
        t3 = task.Task("gee", None)
        self.assertGreater(t1, t2)
        sorted_names = sorted(t.name for t in (t1, t2, t3))
        self.assertEqual(sorted_names, ['bar', 'foo', 'gee'])


class TestTaskInit(unittest.TestCase):
    def test_groupTask(self):
        # group tasks have no action
        t = task.Task("taskX", None)
        self.assertEqual(t.actions, [])

    def test_dependencySequenceIsValid(self):
        task.Task("Task X", ["taskcmd"], file_dep=["123", "456"])

    # dependency must be a sequence or bool.
    # give proper error message when anything else is used.
    def test_dependencyNotSequence(self):
        filePath = "data/dependency1"
        self.assertRaises(task.InvalidTask, task.Task,
                          "Task X", ["taskcmd"], file_dep=filePath)

    def test_options(self):
        # when task is created, options contain the default values
        p1 = {'name': 'p1', 'default': 'p1-default'}
        p2 = {'name': 'p2', 'default': '', 'short': 'm'}
        t = task.Task("MyName", None, params=[p1, p2], pos_arg='pos')
        t.execute(Stream(0))
        self.assertEqual('p1-default', t.options['p1'])
        self.assertEqual('', t.options['p2'])
        self.assertEqual('pos', t.pos_arg)
        self.assertIsNone(t.pos_arg_val)  # always uninitialized

    def test_options_from_cfg(self):
        # Ensure that doit.cfg can specify task options.
        p1 = {'name': 'x', 'long': 'x', 'default': None}
        t = task.Task("MyName", None, params=[p1])
        t.cfg_values = {'x': 1}
        self.assertIsNone(t.options)
        t.init_options()
        self.assertIsNotNone(t.options)
        self.assertEqual(1, t.options['x'])

    def test_options_from_cfg_override(self):
        # Ensure that doit.cfg specified task options can be replaced by
        # command line specified options.

        p1 = {'name': 'x', 'long': 'x', 'default': None, 'type': int}
        p2 = {'name': 'y', 'long': 'y', 'default': 2, 'type': int}
        t = task.Task("MyName", None, params=[p1, p2])
        t.cfg_values = {'x': 1}
        self.assertIsNone(t.options)
        t.init_options(['--x=2'])
        self.assertIsNotNone(t.options)
        self.assertEqual(2, t.options['x'])
        self.assertEqual(2, t.options['y'])

    def test_setup(self):
        t = task.Task("task5", ['action'], setup=["task2"])
        self.assertEqual(["task2"], t.setup_tasks)

    def test_forbid_equal_sign_on_name(self):
        self.assertRaises(task.InvalidTask, task.Task, "a=1", ["taskcmd"])


class TestTaskValueSavers(unittest.TestCase):
    def test_execute_value_savers(self):
        t = task.Task("Task X", ["taskcmd"])
        t.value_savers.append(lambda: {'v1': 1})
        t.save_extra_values()
        self.assertEqual(1, t.values['v1'])


class TestTaskUpToDate(unittest.TestCase):
    def test_FalseRunalways(self):
        t = task.Task("Task X", ["taskcmd"], uptodate=[False])
        self.assertEqual(t.uptodate, [(False, None, None)])

    def test_NoneIgnored(self):
        t = task.Task("Task X", ["taskcmd"], uptodate=[None])
        self.assertEqual(t.uptodate, [(None, None, None)])

    def test_callable_function(self):
        def custom_check(): return True
        t = task.Task("Task X", ["taskcmd"], uptodate=[custom_check])
        self.assertEqual(t.uptodate[0], (custom_check, [], {}))

    def test_callable_instance_method(self):
        class Base(object):
            def check(self): return True
        base = Base()
        t = task.Task("Task X", ["taskcmd"], uptodate=[base.check])
        self.assertEqual(t.uptodate[0], (base.check, [], {}))

    def test_tuple(self):
        def custom_check(pos_arg, xxx=None): return True
        t = task.Task("Task X", ["taskcmd"],
                      uptodate=[(custom_check, [123], {'xxx': 'yyy'})])
        self.assertEqual(t.uptodate[0], (custom_check, [123], {'xxx': 'yyy'}))

    def test_str(self):
        t = task.Task("Task X", ["taskcmd"], uptodate=['my-cmd xxx'])
        self.assertEqual(t.uptodate[0], ('my-cmd xxx', [], {}))

    def test_object_with_configure(self):
        class Check(object):
            def __call__(self): return True
            def configure_task(self, task):
                task.task_dep.append('y1')
        check = Check()
        t = task.Task("Task X", ["taskcmd"], uptodate=[check])
        self.assertEqual((check, [], {}), t.uptodate[0])
        self.assertEqual(['y1'], t.task_dep)

    def test_invalid(self):
        self.assertRaises(task.InvalidTask,
                          task.Task, "Task X", ["taskcmd"],
                          uptodate=[{'x': 'y'}])


class TestTaskExpandFileDep(unittest.TestCase):
    def test_dependencyStringIsFile(self):
        my_task = task.Task("Task X", ["taskcmd"],
                            file_dep=["123", "456"])
        self.assertEqual(set(["123", "456"]), my_task.file_dep)

    def test_file_dep_path(self):
        my_task = task.Task("Task X", ["taskcmd"],
                            file_dep=["123", Path("456"), PurePath("789")])
        self.assertEqual({"123", "456", "789"}, my_task.file_dep)

    def test_file_dep_str(self):
        self.assertRaises(task.InvalidTask, task.Task, "Task X", ["taskcmd"],
                          file_dep=[['aaaa']])

    def test_file_dep_unicode(self):
        unicode_name = "\u4e2d\u6587"
        my_task = task.Task("Task X", ["taskcmd"], file_dep=[unicode_name])
        self.assertIn(unicode_name, my_task.file_dep)


class TestTaskDeps(unittest.TestCase):
    def test_task_dep(self):
        my_task = task.Task("Task X", ["taskcmd"],
                            task_dep=["123", "4*56"])
        self.assertEqual(["123"], my_task.task_dep)
        self.assertEqual(["4*56"], my_task.wild_dep)

    def test_calc_dep(self):
        my_task = task.Task("Task X", ["taskcmd"], calc_dep=["123"])
        self.assertEqual(set(["123"]), my_task.calc_dep)

    def test_update_deps(self):
        my_task = task.Task("Task X", ["taskcmd"], file_dep=["fileX"],
                            calc_dep=["calcX"], uptodate=[None])
        my_task.update_deps({'file_dep': ['fileY'],
                             'task_dep': ['taskY'],
                             'calc_dep': ['calcX', 'calcY'],
                             'uptodate': [True],
                             'to_be_ignored': 'asdf',
                             })
        self.assertEqual(set(['fileX', 'fileY']), my_task.file_dep)
        self.assertEqual(['taskY'], my_task.task_dep)
        self.assertEqual(set(['calcX', 'calcY']), my_task.calc_dep)
        self.assertEqual([(None, None, None), (True, None, None)],
                         my_task.uptodate)


class TestTaskTargets(unittest.TestCase):
    def test_targets_can_be_path(self):
        my_task = task.Task("Task X", ["taskcmd"],
                            targets=["123", Path("456"), PurePath("789")])
        self.assertEqual(["123", "456", "789"], my_task.targets)

    def test_targets_should_be_string_or_path(self):
        self.assertRaises(task.InvalidTask, task.Task, "Task X", ["taskcmd"],
                          targets=["123", Path("456"), 789])


class TestTask_Loader(unittest.TestCase):
    def test_delayed_after_execution(self):
        # after `executed` creates an implicit task_dep
        delayed = task.DelayedLoader(lambda: None, executed='foo')
        t1 = task.Task('bar', None, loader=delayed)
        self.assertEqual(t1.task_dep, ['foo'])


class TestTask_Getargs(unittest.TestCase):
    def test_ok(self):
        getargs = {'x': ('t1', 'x'), 'y': ('t2', 'z')}
        t = task.Task('t3', None, getargs=getargs)
        self.assertEqual(len(t.uptodate), 2)
        self.assertEqual(['t1', 't2'],
                         sorted([t.uptodate[0][0].dep_name,
                                 t.uptodate[1][0].dep_name]))

    def test_invalid_desc(self):
        getargs = {'x': 't1'}
        self.assertRaises(task.InvalidTask, task.Task,
                          't3', None, getargs=getargs)

    def test_invalid_desc_tuple(self):
        getargs = {'x': ('t1',)}
        self.assertRaises(task.InvalidTask, task.Task,
                          't3', None, getargs=getargs)


class TestTaskTitle(unittest.TestCase):
    def test_title(self):
        t = task.Task("MyName", ["MyAction"])
        self.assertEqual("MyName", t.title())

    def test_custom_title(self):
        t = task.Task("MyName", ["MyAction"],
                      title=(lambda x: "X%sX" % x.name))
        self.assertEqual("X%sX" % str(t.name), t.title())


class TestTaskRepr(unittest.TestCase):
    def test_repr(self):
        t = task.Task("taskX", None, ('t1', 't2'))
        self.assertEqual("<Task: taskX>", repr(t))


class TestTaskActions(unittest.TestCase):
    def test_success(self):
        t = task.Task("taskX", [PROGRAM])
        t.execute(Stream(0))

    def test_result(self):
        # task.result is the value of last action
        t = task.Task('t1', ["%s hi_list hi1" % PROGRAM,
                             "%s hi_list hi2" % PROGRAM])
        t.dep_changed = []
        t.execute(Stream(0))
        self.assertEqual("hi_listhi2", t.result)

    def test_values(self):
        def return_dict(d): return d
        # task.result is the value of last action
        t = task.Task('t1', [(return_dict, [{'x': 5}]),
                             (return_dict, [{'y': 10}])])
        t.execute(Stream(0))
        self.assertEqual({'x': 5, 'y': 10}, t.values)

    def test_failure(self):
        t = task.Task("taskX", ["%s 1 2 3" % PROGRAM])
        got = t.execute(Stream(0))
        self.assertIsInstance(got, TaskError)

    # make sure all cmds are being executed.
    def test_many(self):
        t = task.Task("taskX", ["%s hi_stdout hi2" % PROGRAM,
                                "%s hi_list hi6" % PROGRAM])
        t.dep_changed = []
        t.execute(Stream(0))
        got = "".join([a.out for a in t.actions])
        self.assertEqual("hi_stdouthi_list", got)

    def test_fail_first(self):
        t = task.Task("taskX", ["%s 1 2 3" % PROGRAM, PROGRAM])
        got = t.execute(Stream(0))
        self.assertIsInstance(got, TaskError)

    def test_fail_second(self):
        t = task.Task("taskX", ["%s 1 2" % PROGRAM,
                                "%s 1 2 3" % PROGRAM])
        got = t.execute(Stream(0))
        self.assertIsInstance(got, TaskError)

    # python and commands mixed on same task
    def test_mixed(self):
        def my_print(msg):
            print(msg, end='')
        t = task.Task("taskX", ["%s hi_stdout hi2" % PROGRAM,
                                (my_print, ['_PY_']),
                                "%s hi_list hi6" % PROGRAM])
        t.dep_changed = []
        t.execute(Stream(0))
        got = "".join([a.out for a in t.actions])
        self.assertEqual("hi_stdout_PY_hi_list", got)


class TestTaskTeardown(unittest.TestCase):
    def test_ok(self):
        got = []
        def put(x):
            got.append(x)
        t = task.Task('t1', [], teardown=[(put, [1]), (put, [2])])
        t.execute(Stream(0))
        self.assertIsNone(t.execute_teardown(Stream(0)))
        self.assertEqual([1, 2], got)

    def test_fail(self):
        def my_raise():
            raise Exception('hoho')
        t = task.Task('t1', [], teardown=[(my_raise,)])
        t.execute(Stream(0))
        got = t.execute_teardown(Stream(0))
        self.assertIsInstance(got, BaseFail)


class TestTaskClean(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.tmpdir = {}
        self.tmpdir['dir'] = tempfile.mkdtemp(prefix='doit-')
        self.tmpdir['subdir'] = tempfile.mkdtemp(dir=self.tmpdir['dir'])
        files = [os.path.join(self.tmpdir['dir'], fname)
                 for fname in ['a.txt',
                               'b.txt',
                               os.path.join(self.tmpdir['subdir'], 'c.txt')]]
        self.tmpdir['files'] = files
        # create empty files
        for filename in self.tmpdir['files']:
            open(filename, 'a').close()
        self.addCleanup(self._remove_tmpdir)

    def _remove_tmpdir(self):
        if os.path.exists(self.tmpdir['dir']):
            shutil.rmtree(self.tmpdir['dir'])

    def test_clean_nothing(self):
        t = task.Task("xxx", None)
        self.assertFalse(t._remove_targets)
        self.assertEqual(0, len(t.clean_actions))
        t.clean(StringIO(), False)
        for filename in self.tmpdir['files']:
            self.assertTrue(os.path.exists(filename))

    def test_clean_targets(self):
        t = task.Task("xxx", None, targets=self.tmpdir['files'], clean=True)
        self.assertTrue(t._remove_targets)
        self.assertEqual(0, len(t.clean_actions))
        t.clean(StringIO(), False)
        for filename in self.tmpdir['files']:
            self.assertFalse(os.path.exists(filename), filename)

    def test_clean_non_existent_targets(self):
        t = task.Task('xxx', None, targets=["i_dont_exist"], clean=True)
        t.clean(StringIO(), False)
        # nothing is raised

    def test_clean_empty_dirs(self):
        # Remove empty directories listed in targets
        targets = self.tmpdir['files'] + [self.tmpdir['subdir']]
        t = task.Task("xxx", None, targets=targets, clean=True)
        self.assertTrue(t._remove_targets)
        self.assertEqual(0, len(t.clean_actions))
        t.clean(StringIO(), False)
        for filename in self.tmpdir['files']:
            self.assertFalse(os.path.exists(filename))
        self.assertFalse(os.path.exists(self.tmpdir['subdir']))
        self.assertTrue(os.path.exists(self.tmpdir['dir']))

    def test_keep_non_empty_dirs(self):
        # Keep non empty directories listed in targets
        targets = [self.tmpdir['files'][0], self.tmpdir['dir']]
        t = task.Task("xxx", None, targets=targets, clean=True)
        self.assertTrue(t._remove_targets)
        self.assertEqual(0, len(t.clean_actions))
        t.clean(StringIO(), False)
        for filename in self.tmpdir['files']:
            expected = filename not in targets
            self.assertEqual(expected, os.path.exists(filename))
        self.assertTrue(os.path.exists(self.tmpdir['dir']))

    def test_clean_any_order(self):
        # Remove targets in reverse lexical order so that subdirectories' order
        # in the targets array is irrelevant
        targets = (self.tmpdir['files']
                   + [self.tmpdir['dir'], self.tmpdir['subdir']])
        t = task.Task("xxx", None, targets=targets, clean=True)
        self.assertTrue(t._remove_targets)
        self.assertEqual(0, len(t.clean_actions))
        t.clean(StringIO(), False)
        for filename in self.tmpdir['files']:
            self.assertFalse(os.path.exists(filename))
        self.assertFalse(os.path.exists(self.tmpdir['dir']))
        self.assertFalse(os.path.exists(self.tmpdir['subdir']))

    def test_clean_actions(self):
        # a clean action can be anything, it can even not clean anything!
        c_path = self.tmpdir['files'][0]
        def say_hello():
            fh = open(c_path, 'a')
            fh.write("hello!!!")
            fh.close()
        t = task.Task("xxx", None, targets=self.tmpdir['files'],
                      clean=[(say_hello,)])
        self.assertFalse(t._remove_targets)
        self.assertEqual(1, len(t.clean_actions))
        t.clean(StringIO(), False)
        for filename in self.tmpdir['files']:
            self.assertTrue(os.path.exists(filename))
        fh = open(c_path, 'r')
        got = fh.read()
        fh.close()
        self.assertEqual("hello!!!", got)

    def test_clean_action_error(self):
        def fail_clean():
            5 / 0
        t = task.Task("xxx", None, clean=[(fail_clean,)])
        self.assertEqual(1, len(t.clean_actions))
        err = StringIO()
        with contextlib.redirect_stderr(err):
            t.clean(StringIO(), dryrun=False)
        self.assertIn("PythonAction Error", err.getvalue())

    def test_clean_action_kwargs(self):
        def fail_clean(dryrun):
            print('hello %s' % dryrun)
        t = task.Task("xxx", None, clean=[(fail_clean,)])
        self.assertEqual(1, len(t.clean_actions))
        out = StringIO()
        t.clean(out, dryrun=False)
        self.assertIn("hello False", out.getvalue())

    def test_dryrun_file(self):
        t = task.Task("xxx", None, targets=self.tmpdir['files'], clean=True)
        self.assertTrue(t._remove_targets)
        self.assertEqual(0, len(t.clean_actions))
        t.clean(StringIO(), True)
        # files are NOT removed
        for filename in self.tmpdir['files']:
            self.assertTrue(os.path.exists(filename), filename)

    def test_dryrun_dir(self):
        targets = self.tmpdir['files'] + [self.tmpdir['dir']]
        for filename in self.tmpdir['files']:
            os.remove(filename)
        t = task.Task("xxx", None, targets=targets, clean=True)
        self.assertTrue(t._remove_targets)
        self.assertEqual(0, len(t.clean_actions))
        t.clean(StringIO(), True)
        self.assertTrue(os.path.exists(self.tmpdir['dir']))

    def test_dryrun_actions_not_executed(self):
        # clean action is not executed at all if it does not contain
        # a `dryrun` parameter
        self.executed = False
        def say_hello(): self.executed = True
        t = task.Task("xxx", None, targets=self.tmpdir['files'],
                      clean=[(say_hello,)])
        self.assertFalse(t._remove_targets)
        self.assertEqual(1, len(t.clean_actions))
        t.clean(StringIO(), True)
        self.assertFalse(self.executed)

    def test_dryrun_actions_with_param_true(self):
        # clean action is not executed at all if it does not contain
        # a `dryrun` parameter
        self.executed = False
        self.dryrun_val = None
        def say_hello(dryrun):
            self.executed = True
            self.dryrun_val = dryrun
        t = task.Task("xxx", None, targets=self.tmpdir['files'],
                      clean=[(say_hello,)])
        self.assertFalse(t._remove_targets)
        self.assertEqual(1, len(t.clean_actions))
        t.clean(StringIO(), dryrun=True)
        self.assertTrue(self.executed)
        self.assertTrue(self.dryrun_val)

    def test_dryrun_actions_with_param_false(self):
        # clean action is not executed at all if it does not contain
        # a `dryrun` parameter
        self.executed = False
        self.dryrun_val = None
        def say_hello(dryrun):
            self.executed = True
            self.dryrun_val = dryrun
        t = task.Task("xxx", None, targets=self.tmpdir['files'],
                      clean=[(say_hello,)])
        self.assertFalse(t._remove_targets)
        self.assertEqual(1, len(t.clean_actions))
        t.clean(StringIO(), dryrun=False)
        self.assertTrue(self.executed)
        self.assertFalse(self.dryrun_val)


class TestTaskDoc(unittest.TestCase):
    def test_no_doc(self):
        t = task.Task("name", ["action"])
        self.assertEqual('', t.doc)

    def test_single_line(self):
        t = task.Task("name", ["action"], doc="  i am doc")
        self.assertEqual("i am doc", t.doc)

    def test_multiple_lines(self):
        t = task.Task("name", ["action"],
                      doc="i am doc  \n with many lines\n")
        self.assertEqual("i am doc", t.doc)

    def test_start_with_empty_lines(self):
        t = task.Task("name", ["action"], doc="\n\n i am doc \n")
        self.assertEqual("i am doc", t.doc)

    def test_just_new_line(self):
        t = task.Task("name", ["action"], doc="  \n  \n\n")
        self.assertEqual("", t.doc)


class TestTaskPickle(unittest.TestCase):
    def test_geststate(self):
        t = task.Task("my_name", ["action"])
        pd = t.__getstate__()
        self.assertIsNone(pd['uptodate'])
        self.assertIsNone(pd['_action_instances'])

    def test_safedict(self):
        t = task.Task("my_name", ["action"])
        pd = t.pickle_safe_dict()
        self.assertNotIn('uptodate', pd)
        self.assertNotIn('_action_instances', pd)
        self.assertNotIn('value_savers', pd)
        self.assertNotIn('clean_actions', pd)


class TestTaskUpdateFromPickle(unittest.TestCase):
    def test_change_value(self):
        t = task.Task("my_name", ["action"])
        self.assertEqual({}, t.values)
        class FakePickle():
            def __init__(self):
                self.values = [1, 2, 3]
        t.update_from_pickle(FakePickle().__dict__)
        self.assertEqual([1, 2, 3], t.values)
        self.assertEqual('my_name', t.name)


class TestDictToTask(unittest.TestCase):
    def testDictOkMinimum(self):
        dict_ = {'name': 'simple', 'actions': ['xpto 14']}
        self.assertIsInstance(task.dict_to_task(dict_), task.Task)

    def testDictFieldTypo(self):
        dict_ = {'name': 'z', 'actions': ['xpto 14'],
                 'typo_here': ['xxx']}
        self.assertRaises(action.InvalidTask, task.dict_to_task, dict_)

    def testDictMissingFieldAction(self):
        self.assertRaises(action.InvalidTask, task.dict_to_task,
                          {'name': 'xpto 14'})


class TestResultDep(DepManagerMixin, unittest.TestCase):
    def test_single(self):
        tasks = {
            't1': task.Task("t1", None,
                            uptodate=[task.result_dep('t2')]),
            't2': task.Task("t2", None),
        }
        # _config_task was executed and t2 added as task_dep
        self.assertEqual(['t2'], tasks['t1'].task_dep)

        # first t2 result
        tasks['t2'].result = 'yes'
        self.dep_manager.save_success(tasks['t2'])
        self.assertEqual('run',
                         self.dep_manager.get_status(
                             tasks['t1'], tasks).status)  # first time

        tasks['t1'].save_extra_values()
        self.dep_manager.save_success(tasks['t1'])
        self.assertEqual('up-to-date',
                         self.dep_manager.get_status(
                             tasks['t1'], tasks).status)

        # t2 result changed
        tasks['t2'].result = '222'
        self.dep_manager.save_success(tasks['t2'])
        self.assertEqual('run',
                         self.dep_manager.get_status(
                             tasks['t1'], tasks).status)

        tasks['t1'].save_extra_values()
        self.dep_manager.save_success(tasks['t1'])
        self.assertEqual('up-to-date',
                         self.dep_manager.get_status(
                             tasks['t1'], tasks).status)

    def test_group(self):
        tasks = {
            't1': task.Task("t1", None,
                            uptodate=[task.result_dep('t2')]),
            't2': task.Task("t2", None, task_dep=['t2:a', 't2:b'],
                            has_subtask=True),
            't2:a': task.Task("t2:a", None),
            't2:b': task.Task("t2:b", None),
        }
        # _config_task was executed and t2 added as task_dep
        self.assertEqual(['t2'], tasks['t1'].task_dep)

        # first t2 result
        tasks['t2:a'].result = 'yes1'
        self.dep_manager.save_success(tasks['t2:a'])
        tasks['t2:b'].result = 'yes2'
        self.dep_manager.save_success(tasks['t2:b'])
        self.assertEqual('run',
                         self.dep_manager.get_status(
                             tasks['t1'], tasks).status)  # first time

        tasks['t1'].save_extra_values()
        self.dep_manager.save_success(tasks['t1'])
        self.assertEqual('up-to-date',
                         self.dep_manager.get_status(
                             tasks['t1'], tasks).status)

        # t2 result changed
        tasks['t2:a'].result = '222'
        self.dep_manager.save_success(tasks['t2:a'])
        self.assertEqual('run',
                         self.dep_manager.get_status(
                             tasks['t1'], tasks).status)

        tasks['t1'].save_extra_values()
        self.dep_manager.save_success(tasks['t1'])
        self.assertEqual('up-to-date',
                         self.dep_manager.get_status(
                             tasks['t1'], tasks).status)

