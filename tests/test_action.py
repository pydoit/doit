# coding=UTF-8

import os
import sys
import StringIO
import tempfile

import pytest
from mock import Mock

from doit import action
from doit.exceptions import TaskError, TaskFailed

#path to test folder
TEST_PATH = os.path.dirname(__file__)
PROGRAM = "python %s/sample_process.py" % TEST_PATH


def create_tempfile():
    return tempfile.TemporaryFile('w+b')

def pytest_funcarg__tmpfile(request):
    """crate a temporary file"""
    return request.cached_setup(
        setup=create_tempfile,
        teardown=(lambda tmpfile: tmpfile.close()),
        scope="function")

class FakeTask(object):
    def __init__(self, file_dep, dep_changed, targets, options):
        self.name = "Fake"
        self.file_dep = file_dep
        self.dep_changed = dep_changed
        self.targets = targets
        self.options = options


############# CmdAction
class TestCmdAction(object):
    # if nothing is raised it is successful
    def test_success(self):
        my_action = action.CmdAction(PROGRAM)
        got = my_action.execute()
        assert got is None

    def test_error(self):
        my_action = action.CmdAction("%s 1 2 3" % PROGRAM)
        got = my_action.execute()
        assert isinstance(got, TaskError)

    def test_failure(self):
        my_action = action.CmdAction("%s please fail" % PROGRAM)
        got = my_action.execute()
        assert isinstance(got, TaskFailed)

    def test_str(self):
        my_action = action.CmdAction(PROGRAM)
        assert "Cmd: %s" % PROGRAM == str(my_action)

    def test_unicode(self):
        action_str = unicode(PROGRAM) + u"中文"
        my_action = action.CmdAction(action_str)
        assert "Cmd: %s" % action_str == unicode(my_action)

    def test_repr(self):
        my_action = action.CmdAction(PROGRAM)
        expected = "<CmdAction: '%s'>" % PROGRAM
        assert  expected == repr(my_action), repr(my_action)

    def test_result(self):
        my_action = action.CmdAction("%s 1 2" % PROGRAM)
        my_action.execute()
        assert "12" == my_action.result

    def test_values(self):
        # for cmdActions they are always empty
        my_action = action.CmdAction("%s 1 2" % PROGRAM)
        my_action.execute()
        assert {} == my_action.values

    def test_clone(self):
        my_action = action.CmdAction("%s 1 2" % PROGRAM, "x")
        clone = my_action.clone('y')
        assert my_action.action == clone.action
        assert 'y' == clone.task


class TestCmdVerbosity(object):
    # Capture stderr
    def test_captureStderr(self):
        cmd = "%s please fail" % PROGRAM
        my_action = action.CmdAction(cmd)
        got = my_action.execute()
        assert isinstance(got, TaskFailed)
        assert "err output on failure" == my_action.err, repr(my_action.err)

    # Capture stdout
    def test_captureStdout(self):
        my_action = action.CmdAction("%s hi_stdout hi2" % PROGRAM)
        my_action.execute()
        assert "hi_stdout" == my_action.out, repr(my_action.out)

    # Do not capture stderr
    # test using a tempfile. it is not possible (at least i dont know)
    # how to test if the output went to the parent process,
    # faking sys.stderr with a StringIO doesnt work.
    def test_noCaptureStderr(self, tmpfile):
        my_action = action.CmdAction("%s please fail" % PROGRAM)
        action_result = my_action.execute(err=tmpfile)
        assert isinstance(action_result, TaskFailed)
        tmpfile.seek(0)
        got = tmpfile.read().decode('utf-8')
        assert "err output on failure" == got, repr(got)
        assert "err output on failure" == my_action.err, repr(my_action.err)

    # Do not capture stdout
    def test_noCaptureStdout(self, tmpfile):
        my_action = action.CmdAction("%s hi_stdout hi2" % PROGRAM)
        my_action.execute(out=tmpfile)
        tmpfile.seek(0)
        got = tmpfile.read().decode('utf-8')
        assert "hi_stdout" == got, repr(got)
        assert "hi_stdout" == my_action.out, repr(my_action.out)


class TestCmdExpandAction(object):

    def test_task_meta_reference(self):
        cmd = "python %s/myecho.py" % TEST_PATH
        cmd += " %(dependencies)s - %(changed)s - %(targets)s"
        dependencies = ["data/dependency1", "data/dependency2", ":dep_on_task"]
        targets = ["data/target", "data/targetXXX"]
        task = FakeTask(dependencies, ["data/dependency1"], targets, {})
        my_action = action.CmdAction(cmd, task)
        my_action.execute()

        got = my_action.out.split('-')
        assert task.file_dep == got[0].split(), got[0]
        assert task.dep_changed == got[1].split(), got[1]
        assert targets == got[2].split(), got[2]

    def test_task_options(self):
        cmd = "python %s/myecho.py" % TEST_PATH
        cmd += " %(opt1)s - %(opt2)s"
        task = FakeTask([],[],[],{'opt1':'3', 'opt2':'abc def'})
        my_action = action.CmdAction(cmd, task)
        my_action.execute()

        got = my_action.out.strip()
        assert "3 - abc def" == got, repr(got)



class TestCmd_print_process_output(object):
    def test_non_unicode_string(self):
        my_action = action.CmdAction("")
        not_unicode = StringIO.StringIO('\xc0')
        pytest.raises(Exception, my_action._print_process_output,
                       Mock(), not_unicode, Mock(), Mock())

    def test_unicode_string(self, tmpfile):
        my_action = action.CmdAction("")
        unicode_in = create_tempfile()
        unicode_in.write(u" 中文".encode('utf-8'))
        unicode_in.seek(0)
        my_action._print_process_output(Mock(), unicode_in, Mock(), tmpfile)

    def test_unicode_string2(self, tmpfile):
        # this \uXXXX has a different behavior!
        my_action = action.CmdAction("")
        unicode_in = create_tempfile()
        unicode_in.write(u" 中文 \u2018".encode('utf-8'))
        unicode_in.seek(0)
        my_action._print_process_output(Mock(), unicode_in, Mock(), tmpfile)



class TestWriter(object):
    def test_writer(self):
        w1 = StringIO.StringIO()
        w2 = StringIO.StringIO()
        writer = action.Writer(w1, w2)
        writer.flush() # make sure flush is supported
        writer.write("hello")
        assert "hello" == w1.getvalue()
        assert "hello" == w2.getvalue()


############# PythonAction

class TestPythonAction(object):

    def test_success_bool(self):
        def success_sample():return True
        my_action = action.PythonAction(success_sample)
        # nothing raised it was successful
        my_action.execute()

    def test_success_None(self):
        def success_sample():return
        my_action = action.PythonAction(success_sample)
        # nothing raised it was successful
        my_action.execute()

    def test_success_str(self):
        def success_sample():return ""
        my_action = action.PythonAction(success_sample)
        # nothing raised it was successful
        my_action.execute()

    def test_success_dict(self):
        def success_sample():return {}
        my_action = action.PythonAction(success_sample)
        # nothing raised it was successful
        my_action.execute()

    def test_error_object(self):
        # anthing but None, bool, string or dict
        def error_sample(): return object()
        my_action = action.PythonAction(error_sample)
        got = my_action.execute()
        assert isinstance(got, TaskError)

    def test_error_exception(self):
        def error_sample(): raise Exception("asdf")
        my_action = action.PythonAction(error_sample)
        got = my_action.execute()
        assert isinstance(got, TaskError)

    def test_fail_bool(self):
        def fail_sample():return False
        my_action = action.PythonAction(fail_sample)
        got = my_action.execute()
        assert isinstance(got, TaskFailed)

    # any callable should work, not only functions
    def test_nonFunction(self):
        class CallMe:
            def __call__(self):
                return False

        my_action = action.PythonAction(CallMe())
        got = my_action.execute()
        assert isinstance(got, TaskFailed)

    # helper to test callable with parameters
    def _func_par(self,par1,par2,par3=5):
        if par1 == par2 and par3 > 10:
            return True
        else:
            return False


    def test_init(self):
        # default values
        action1 = action.PythonAction(self._func_par)
        assert action1.args == []
        assert action1.kwargs == {}

        # not a callable
        pytest.raises(action.InvalidTask, action.PythonAction, "abc")
        # args not a list
        pytest.raises(action.InvalidTask, action.PythonAction, self._func_par, "c")
        # kwargs not a list
        pytest.raises(action.InvalidTask, action.PythonAction,
                      self._func_par, None, "a")


    def test_functionParametersArgs(self):
        my_action = action.PythonAction(self._func_par,args=(2,2,25))
        my_action.execute()

    def test_functionParametersKwargs(self):
        my_action = action.PythonAction(self._func_par,
                              kwargs={'par1':2,'par2':2,'par3':25})
        my_action.execute()

    def test_functionParameters(self):
        my_action = action.PythonAction(self._func_par,args=(2,2),
                                   kwargs={'par3':25})
        my_action.execute()

    def test_functionParametersFail(self):
        my_action = action.PythonAction(self._func_par, args=(2,3),
                                   kwargs={'par3':25})
        got = my_action.execute()
        assert isinstance(got, TaskFailed)

    def test_str(self):
        def str_sample(): return True
        my_action = action.PythonAction(str_sample)
        assert "Python: function str_sample" == str(my_action), "'%s'"%str(my_action)

    def test_repr(self):
        def repr_sample(): return True
        my_action = action.PythonAction(repr_sample)
        assert  "<PythonAction: '%s'>" % repr(repr_sample) == repr(my_action)

    def test_result(self):
        def vvv(): return "my value"
        my_action = action.PythonAction(vvv)
        my_action.execute()
        assert "my value" == my_action.result

    def test_values(self):
        def vvv(): return {'x': 5, 'y':10}
        my_action = action.PythonAction(vvv)
        my_action.execute()
        assert {'x': 5, 'y':10} == my_action.values

    def test_clone(self):
        def aaa(): return 1
        my_action = action.PythonAction(aaa, (3,), {'1':2}, 'x')
        clone = my_action.clone('y')
        assert my_action.py_callable == clone.py_callable
        assert my_action.args == clone.args
        assert my_action.kwargs == clone.kwargs
        assert 'y' == clone.task


class TestPythonVerbosity(object):
    def write_stderr(self):
        sys.stderr.write("this is stderr S\n")

    def write_stdout(self):
        sys.stdout.write("this is stdout S\n")

    def test_captureStderr(self):
        my_action = action.PythonAction(self.write_stderr)
        my_action.execute()
        assert "this is stderr S\n" == my_action.err, repr(my_action.err)

    def test_captureStdout(self):
        my_action = action.PythonAction(self.write_stdout)
        my_action.execute()
        assert "this is stdout S\n" == my_action.out, repr(my_action.out)

    def test_noCaptureStderr(self, capsys):
        my_action = action.PythonAction(self.write_stderr)
        my_action.execute(err=sys.stderr)
        got = capsys.readouterr()[1]
        assert "this is stderr S\n" == got, repr(got)

    def test_noCaptureStdout(self, capsys):
        my_action = action.PythonAction(self.write_stdout)
        my_action.execute(out=sys.stdout)
        got = capsys.readouterr()[0]
        assert "this is stdout S\n" == got, repr(got)

    def test_redirectStderr(self):
        tmpfile = tempfile.TemporaryFile('w+')
        my_action = action.PythonAction(self.write_stderr)
        my_action.execute(err=tmpfile)
        tmpfile.seek(0)
        got = tmpfile.read()
        tmpfile.close()
        assert "this is stderr S\n" == got, got

    def test_redirectStdout(self):
        tmpfile = tempfile.TemporaryFile('w+')
        my_action = action.PythonAction(self.write_stdout)
        my_action.execute(out=tmpfile)
        tmpfile.seek(0)
        got = tmpfile.read()
        tmpfile.close()
        assert "this is stdout S\n" == got, got


class TestPythonActionPrepareKwargsMeta(object):

    def pytest_funcarg__task_depchanged(self, request):
        def create_task_depchanged():
            task = FakeTask(['dependencies'],['changed'],['targets'],{})
            return task
        return request.cached_setup(
            setup=create_task_depchanged,
            scope="function")

    def test_no_extra_args(self, task_depchanged):
        def py_callable():
            return True
        my_action = action.PythonAction(py_callable, task=task_depchanged)
        my_action.execute()

    def test_keyword_extra_args(self, task_depchanged):
        got = []
        def py_callable(arg=None, **kwargs):
            got.append(kwargs['targets'])
            got.append(kwargs['dependencies'])
            got.append(kwargs['changed'])
        my_action = action.PythonAction(py_callable, task=task_depchanged)
        my_action.execute()
        assert got == [['targets'], ['dependencies'], ['changed']], got

    def test_named_extra_args(self, task_depchanged):
        got = []
        def py_callable(targets, dependencies, changed):
            got.append(targets)
            got.append(dependencies)
            got.append(changed)
        my_action = action.PythonAction(py_callable, task=task_depchanged)
        my_action.execute()
        assert got == [['targets'], ['dependencies'], ['changed']]

    def test_mixed_args(self, task_depchanged):
        got = []
        def py_callable(a, b, changed):
            got.append(a)
            got.append(b)
            got.append(changed)
        my_action = action.PythonAction(py_callable, ('a', 'b'),
                                        task=task_depchanged)
        my_action.execute()
        assert got == ['a', 'b', ['changed']]

    def test_extra_arg_overwritten(self, task_depchanged):
        got = []
        def py_callable(a, b, changed):
            got.append(a)
            got.append(b)
            got.append(changed)
        my_action = action.PythonAction(py_callable, ('a', 'b', 'c'),
                                        task=task_depchanged)
        my_action.execute()
        assert got == ['a', 'b', 'c']

    def test_extra_kwarg_overwritten(self, task_depchanged):
        got = []
        def py_callable(a, b, **kwargs):
            got.append(a)
            got.append(b)
            got.append(kwargs['changed'])
        my_action = action.PythonAction(py_callable, ('a', 'b'),
                                        {'changed': 'c'}, task_depchanged)
        my_action.execute()
        assert got == ['a', 'b', 'c']

    def test_extra_arg_default_disallowed(self, task_depchanged):
        def py_callable(a, b, changed=None): pass
        my_action = action.PythonAction(py_callable, ('a', 'b'),
                                        task=task_depchanged)
        pytest.raises(action.InvalidTask, my_action.execute)

class TestPythonActionOptions(object):
    def test_task_options(self):
        got = []
        def py_callable(opt1, opt3):
            got.append(opt1)
            got.append(opt3)
        task = FakeTask([],[],[],{'opt1':'1', 'opt2':'abc def', 'opt3':3})
        my_action = action.PythonAction(py_callable, task=task)
        my_action.execute()
        assert ['1',3] == got, repr(got)


##############


class TestCreateAction(object):
    class TaskStub(object):
        name = 'stub'
    mytask = TaskStub()

    def testBaseAction(self):
        class Sample(action.BaseAction): pass
        my_action = action.create_action(Sample(), self.mytask)
        assert isinstance(my_action, Sample)
        assert self.mytask == my_action.task

    def testStringAction(self):
        my_action = action.create_action("xpto 14 7", self.mytask)
        assert isinstance(my_action, action.CmdAction)

    def testMethodAction(self):
        def dumb(): return
        my_action = action.create_action(dumb, self.mytask)
        assert isinstance(my_action, action.PythonAction)

    def testTupleAction(self):
        def dumb(): return
        my_action = action.create_action((dumb,[1,2],{'a':5}), self.mytask)
        assert isinstance(my_action, action.PythonAction)

    def testTupleActionMoreThanThreeElements(self):
        def dumb(): return
        pytest.raises(action.InvalidTask, action.create_action,
                       (dumb,[1,2],{'a':5},'oo'), self.mytask)

    def testInvalidActionNone(self):
        pytest.raises(action.InvalidTask, action.create_action,
                       None, self.mytask)

    def testInvalidActionObject(self):
        pytest.raises(action.InvalidTask, action.create_action,
                       self, self.mytask)

