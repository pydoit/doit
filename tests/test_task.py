import os
import sys, StringIO

from nose.tools import assert_raises

from doit import logger
from doit import task

#path to test folder
TEST_PATH = os.path.abspath(__file__+'/../')


############# CmdAction

class TestCmdAction(object):

    # if nothing is raised it is successful
    def test_success(self):
        t = task.CmdAction("python %s/sample_process.py"%TEST_PATH)
        t.execute()

    def test_error(self):
        t = task.CmdAction("python %s/sample_process.py 1 2 3"%TEST_PATH)
        assert_raises(task.TaskError, t.execute)

    def test_failure(self):
        cmd = "python %s/sample_process.py please fail" % TEST_PATH
        t = task.CmdAction(cmd)
        assert_raises(task.TaskFailed, t.execute)

    def test_str(self):
        t = task.CmdAction("python %s/sample_process.py"%TEST_PATH)
        assert "Cmd: python %s/sample_process.py"%TEST_PATH == str(t), str(t)

    def test_repr(self):
        t = task.CmdAction("python %s/sample_process.py"%TEST_PATH)
        expected = "<CmdAction: 'python %s/sample_process.py'>"%TEST_PATH
        assert  expected == repr(t), repr(t)


class TestCmdVerbosityStderr(object):
    def setUp(self):
        # capture stderr
        self.oldErr = sys.stderr
        sys.stderr = StringIO.StringIO()
        logger.clear("stderr")

    def tearDown(self):
        sys.stderr.close()
        sys.stderr = self.oldErr

    # Capture stderr
    def test_capture(self):
        cmd = "python %s/sample_process.py please fail" % TEST_PATH
        t = task.CmdAction(cmd)
        assert_raises(task.TaskFailed, t.execute, capture_stderr=True)
        assert "" == sys.stderr.getvalue()
        logger.flush('stderr',sys.stderr)
        got = sys.stderr.getvalue()
        assert "err output on failure" == got, got


    # Do not capture stderr
    #
    # i dont know how to test this (in a reasonable easy way).
    # the stream is sent straight to the parent process from doit.
    def test_noCapture(self):
        t = task.CmdAction("python %s/sample_process.py please fail"%TEST_PATH)
        assert_raises(task.TaskFailed, t.execute, capture_stderr=False)
        assert "" == sys.stderr.getvalue(),repr(sys.stderr.getvalue())
        logger.flush('stderr',sys.stderr)
        assert "" == sys.stderr.getvalue(),repr(sys.stderr.getvalue())



class TestCmdVerbosityStdout(object):
    def setUp(self):
        # capture stdout
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()
        logger.clear("stdout")

    def tearDown(self):
        sys.stdout.close()
        sys.stdout = self.oldOut

    # Capture stdout
    def test_capture(self):
        cmd = "python %s/sample_process.py hi_stdout hi2" % TEST_PATH
        t = task.CmdAction(cmd)
        t.execute(capture_stdout = True)
        assert "" == sys.stdout.getvalue()
        logger.flush('stdout',sys.stdout)
        assert "hi_stdout" == sys.stdout.getvalue(),repr(sys.stdout.getvalue())


    # Do not capture stdout
    #
    # i dont know how to test this (in a reasonable easy way).
    # the stream is sent straight to the parent process from doit.
    def test_noCapture(self):
        cmd = "python %s/sample_process.py hi_stdout hi2" % TEST_PATH
        t = task.CmdAction(cmd)
        t.execute(capture_stdout = False)
        assert "" == sys.stdout.getvalue(),repr(sys.stdout.getvalue())
        logger.flush('stdout',sys.stdout)
        assert "" == sys.stdout.getvalue(),repr(sys.stdout.getvalue())



############# PythonAction

class TestPythonAction(object):

    def test_success(self):
        def success_sample():return True
        t = task.PythonAction(success_sample)
        t.execute() # nothing raised it was successful

    def test_error(self):
        def error_sample(): raise Exception("asdf")
        t = task.PythonAction(error_sample)
        assert_raises(task.TaskError, t.execute)

    def test_fail(self):
        def fail_sample():return False
        t = task.PythonAction(fail_sample)
        assert_raises(task.TaskFailed, t.execute)

    # any callable should work, not only functions
    def test_nonFunction(self):
        class CallMe:
            def __call__(self):
                return False

        t = task.PythonAction(CallMe())
        assert_raises(task.TaskFailed, t.execute)

    # helper to test callable with parameters
    def _func_par(self,par1,par2,par3=5):
        if par1 == par2 and par3 > 10:
            return True
        else:
            return False


    def test_init(self):
        # default values
        t1 = task.PythonAction(self._func_par)
        assert t1.args == []
        assert t1.kwargs == {}

        # not a callable
        assert_raises(task.InvalidTask, task.PythonAction, "abc")
        # args not a list
        assert_raises(task.InvalidTask, task.PythonAction, self._func_par, "c")
        # kwargs not a list
        assert_raises(task.InvalidTask, task.PythonAction,
                      self._func_par, None, "a")


    def test_functionParametersArgs(self):
        t = task.PythonAction(self._func_par,args=(2,2,25))
        t.execute()

    def test_functionParametersKwargs(self):
        t = task.PythonAction(self._func_par,
                              kwargs={'par1':2,'par2':2,'par3':25})
        t.execute()

    def test_functionParameters(self):
        t = task.PythonAction(self._func_par,args=(2,2), kwargs={'par3':25})
        t.execute()

    def test_functionParametersFail(self):
        t = task.PythonAction(self._func_par, args=(2,3), kwargs={'par3':25})
        assert_raises(task.TaskFailed, t.execute)

    def test_str(self):
        def str_sample(): return True
        t = task.PythonAction(str_sample)
        assert "Python: function str_sample" == str(t), "'%s'"%str(t)

    def test_repr(self):
        def repr_sample(): return True
        t = task.PythonAction(repr_sample)
        assert  "<PythonAction: '%s'>" % repr(repr_sample) == repr(t), repr(t)



class TestPythonVerbosityStderr(object):
    def setUp(self):
        # capture stderr
        self.oldErr = sys.stderr
        sys.stderr = StringIO.StringIO()
        logger.clear("stderr")

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
        t = task.PythonAction(self.write_and_success)
        t.execute(capture_stderr = True)
        assert "" == sys.stderr.getvalue()
        logger.flush('stderr',sys.stderr)
        got = sys.stderr.getvalue()
        assert "this is stderr S\n" == got, repr(got)

    # failure
    def test_captureFail(self):
        t = task.PythonAction(self.write_and_fail)
        assert_raises(task.TaskFailed, t.execute, capture_stderr=True)
        assert "" == sys.stderr.getvalue()
        logger.flush('stderr',sys.stderr)
        got = sys.stderr.getvalue()
        assert "this is stderr F\n" == got, repr(got)

    # error
    def test_captureError(self):
        t = task.PythonAction(self.write_and_error)
        assert_raises(task.TaskError, t.execute, capture_stderr=True)
        assert "" == sys.stderr.getvalue()
        logger.flush('stderr',sys.stderr)
        got = sys.stderr.getvalue()
        assert "this is stderr E\n" == got, repr(got)

    ##### Do not capture stderr
    #
    # success
    def test_noCaptureSuccess(self):
        t = task.PythonAction(self.write_and_success)
        t.execute(capture_stderr = False)
        got = sys.stderr.getvalue()
        assert "this is stderr S\n" == got, repr(got)

    # failure
    def test_noCaptureFail(self):
        t = task.PythonAction(self.write_and_fail)
        assert_raises(task.TaskFailed, t.execute, capture_stderr=False)
        got = sys.stderr.getvalue()
        assert "this is stderr F\n" == got, repr(got)

    # error
    def test_noCaptureError(self):
        t = task.PythonAction(self.write_and_error)
        assert_raises(task.TaskError, t.execute, capture_stderr=False)
        got = sys.stderr.getvalue()
        assert "this is stderr E\n" == got, repr(got)


class TestPythonVerbosityStdout(object):
    def setUp(self):
        # capture stdout
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()
        logger.clear("stdout")

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
        t = task.PythonAction(self.write_and_success)
        t.execute(capture_stdout = True)
        assert "" == sys.stdout.getvalue()
        logger.flush('stdout',sys.stdout)
        got = sys.stdout.getvalue()
        assert "this is stdout S\n" == got, repr(got)

    # failure
    def test_captureFail(self):
        t = task.PythonAction(self.write_and_fail)
        assert_raises(task.TaskFailed, t.execute, capture_stdout=True)
        assert "" == sys.stdout.getvalue()
        logger.flush('stdout',sys.stdout)
        got = sys.stdout.getvalue()
        assert "this is stdout F\n" == got, repr(got)

    # error
    def test_captureError(self):
        t = task.PythonAction(self.write_and_error)
        assert_raises(task.TaskError, t.execute, capture_stdout=True)
        assert "" == sys.stdout.getvalue()
        logger.flush('stdout',sys.stdout)
        got = sys.stdout.getvalue()
        assert "this is stdout E\n" == got, repr(got)

    ##### Do not capture stdout
    #
    # success
    def test_noCaptureSuccess(self):
        t = task.PythonAction(self.write_and_success)
        t.execute(capture_stdout=False)
        got = sys.stdout.getvalue()
        assert "this is stdout S\n" == got, repr(got)

    # failure
    def test_noCaptureFail(self):
        t = task.PythonAction(self.write_and_fail)
        assert_raises(task.TaskFailed, t.execute, capture_stdout=False)
        got = sys.stdout.getvalue()
        assert "this is stdout F\n" == got, repr(got)

    # error
    def test_noCaptureError(self):
        t = task.PythonAction(self.write_and_error)
        assert_raises(task.TaskError, t.execute, capture_stdout=False)
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




class TestTask(object):


    def test_groupTask(self):
        # group tasks have no action
        t = task.Task("taskX", None)
        assert t.actions == []

    # DEPRECATED - simple action is transformed into a list
    def test_mustSubclass(self):
        t = task.Task("MyName", "single_task")
        assert type(t.actions) is list
        assert 1 == len(t.actions)

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


    # targets must be a sequence. give proper error message when anything
    # else is used.
    def test_targetNotSequence(self):
        filePath = "data/target1"
        assert_raises(task.InvalidTask, task.Task,
                      "Task X",["taskcmd"], targets=filePath)

    def test_title(self):
        t = task.Task("MyName",["MyAction"])
        assert "MyName => %s"%str(t) == t.title(), t.title()


    def test_strGroup(self):
        t = task.Task("taskX",None,('t1','t2'))
        assert "Group: t1, t2" == str(t), "'%s'"%str(t)


    # dependency types going to the write place
    def test_dependencyTypes(self):
        dep = ["file1.txt",":taskX","folderA/","pathB/","file2"]
        t = task.Task("MyName", ["MyAction"], dep)
        assert t.dependencies == dep
        assert t.folder_dep == [dep[2],dep[3]]
        assert t.task_dep == [dep[1][1:]]
        assert t.file_dep == [dep[0],dep[4]]



class TestTaskActions(object):
    def setUp(self):
        # capture stdout
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()
        logger.clear("stdout")

    def tearDown(self):
        sys.stdout.close()
        sys.stdout = self.oldOut

    def test_success(self):
        t = task.Task("taskX", ["python %s/sample_process.py" % TEST_PATH])
        t.execute()

    def test_failure(self):
        t = task.Task("taskX", ["python %s/sample_process.py 1 2 3" % TEST_PATH])
        assert_raises(task.TaskError, t.execute)

    # make sure all cmds are being executed.
    def test_many(self):
        t = task.Task("taskX",[
                "python %s/sample_process.py hi_stdout hi2"%TEST_PATH,
                "python %s/sample_process.py hi_list hi6"%TEST_PATH])
        t.execute(capture_stdout=True)
        assert "" == sys.stdout.getvalue()
        logger.flush('stdout',sys.stdout)
        got = sys.stdout.getvalue()
        assert "hi_stdouthi_list" == got, repr(got)


    def test_fail_first(self):
        t = task.Task("taskX", ["python %s/sample_process.py 1 2 3" % TEST_PATH,
                                "python %s/sample_process.py " % TEST_PATH])
        assert_raises(task.TaskError, t.execute)

    def test_fail_second(self):
        t = task.Task("taskX", ["python %s/sample_process.py 1 2" % TEST_PATH,
                                "python %s/sample_process.py 1 2 3" % TEST_PATH])
        assert_raises(task.TaskError, t.execute)


    # python and commands mixed on same task
    def test_mixed(self):
        def my_print(msg):
            print msg,
            return True
        t = task.Task("taskX",[
                "python %s/sample_process.py hi_stdout hi2"%TEST_PATH,
                (my_print,['_PY_']),
                "python %s/sample_process.py hi_list hi6"%TEST_PATH])
        t.execute(capture_stdout=True)
        assert "" == sys.stdout.getvalue()
        logger.flush('stdout',sys.stdout)
        got = sys.stdout.getvalue()
        assert "hi_stdout_PY_hi_list" == got, repr(got)


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

    # deprecated
    def testDeprecatedAction(self):
        dict_ = {'name':'simple','action':['xpto 14']}
        t = task.dict_to_task(dict_)
        assert isinstance(t, task.Task)
        assert not hasattr(t, 'action')
        assert hasattr(t, 'actions')


class TestCmdFormatting(object):
    def setUp(self):
        # capture stdout
        self.oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()

    def tearDown(self):
        sys.stdout.close()
        sys.stdout = self.oldOut

    def test_task_meta_reference(self):
        cmd = "python %s/myecho.py" % TEST_PATH
        cmd += " %(dependencies)s - %(changed)s - %(targets)s"
        dependencies = ["data/dependency1", "data/dependency2"]
        targets = ["data/target", "data/targetXXX"]
        t = task.Task('formating', [cmd], dependencies, targets)
        t.dep_changed = ["data/dependency1"]
        t.execute(capture_stdout=True)
        logger.flush('stdout',sys.stdout)

        got = sys.stdout.getvalue().split('-')
        assert dependencies == got[0].split(), got[0]
        assert t.dep_changed == got[1].split(), got[1]
        assert targets == got[2].split(), got[2]


