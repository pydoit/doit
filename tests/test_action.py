import os
import sys

import py.test

from doit import action
from doit.exceptions import TaskError, TaskFailed

#path to test folder
TEST_PATH = os.path.dirname(__file__)
PROGRAM = "python %s/sample_process.py" % TEST_PATH


def pytest_funcarg__tmpfile(request):
    """crate a temporary file"""
    return request.cached_setup(
        setup=os.tmpfile,
        teardown=(lambda tmpfile: tmpfile.close()),
        scope="function")



############# CmdAction
class TestCmdAction(object):
    # if nothing is raised it is successful
    def test_success(self):
        my_action = action.CmdAction(PROGRAM)
        my_action.execute()

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
        got = tmpfile.read()
        assert "err output on failure" == got, repr(got)
        assert "err output on failure" == my_action.err, repr(my_action.err)

    # Do not capture stdout
    def test_noCaptureStdout(self, tmpfile):
        my_action = action.CmdAction("%s hi_stdout hi2" % PROGRAM)
        my_action.execute(out=tmpfile)
        tmpfile.seek(0)
        got = tmpfile.read()
        assert "hi_stdout" == got, repr(got)
        assert "hi_stdout" == my_action.out, repr(my_action.out)



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
        py.test.raises(action.InvalidTask, action.PythonAction, "abc")
        # args not a list
        py.test.raises(action.InvalidTask, action.PythonAction, self._func_par, "c")
        # kwargs not a list
        py.test.raises(action.InvalidTask, action.PythonAction,
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
        tmpfile = os.tmpfile()
        my_action = action.PythonAction(self.write_stderr)
        my_action.execute(err=tmpfile)
        tmpfile.seek(0)
        got = tmpfile.read()
        tmpfile.close()
        assert "this is stderr S\n" == got, got

    def test_redirectStdout(self):
        tmpfile = os.tmpfile()
        my_action = action.PythonAction(self.write_stdout)
        my_action.execute(out=tmpfile)
        tmpfile.seek(0)
        got = tmpfile.read()
        tmpfile.close()
        assert "this is stdout S\n" == got, got


##############


class TestCreateAction(object):
    def testBaseAction(self):
        class Sample(action.BaseAction): pass
        my_action = action.create_action(Sample())
        assert isinstance(my_action, Sample)

    def testStringAction(self):
        my_action = action.create_action("xpto 14 7")
        assert isinstance(my_action, action.CmdAction)

    def testMethodAction(self):
        def dumb(): return
        my_action = action.create_action(dumb)
        assert isinstance(my_action, action.PythonAction)

    def testTupleAction(self):
        def dumb(): return
        my_action = action.create_action((dumb,[1,2],{'a':5}))
        assert isinstance(my_action, action.PythonAction)

    def testInvalidActionNone(self):
        py.test.raises(action.InvalidTask, action.create_action, None)

    def testInvalidActionObject(self):
        py.test.raises(action.InvalidTask, action.create_action, self)

