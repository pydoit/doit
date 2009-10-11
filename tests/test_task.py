import os
import sys, StringIO

from nose.tools import assert_raises

from doit import TaskError, TaskFailed
from doit import task

#path to test folder
TEST_PATH = os.path.dirname(__file__)
PROGRAM = "python %s/sample_process.py" % TEST_PATH


############# CmdAction
class TestCmdAction(object):
    # if nothing is raised it is successful
    def test_success(self):
        action = task.CmdAction(PROGRAM)
        action.execute()

    def test_error(self):
        action = task.CmdAction("%s 1 2 3" % PROGRAM)
        assert_raises(TaskError, action.execute)

    def test_failure(self):
        action = task.CmdAction("%s please fail" % PROGRAM)
        assert_raises(TaskFailed, action.execute)

    def test_str(self):
        action = task.CmdAction(PROGRAM)
        assert "Cmd: %s" % PROGRAM == str(action)

    def test_repr(self):
        action = task.CmdAction(PROGRAM)
        expected = "<CmdAction: '%s'>" % PROGRAM
        assert  expected == repr(action), repr(action)


class TestCmdVerbosity(object):
    def setUp(self):
        self.tmp = os.tmpfile()

    def tearDown(self):
        self.tmp.close()

    def tmp_read(self):
        self.tmp.seek(0)
        return self.tmp.read()

    # Capture stderr
    def test_captureStderr(self):
        cmd = "%s please fail" % PROGRAM
        action = task.CmdAction(cmd)
        assert_raises(TaskFailed, action.execute)
        assert "err output on failure" == action.err, repr(action.err)

    # Capture stdout
    def test_captureStdout(self):
        action = task.CmdAction("%s hi_stdout hi2" % PROGRAM)
        action.execute()
        assert "hi_stdout" == action.out, repr(action.out)

    # Do not capture stderr
    # test using a tempfile. it is not possible (at least i dont know)
    # how to test if the output went to the parent process,
    # faking sys.stderr with a StringIO doesnt work.
    def test_noCaptureStderr(self):
        action = task.CmdAction("%s please fail" % PROGRAM)
        assert_raises(TaskFailed, action.execute, err=self.tmp)
        got = self.tmp_read()
        assert "err output on failure" == got, repr(got)
        assert "err output on failure" == action.err, repr(action.err)

    # Do not capture stdout
    def test_noCaptureStdout(self):
        action = task.CmdAction("%s hi_stdout hi2" % PROGRAM)
        action.execute(out=self.tmp)
        got = self.tmp_read()
        assert "hi_stdout" == got, repr(got)
        assert "hi_stdout" == action.out, repr(action.out)


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



class TestPythonVerbosity(object):
    def write_stderr(self):
        sys.stderr.write("this is stderr S\n")

    def write_stdout(self):
        sys.stdout.write("this is stdout S\n")

    def test_captureStderr(self):
        action = task.PythonAction(self.write_stderr)
        action.execute()
        assert "this is stderr S\n" == action.err, repr(action.err)

    def test_captureStdout(self):
        action = task.PythonAction(self.write_stdout)
        action.execute()
        assert "this is stdout S\n" == action.out, repr(action.out)

    def test_noCaptureStderr(self):
        # fake stderr
        oldErr = sys.stderr
        sys.stderr = StringIO.StringIO()
        try:
            # execute task
            action = task.PythonAction(self.write_stderr)
            action.execute(err=sys.stderr)
            got = sys.stderr.getvalue()
        finally:
            # restore stderr
            sys.stderr.close()
            sys.stderr = oldErr
        assert "this is stderr S\n" == got, repr(got)

    def test_noCaptureStdout(self):
        # fake stderr
        oldOut = sys.stdout
        sys.stdout = StringIO.StringIO()
        try:
            # execute task
            action = task.PythonAction(self.write_stdout)
            action.execute(out=sys.stdout)
            got = sys.stdout.getvalue()
        finally:
            # restore stderr
            sys.stdout.close()
            sys.stdout = oldOut
        assert "this is stdout S\n" == got, repr(got)

    def test_redirectStderr(self):
        tmpfile = os.tmpfile()
        action = task.PythonAction(self.write_stderr)
        action.execute(err=tmpfile)
        tmpfile.seek(0)
        got = tmpfile.read()
        tmpfile.close()
        assert "this is stderr S\n" == got, got

    def test_redirectStdout(self):
        tmpfile = os.tmpfile()
        action = task.PythonAction(self.write_stdout)
        action.execute(out=tmpfile)
        tmpfile.seek(0)
        got = tmpfile.read()
        tmpfile.close()
        assert "this is stdout S\n" == got, got


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
    def test_success(self):
        t = task.Task("taskX", [PROGRAM])
        t.execute()

    def test_failure(self):
        t = task.Task("taskX", ["%s 1 2 3" % PROGRAM])
        assert_raises(TaskError, t.execute)

    # make sure all cmds are being executed.
    def test_many(self):
        t = task.Task("taskX",["%s hi_stdout hi2" % PROGRAM,
                               "%s hi_list hi6" % PROGRAM])
        t.execute()
        got = "".join([a.out for a in t.actions])
        assert "hi_stdouthi_list" == got, repr(got)


    def test_fail_first(self):
        t = task.Task("taskX", ["%s 1 2 3" % PROGRAM, PROGRAM])
        assert_raises(TaskError, t.execute)

    def test_fail_second(self):
        t = task.Task("taskX", ["%s 1 2" % PROGRAM, "%s 1 2 3" % PROGRAM])
        assert_raises(TaskError, t.execute)


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
        t.execute()

        got = t.actions[0].out.split('-')
        assert t.file_dep == got[0].split(), got[0]
        assert t.dep_changed == got[1].split(), got[1]
        assert targets == got[2].split(), got[2]


class TestPythonActionExtraArgs(object):
    def setUp(self):
        self.task = task.Task('name',None,['dependencies'],['targets'])
        self.task.dep_changed = ['changed']

    def test_no_extra_args(self):
        def py_callable():
            return True
        action = task.PythonAction(py_callable)
        action.task = self.task
        action.execute()

    def test_keyword_extra_args(self):
        got = []
        def py_callable(arg=None, **kwargs):
            got.append(kwargs['targets'])
            got.append(kwargs['dependencies'])
            got.append(kwargs['changed'])
        action = task.PythonAction(py_callable)
        action.task = self.task
        action.execute()
        assert got == [['targets'], ['dependencies'], ['changed']], got

    def test_named_extra_args(self):
        got = []
        def py_callable(targets, dependencies, changed):
            got.append(targets)
            got.append(dependencies)
            got.append(changed)
        action = task.PythonAction(py_callable)
        action.task = self.task
        action.execute()
        assert got == [['targets'], ['dependencies'], ['changed']]

    def test_mixed_args(self):
        got = []
        def py_callable(a, b, changed):
            got.append(a)
            got.append(b)
            got.append(changed)
        action = task.PythonAction(py_callable, ('a', 'b'))
        action.task = self.task
        action.execute()
        assert got == ['a', 'b', ['changed']]

    def test_extra_arg_overwritten(self):
        got = []
        def py_callable(a, b, changed):
            got.append(a)
            got.append(b)
            got.append(changed)
        action = task.PythonAction(py_callable, ('a', 'b', 'c'))
        action.task = self.task
        action.execute()
        assert got == ['a', 'b', 'c']

    def test_extra_kwarg_overwritten(self):
        got = []
        def py_callable(a, b, **kwargs):
            got.append(a)
            got.append(b)
            got.append(kwargs['changed'])
        action = task.PythonAction(py_callable, ('a', 'b'), {'changed': 'c'})
        action.task = self.task
        action.execute()
        assert got == ['a', 'b', 'c']

    def test_extra_arg_default_disallowed(self):
        def py_callable(a, b, changed=None): pass
        action = task.PythonAction(py_callable, ('a', 'b'))
        action.task = self.task
        assert_raises(task.InvalidTask, action.execute)
