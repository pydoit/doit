import os
import sys, StringIO

from nose.tools import assert_raises

from doit import TaskError, TaskFailed
from doit import task

#path to test folder
TEST_PATH = os.path.dirname(__file__)

class BaseTempFile(object):
    def setUp(self):
        self.tmp = os.tmpfile()

    def tearDown(self):
        self.tmp.close()

    def tmp_read(self):
        self.tmp.seek(0)
        return self.tmp.read()




############# CmdAction
class TestCmdAction(object):
    # if nothing is raised it is successful
    def test_success(self):
        action = task.CmdAction("python %s/sample_process.py"%TEST_PATH)
        action.execute()

    def test_error(self):
        action = task.CmdAction("python %s/sample_process.py 1 2 3" %TEST_PATH)
        assert_raises(TaskError, action.execute)

    def test_failure(self):
        cmd = "python %s/sample_process.py please fail" % TEST_PATH
        action = task.CmdAction(cmd)
        assert_raises(TaskFailed, action.execute)

    def test_str(self):
        action = task.CmdAction("python %s/sample_process.py"%TEST_PATH)
        assert "Cmd: python %s/sample_process.py"%TEST_PATH == str(action)

    def test_repr(self):
        action = task.CmdAction("python %s/sample_process.py"%TEST_PATH)
        expected = "<CmdAction: 'python %s/sample_process.py'>"%TEST_PATH
        assert  expected == repr(action), repr(action)


class TestCmdVerbosityStderr(BaseTempFile):
    # Capture stderr
    def test_capture(self):
        cmd = "python %s/sample_process.py please fail" % TEST_PATH
        action = task.CmdAction(cmd)
        assert_raises(TaskFailed, action.execute)
        assert "err output on failure" == action.err, repr(action.err)


    # Do not capture stderr
    def test_noCapture(self):
        cmd = "python %s/sample_process.py please fail"
        action = task.CmdAction(cmd % TEST_PATH)
        assert_raises(TaskFailed, action.execute, stderr=self.tmp.fileno())
        got = self.tmp_read()
        assert "err output on failure" == got, repr(got)
        assert None == action.err, repr(action.err)



class TestCmdVerbosityStdout(BaseTempFile):
    # Capture stdout
    def test_capture(self):
        cmd = "python %s/sample_process.py hi_stdout hi2" % TEST_PATH
        action = task.CmdAction(cmd)
        action.execute()
        assert "hi_stdout" == action.out, repr(action.out)


    # Do not capture stdout
    def test_noCapture(self):
        cmd = "python %s/sample_process.py hi_stdout hi2" % TEST_PATH
        action = task.CmdAction(cmd)
        action.execute(stdout=self.tmp.fileno())
        got = self.tmp_read()
        assert "hi_stdout" == got, repr(got)
        assert None == action.out, repr(action.out)



############# PythonAction

class TestPythonAction(object):

    def test_success_bool(self):
        def success_sample():return True
        action = task.PythonAction(success_sample)
        # nothing raised it was successful
        action.execute()

    def test_success_None(self):
        def success_sample():return
        action = task.PythonAction(success_sample)
        # nothing raised it was successful
        action.execute()

    def test_success_str(self):
        def success_sample():return ""
        action = task.PythonAction(success_sample)
        # nothing raised it was successful
        action.execute()

    def test_error_object(self):
        # anthing but None, bool, or string
        def error_sample(): return {}
        action = task.PythonAction(error_sample)
        assert_raises(TaskError, action.execute)

    def test_error_exception(self):
        def error_sample(): raise Exception("asdf")
        action = task.PythonAction(error_sample)
        assert_raises(TaskError, action.execute)

    def test_fail_bool(self):
        def fail_sample():return False
        action = task.PythonAction(fail_sample)
        assert_raises(TaskFailed, action.execute)

    # any callable should work, not only functions
    def test_nonFunction(self):
        class CallMe:
            def __call__(self):
                return False

        action= task.PythonAction(CallMe())
        assert_raises(TaskFailed, action.execute)

    # helper to test callable with parameters
    def _func_par(self,par1,par2,par3=5):
        if par1 == par2 and par3 > 10:
            return True
        else:
            return False


    def test_init(self):
        # default values
        action1 = task.PythonAction(self._func_par)
        assert action1.args == []
        assert action1.kwargs == {}

        # not a callable
        assert_raises(task.InvalidTask, task.PythonAction, "abc")
        # args not a list
        assert_raises(task.InvalidTask, task.PythonAction, self._func_par, "c")
        # kwargs not a list
        assert_raises(task.InvalidTask, task.PythonAction,
                      self._func_par, None, "a")


    def test_functionParametersArgs(self):
        action = task.PythonAction(self._func_par,args=(2,2,25))
        action.execute()

    def test_functionParametersKwargs(self):
        action = task.PythonAction(self._func_par,
                              kwargs={'par1':2,'par2':2,'par3':25})
        action.execute()

    def test_functionParameters(self):
        action = task.PythonAction(self._func_par,args=(2,2),
                                   kwargs={'par3':25})
        action.execute()

    def test_functionParametersFail(self):
        action = task.PythonAction(self._func_par, args=(2,3),
                                   kwargs={'par3':25})
        assert_raises(TaskFailed, action.execute)

    def test_str(self):
        def str_sample(): return True
        action = task.PythonAction(str_sample)
        assert "Python: function str_sample" == str(action), "'%s'"%str(action)

    def test_repr(self):
        def repr_sample(): return True
        action = task.PythonAction(repr_sample)
        assert  "<PythonAction: '%s'>" % repr(repr_sample) == repr(action)



class TestPythonVerbosityStderr(object):
    def setUp(self):
        # capture stderr
        self.oldErr = sys.stderr
        sys.stderr = StringIO.StringIO()

    def tearDown(self):
        sys.stderr.close()
        sys.stderr = self.oldErr

    def write_and_error(self):
        sys.stderr.write("this is stderr E\n")
        raise Exception("Hi i am an exception")

    def write_and_success(self):
        sys.stderr.write("this is stderr S\n")
        return True

    def write_and_fail(self):
        sys.stderr.write("this is stderr F\n")
        return False

    ##### Capture stderr
    #
    # success
    def test_captureSuccess(self):
        action = task.PythonAction(self.write_and_success)
        action.execute()
        assert "" == sys.stderr.getvalue()
        assert "this is stderr S\n" == action.err, repr(action.err)

    # failure
    def test_captureFail(self):
        action = task.PythonAction(self.write_and_fail)
        assert_raises(TaskFailed, action.execute)
        assert "" == sys.stderr.getvalue()
        assert "this is stderr F\n" == action.err, repr(action.err)

    # error
    def test_captureError(self):
        action = task.PythonAction(self.write_and_error)
        assert_raises(TaskError, action.execute)
        assert "" == sys.stderr.getvalue()
        assert "this is stderr E\n" == action.err, repr(action.err)

    ##### Do not capture stderr
    #
    # success
    def test_noCaptureSuccess(self):
        t = task.PythonAction(self.write_and_success)
        t.execute(stderr=None)
        got = sys.stderr.getvalue()
        assert "this is stderr S\n" == got, repr(got)

    # failure
    def test_noCaptureFail(self):
        t = task.PythonAction(self.write_and_fail)
        assert_raises(TaskFailed, t.execute, stderr=None)
        got = sys.stderr.getvalue()
        assert "this is stderr F\n" == got, repr(got)

    # error
    def test_noCaptureError(self):
        t = task.PythonAction(self.write_and_error)
        assert_raises(TaskError, t.execute, stderr=None)
        got = sys.stderr.getvalue()
        assert "this is stderr E\n" == got, repr(got)


class TestPythonVerbosityStdout(object):
    def setUp(self):
        # capture stdout
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()

    def tearDown(self):
        sys.stdout.close()
        sys.stdout = self.oldOut

    def write_and_error(self):
        sys.stdout.write("this is stdout E\n")
        raise Exception("Hi i am an exception")

    def write_and_success(self):
        sys.stdout.write("this is stdout S\n")
        return True

    def write_and_fail(self):
        sys.stdout.write("this is stdout F\n")
        return False

    ##### Capture stdout
    #
    # success
    def test_captureSuccess(self):
        action = task.PythonAction(self.write_and_success)
        action.execute()
        assert "" == sys.stdout.getvalue()
        assert "this is stdout S\n" == action.out, repr(action.out)

    # failure
    def test_captureFail(self):
        action = task.PythonAction(self.write_and_fail)
        assert_raises(TaskFailed, action.execute)
        assert "" == sys.stdout.getvalue()
        assert "this is stdout F\n" == action.out, repr(action.out)

    # error
    def test_captureError(self):
        action = task.PythonAction(self.write_and_error)
        assert_raises(TaskError, action.execute)
        assert "" == sys.stdout.getvalue()
        assert "this is stdout E\n" == action.out, repr(action.out)


    ##### Do not capture stdout
    #
    # success
    def test_noCaptureSuccess(self):
        action = task.PythonAction(self.write_and_success)
        action.execute(stdout=None)
        got = sys.stdout.getvalue()
        assert "this is stdout S\n" == got, repr(got)

    # failure
    def test_noCaptureFail(self):
        action = task.PythonAction(self.write_and_fail)
        assert_raises(TaskFailed, action.execute, stdout=None)
        got = sys.stdout.getvalue()
        assert "this is stdout F\n" == got, repr(got)

    # error
    def test_noCaptureError(self):
        action = task.PythonAction(self.write_and_error)
        assert_raises(TaskError, action.execute, stdout=None)
        got = sys.stdout.getvalue()
        assert "this is stdout E\n" == got, repr(got)



##############


class TestCreateAction(object):
    def testBaseAction(self):
        class Sample(task.BaseAction): pass
        action = task.create_action(Sample())
        assert isinstance(action, Sample)

    def testStringAction(self):
        action = task.create_action("xpto 14 7")
        assert isinstance(action, task.CmdAction)

    def testMethodAction(self):
        def dumb(): return
        action = task.create_action(dumb)
        assert isinstance(action, task.PythonAction)

    def testTupleAction(self):
        def dumb(): return
        action = task.create_action((dumb,[1,2],{'a':5}))
        assert isinstance(action, task.PythonAction)

    def testInvalidActionNone(self):
        assert_raises(task.InvalidTask, task.create_action, None)

    def testInvalidActionObject(self):
        assert_raises(task.InvalidTask, task.create_action, self)



class TestTaskCheckInput(object):

    def testOkType(self):
        task.Task.check_attr_input('xxx', 'attr', [], [int, list])

    def testOkValue(self):
        task.Task.check_attr_input('xxx', 'attr', None, [list, None])

    def testFailType(self):
        assert_raises(task.InvalidTask, task.Task.check_attr_input, 'xxx',
                      'attr', int, [list, False])

    def testFailValue(self):
        assert_raises(task.InvalidTask, task.Task.check_attr_input, 'xxx',
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

    def test_dependencyTrueIsValid(self):
        t = task.Task("Task X",["taskcmd"], dependencies=[True])
        assert t.run_once

    def test_dependencyFalseIsNotValid(self):
        assert_raises(task.InvalidTask, task.Task,
                      "Task X",["taskcmd"], dependencies=[False])

    def test_ruOnce_or_fileDependency(self):
        assert_raises(task.InvalidTask, task.Task,
                      "Task X",["taskcmd"], dependencies=[True,"whatever"])

    # dependency must be a sequence or bool.
    # give proper error message when anything else is used.
    def test_dependencyNotSequence(self):
        filePath = "data/dependency1"
        assert_raises(task.InvalidTask, task.Task,
                      "Task X",["taskcmd"], dependencies=filePath)


    def test_title(self):
        t = task.Task("MyName",["MyAction"])
        assert "MyName => %s"%str(t) == t.title(), t.title()


    def test_strGroup(self):
        t = task.Task("taskX",None,('file_foo', ':t1',':t2'))
        assert "Group: t1, t2" == str(t), "'%s'"%str(t)


    # dependency types going to the write place
    def test_dependencyTypes(self):
        dep = ["file1.txt",":taskX","file2"]
        t = task.Task("MyName", ["MyAction"], dep)
        assert t.task_dep == [dep[1][1:]]
        assert t.file_dep == [dep[0],dep[2]]



class TestTaskActions(object):
    def setUp(self):
        # capture stdout
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()

    def tearDown(self):
        sys.stdout.close()
        sys.stdout = self.oldOut

    def test_success(self):
        t = task.Task("taskX", ["python %s/sample_process.py" % TEST_PATH])
        t.execute()

    def test_failure(self):
        t = task.Task("taskX", ["python %s/sample_process.py 1 2 3" % TEST_PATH])
        assert_raises(TaskError, t.execute)

    # make sure all cmds are being executed.
    def test_many(self):
        t = task.Task("taskX",[
                "python %s/sample_process.py hi_stdout hi2" % TEST_PATH,
                "python %s/sample_process.py hi_list hi6" % TEST_PATH])
        t.execute(capture_stdout=True, capture_stderr=True)
        assert "" == sys.stdout.getvalue()
        got = "".join([a.out for a in t.actions])
        assert "hi_stdouthi_list" == got, repr(got)


    def test_fail_first(self):
        t = task.Task("taskX", ["python %s/sample_process.py 1 2 3" % TEST_PATH,
                                "python %s/sample_process.py " % TEST_PATH])
        assert_raises(TaskError, t.execute)

    def test_fail_second(self):
        t = task.Task("taskX", ["python %s/sample_process.py 1 2" % TEST_PATH,
                                "python %s/sample_process.py 1 2 3" % TEST_PATH])
        assert_raises(TaskError, t.execute,
                      capture_stdout=True, capture_stderr=True)


    # python and commands mixed on same task
    def test_mixed(self):
        def my_print(msg):
            print msg,
            return True
        t = task.Task("taskX",[
                "python %s/sample_process.py hi_stdout hi2"%TEST_PATH,
                (my_print,['_PY_']),
                "python %s/sample_process.py hi_list hi6"%TEST_PATH])
        t.execute(capture_stdout=True, capture_stderr=True)
        assert "" == sys.stdout.getvalue()
        got = "".join([a.out for a in t.actions])
        assert "hi_stdout_PY_hi_list" == got, repr(got)




class TestTaskClean(object):
    C_PATH = 'tclean.txt'

    def setUp(self):
        fh = file(self.C_PATH, 'a')
        fh.close()

    def tearDown(self):
        if os.path.exists(self.C_PATH):
            os.remove(self.C_PATH)

    def test_clean_nothing(self):
        t = task.Task("xxx", None)
        assert False == t._remove_targets
        assert 0 == len(t.clean_actions)
        t.clean()
        assert os.path.exists(self.C_PATH)

    def test_clean_targets(self):
        t = task.Task("xxx", None, targets=[self.C_PATH], clean=True)
        assert True == t._remove_targets
        assert 0 == len(t.clean_actions)
        t.clean()
        assert not os.path.exists(self.C_PATH)

    def test_clean_actions(self):
        # a clean action can be anything, it can even not clean anything!
        def say_hello():
            fh = file(self.C_PATH, 'a')
            fh.write("hello!!!")
            fh.close()
            return True
        t = task.Task("xxx", None, targets=[self.C_PATH], clean=[(say_hello,)])
        assert False == t._remove_targets
        assert 1 == len(t.clean_actions)
        t.clean()
        assert os.path.exists(self.C_PATH)
        fh = file(self.C_PATH, 'r')
        got = fh.read()
        fh.close()
        assert "hello!!!" == got



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
        assert_raises(task.InvalidTask, task.dict_to_task, dict_)

    def testDictMissingFieldAction(self):
        assert_raises(task.InvalidTask, task.dict_to_task, {'name':'xpto 14'})


class TestCmdFormatting(object):

    def test_task_meta_reference(self):
        cmd = "python %s/myecho.py" % TEST_PATH
        cmd += " %(dependencies)s - %(changed)s - %(targets)s"
        dependencies = ["data/dependency1", "data/dependency2", ":dep_on_task"]
        targets = ["data/target", "data/targetXXX"]
        t = task.Task('formating', [cmd], dependencies, targets)
        t.dep_changed = ["data/dependency1"]
        t.execute(capture_stdout=True)

        got = t.actions[0].out.split('-')
        assert t.file_dep == got[0].split(), got[0]
        assert t.dep_changed == got[1].split(), got[1]
        assert targets == got[2].split(), got[2]


class TestPythonActionExtraArgs(object):
    class FakeTask(object):
        def __init__(self):
            self.name = 'name'
            self.targets = 'targets'
            self.file_dep = 'dependencies'
            self.dep_changed = 'changed'

    # TODO dont use sys.stdout on tests.
    def setUp(self):
        self.task = self.FakeTask()

        # capture stdout
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()

    def tearDown(self):
        sys.stdout.close()
        sys.stdout = self.oldOut

    def test_no_extra_args(self):
        def py_callable():
            return True
        action = task.PythonAction(py_callable)
        action.task = self.task
        action.execute()

    def test_keyword_extra_args(self):
        def py_callable(arg=None, **kwargs):
            print kwargs['targets']
            print kwargs['dependencies']
            print kwargs['changed']
            return True
        action = task.PythonAction(py_callable)
        action.task = self.task
        action.execute(stdout=None)
        got = sys.stdout.getvalue().splitlines()
        assert got == ['targets', 'dependencies', 'changed']

    def test_named_extra_args(self):
        def py_callable(targets, dependencies, changed):
            print targets
            print dependencies
            print changed
            return True
        action = task.PythonAction(py_callable)
        action.task = self.task
        action.execute(stdout=None)
        got = sys.stdout.getvalue().splitlines()
        assert got == ['targets', 'dependencies', 'changed']

    def test_mixed_args(self):
        def py_callable(a, b, changed):
            print a
            print b
            print changed
            return True
        action = task.PythonAction(py_callable, ('a', 'b'))
        action.task = self.task
        action.execute(stdout=None)
        got = sys.stdout.getvalue().splitlines()
        assert got == ['a', 'b', 'changed']

    def test_extra_arg_overwritten(self):
        def py_callable(a, b, changed):
            print a
            print b
            print changed
            return True
        action = task.PythonAction(py_callable, ('a', 'b', 'c'))
        action.task = self.task
        action.execute(stdout=None)
        got = sys.stdout.getvalue().splitlines()
        assert got == ['a', 'b', 'c']

    def test_extra_kwarg_overwritten(self):
        def py_callable(a, b, **kwargs):
            print a
            print b
            print kwargs['changed']
            return True
        action = task.PythonAction(py_callable, ('a', 'b'), {'changed': 'c'})
        action.task = self.task
        action.execute(stdout=None)
        got = sys.stdout.getvalue().splitlines()
        assert got == ['a', 'b', 'c']

    def test_extra_arg_default_disallowed(self):
        def py_callable(a, b, changed=None): pass
        action = task.PythonAction(py_callable, ('a', 'b'))
        action.task = self.task
        assert_raises(task.InvalidTask, action.execute)
