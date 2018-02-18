import os
import sys
import tempfile
import textwrap
import locale
locale # quiet pyflakes
from pathlib import PurePath, Path
from io import StringIO, BytesIO
from threading import Thread
import time
from sys import executable
from unittest.mock import Mock

import pytest

from doit import action
from doit.exceptions import TaskError, TaskFailed


#path to test folder
TEST_PATH = os.path.dirname(__file__)
PROGRAM = "%s %s/sample_process.py" % (executable, TEST_PATH)


@pytest.fixture
def tmpfile(request):
    temp = tempfile.TemporaryFile('w+')
    request.addfinalizer(temp.close)
    return temp


class FakeTask(object):
    def __init__(self, file_dep, dep_changed, targets, options,
                 pos_arg=None, pos_arg_val=None):
        self.name = "Fake"
        self.file_dep = file_dep
        self.dep_changed = dep_changed
        self.targets = targets
        self.options = options
        self.pos_arg = pos_arg
        self.pos_arg_val = pos_arg_val


############# CmdAction
class TestCmdAction(object):
    # if nothing is raised it is successful
    def test_success(self):
        my_action = action.CmdAction(PROGRAM)
        got = my_action.execute()
        assert got is None

    def test_success_noshell(self):
        my_action = action.CmdAction(PROGRAM.split(), shell=False)
        got = my_action.execute()
        assert got is None

    def test_error(self):
        my_action = action.CmdAction("%s 1 2 3" % PROGRAM)
        got = my_action.execute()
        assert isinstance(got, TaskError)

    def test_env(self):
        env = os.environ.copy()
        env['GELKIPWDUZLOVSXE'] = '1'
        my_action = action.CmdAction("%s check env" % PROGRAM, env=env)
        got = my_action.execute()
        assert got is None

    def test_failure(self):
        my_action = action.CmdAction("%s please fail" % PROGRAM)
        got = my_action.execute()
        assert isinstance(got, TaskFailed)

    def test_str(self):
        my_action = action.CmdAction(PROGRAM)
        assert "Cmd: %s" % PROGRAM == str(my_action)

    def test_unicode(self):
        action_str = PROGRAM + "中文"
        my_action = action.CmdAction(action_str)
        assert "Cmd: %s" % action_str == str(my_action)

    def test_repr(self):
        my_action = action.CmdAction(PROGRAM)
        expected = "<CmdAction: '%s'>" % PROGRAM
        assert  expected == repr(my_action), repr(my_action)

    def test_result(self):
        my_action = action.CmdAction("%s 1 2" % PROGRAM)
        my_action.execute()
        assert "12" == my_action.result

    def test_values(self):
        # for cmdActions they are emtpy if save_out not specified
        my_action = action.CmdAction("%s 1 2" % PROGRAM)
        my_action.execute()
        assert {} == my_action.values


class TestCmdActionParams(object):
    def test_invalid_param_stdout(self):
        pytest.raises(action.InvalidTask, action.CmdAction,
                      [PROGRAM], stdout=None)

    def test_changePath(self, tmpdir):
        path = tmpdir.mkdir("foo")
        command = '%s -c "import os; print(os.getcwd())"' % executable
        my_action = action.CmdAction(command, cwd=path.strpath)
        my_action.execute()
        assert path + os.linesep == my_action.out, repr(my_action.out)

    def test_noPathSet(self, tmpdir):
        path = tmpdir.mkdir("foo")
        command = '%s -c "import os; print(os.getcwd())"' % executable
        my_action = action.CmdAction(command)
        my_action.execute()
        assert path.strpath + os.linesep != my_action.out, repr(my_action.out)


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


class TestCmdExpandAction(object):

    def test_task_meta_reference(self):
        cmd = "%s %s/myecho.py" % (executable, TEST_PATH)
        cmd += " %(dependencies)s - %(changed)s - %(targets)s"
        dependencies = ["data/dependency1", "data/dependency2", ":dep_on_task"]
        targets = ["data/target", "data/targetXXX"]
        task = FakeTask(dependencies, ["data/dependency1"], targets, {})
        my_action = action.CmdAction(cmd, task)
        assert my_action.execute() is None

        got = my_action.out.split('-')
        assert task.file_dep == got[0].split(), got[0]
        assert task.dep_changed == got[1].split(), got[1]
        assert targets == got[2].split(), got[2]

    def test_task_options(self):
        cmd = "%s %s/myecho.py" % (executable, TEST_PATH)
        cmd += " %(opt1)s - %(opt2)s"
        task = FakeTask([],[],[],{'opt1':'3', 'opt2':'abc def'})
        my_action = action.CmdAction(cmd, task)
        assert my_action.execute() is None
        got = my_action.out.strip()
        assert "3 - abc def" == got

    def test_task_pos_arg(self):
        cmd = "%s %s/myecho.py" % (executable, TEST_PATH)
        cmd += " %(pos)s"
        task = FakeTask([],[],[],{}, 'pos', ['hi', 'there'])
        my_action = action.CmdAction(cmd, task)
        assert my_action.execute() is None
        got = my_action.out.strip()
        assert "hi there" == got

    def test_task_pos_arg_None(self):
        # pos_arg_val is None when the task is not specified from
        # command line but executed because it is a task_dep
        cmd = "%s %s/myecho.py" % (executable, TEST_PATH)
        cmd += " %(pos)s"
        task = FakeTask([],[],[],{}, 'pos', None)
        my_action = action.CmdAction(cmd, task)
        assert my_action.execute() is None
        got = my_action.out.strip()
        assert "" == got

    def test_callable_return_command_str(self):
        def get_cmd(opt1, opt2):
            cmd = "%s %s/myecho.py" % (executable, TEST_PATH)
            return cmd + " %s - %s" % (opt1, opt2)
        task = FakeTask([],[],[],{'opt1':'3', 'opt2':'abc def'})
        my_action = action.CmdAction(get_cmd, task)
        assert my_action.execute() is None
        got = my_action.out.strip()
        assert "3 - abc def" == got, repr(got)

    def test_callable_tuple_return_command_str(self):
        def get_cmd(opt1, opt2):
            cmd = "%s %s/myecho.py" % (executable, TEST_PATH)
            return cmd + " %s - %s" % (opt1, opt2)
        task = FakeTask([],[],[],{'opt1':'3'})
        my_action = action.CmdAction((get_cmd, [], {'opt2':'abc def'}), task)
        assert my_action.execute() is None
        got = my_action.out.strip()
        assert "3 - abc def" == got, repr(got)

    def test_callable_invalid(self):
        def get_cmd(blabla): pass
        task = FakeTask([],[],[],{'opt1':'3'})
        my_action = action.CmdAction(get_cmd, task)
        got = my_action.execute()
        assert isinstance(got, TaskError)

    def test_string_list_cant_be_expanded(self):
        cmd = [executable,  "%s/myecho.py" % TEST_PATH]
        task = FakeTask([],[],[], {})
        my_action = action.CmdAction(cmd, task)
        assert cmd == my_action.expand_action()

    def test_list_can_contain_path(self):
        cmd = [executable, PurePath(TEST_PATH), Path("myecho.py")]
        task = FakeTask([], [], [], {})
        my_action = action.CmdAction(cmd, task)
        assert [executable, TEST_PATH, "myecho.py"] == my_action.expand_action()

    def test_list_should_contain_strings_or_paths(self):
        cmd = [executable, PurePath(TEST_PATH), 42, Path("myecho.py")]
        task = FakeTask([], [], [], {})
        my_action = action.CmdAction(cmd, task)
        assert pytest.raises(action.InvalidTask, my_action.expand_action)


class TestCmd_print_process_output_line(object):
    def test_non_unicode_string_error_strict(self):
        my_action = action.CmdAction("", decode_error='strict')
        not_unicode = BytesIO('\xa9'.encode("latin-1"))
        realtime = Mock()
        realtime.encoding = 'utf-8'
        pytest.raises(UnicodeDecodeError,
                      my_action._print_process_output,
                      Mock(), not_unicode, Mock(), realtime)

    def test_non_unicode_string_error_replace(self):
        my_action = action.CmdAction("") # default is decode_error = 'replace'
        not_unicode = BytesIO('\xa9'.encode("latin-1"))
        realtime = Mock()
        realtime.encoding = 'utf-8'
        capture = StringIO()
        my_action._print_process_output(
            Mock(), not_unicode, capture, realtime)
        # get the replacement char
        expected = '�'
        assert expected == capture.getvalue()

    def test_non_unicode_string_ok(self):
        my_action = action.CmdAction("", encoding='iso-8859-1')
        not_unicode = BytesIO('\xa9'.encode("latin-1"))
        realtime = Mock()
        realtime.encoding = 'utf-8'
        capture = StringIO()
        my_action._print_process_output(
            Mock(), not_unicode, capture, realtime)
        # get the correct char from latin-1 encoding
        expected = '©'
        assert expected == capture.getvalue()


    # dont test unicode if system locale doesnt support unicode
    # see https://bitbucket.org/schettino72/doit/pull-request/11
    @pytest.mark.skipif('locale.getlocale()[1] is None')
    def test_unicode_string(self, tmpfile):
        my_action = action.CmdAction("")
        unicode_in = tempfile.TemporaryFile('w+b')
        unicode_in.write(" 中文".encode('utf-8'))
        unicode_in.seek(0)
        my_action._print_process_output(
            Mock(), unicode_in, Mock(), tmpfile)

    @pytest.mark.skipif('locale.getlocale()[1] is None')
    def test_unicode_string2(self, tmpfile):
        # this \uXXXX has a different behavior!
        my_action = action.CmdAction("")
        unicode_in = tempfile.TemporaryFile('w+b')
        unicode_in.write(" 中文 \u2018".encode('utf-8'))
        unicode_in.seek(0)
        my_action._print_process_output(
            Mock(), unicode_in, Mock(), tmpfile)

    def test_line_buffered_output(self):
        my_action = action.CmdAction("")
        out, inp = os.pipe()
        out, inp = os.fdopen(out, 'rb'), os.fdopen(inp, 'wb')
        inp.write('abcd\nline2'.encode('utf-8'))
        inp.flush()
        capture = StringIO()

        thread = Thread(target=my_action._print_process_output,
                        args=(Mock(), out, capture, None))
        thread.start()
        time.sleep(0.1)
        try:
            got = capture.getvalue()
            # 'line2' is not captured because of line buffering
            assert 'abcd\n' == got
            print('asserted')
        finally:
            inp.close()

    def test_unbuffered_output(self):
        my_action = action.CmdAction("", buffering=1)
        out, inp = os.pipe()
        out, inp = os.fdopen(out, 'rb'), os.fdopen(inp, 'wb')
        inp.write('abcd\nline2'.encode('utf-8'))
        inp.flush()
        capture = StringIO()

        thread = Thread(target=my_action._print_process_output,
                        args=(Mock(), out, capture, None))
        thread.start()
        time.sleep(0.1)
        try:
            got = capture.getvalue()
            assert 'abcd\nline2' == got
        finally:
            inp.close()


    def test_unbuffered_env(self, monkeypatch):
        my_action = action.CmdAction("", buffering=1)
        proc_mock = Mock()
        proc_mock.configure_mock(returncode=0)
        popen_mock = Mock(return_value=proc_mock)
        from doit.action import subprocess
        monkeypatch.setattr(subprocess, 'Popen', popen_mock)
        my_action._print_process_output = Mock()
        my_action.execute()
        env = popen_mock.call_args[-1]['env']
        assert env and env.get('PYTHONUNBUFFERED', False) == '1'



class TestCmdSaveOuput(object):
    def test_success(self):
        TEST_PATH = os.path.dirname(__file__)
        PROGRAM = "%s %s/sample_process.py" % (executable, TEST_PATH)
        my_action = action.CmdAction(PROGRAM + " x1 x2", save_out='out')
        my_action.execute()
        assert {'out': 'x1'} == my_action.values



class TestWriter(object):
    def test_write(self):
        w1 = StringIO()
        w2 = StringIO()
        writer = action.Writer(w1, w2)
        writer.flush() # make sure flush is supported
        writer.write("hello")
        assert "hello" == w1.getvalue()
        assert "hello" == w2.getvalue()

    def test_isatty_true(self):
        w1 = StringIO()
        w1.isatty = lambda: True
        w2 = StringIO()
        writer = action.Writer(w1, w2)
        assert not writer.isatty()

    def test_isatty_false(self):
        w1 = StringIO()
        w1.isatty = lambda: True
        w2 = StringIO()
        w2.isatty = lambda: True
        writer = action.Writer(w1, w2)
        assert writer.isatty()

    def test_isatty_overwrite_yes(self):
        w1 = StringIO()
        w1.isatty = lambda: True
        w2 = StringIO()
        writer = action.Writer(w1)
        writer.add_writer(w2, True)

    def test_isatty_overwrite_no(self):
        w1 = StringIO()
        w1.isatty = lambda: True
        w2 = StringIO()
        w2.isatty = lambda: True
        writer = action.Writer(w1)
        writer.add_writer(w2, False)


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

    def test_error_taskfail(self):
        # should get the same exception as was returned from the
        # user's function
        def error_sample(): return TaskFailed("too bad")
        ye_olde_action = action.PythonAction(error_sample)
        ret = ye_olde_action.execute()
        assert isinstance(ret, TaskFailed)
        assert str(ret).endswith("too bad\n")

    def test_error_taskerror(self):
        def error_sample(): return TaskError("so sad")
        ye_olde_action = action.PythonAction(error_sample)
        ret = ye_olde_action.execute()
        assert str(ret).endswith("so sad\n")

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
    def test_callable_obj(self):
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

    # cant use a class as callable
    def test_init_callable_class(self):
        class CallMe(object):
            pass
        pytest.raises(action.InvalidTask, action.PythonAction, CallMe)

    # cant use built-ins
    def test_init_callable_builtin(self):
        pytest.raises(action.InvalidTask, action.PythonAction, any)

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
        assert "Python: function" in str(my_action)
        assert "str_sample" in str(my_action)

    def test_repr(self):
        def repr_sample(): return True
        my_action = action.PythonAction(repr_sample)
        assert  "<PythonAction: '%s'>" % repr(repr_sample) == repr(my_action)

    def test_result(self):
        def vvv(): return "my value"
        my_action = action.PythonAction(vvv)
        my_action.execute()
        assert "my value" == my_action.result

    def test_result_dict(self):
        def vvv(): return {'xxx': "my value"}
        my_action = action.PythonAction(vvv)
        my_action.execute()
        assert {'xxx': "my value"} == my_action.result

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

    @pytest.fixture
    def task_depchanged(self, request):
        return FakeTask(['dependencies'],['changed'],['targets'],{})

    def test_no_extra_args(self, task_depchanged):
        # no error trying to inject values
        def py_callable():
            return True
        my_action = action.PythonAction(py_callable, task=task_depchanged)
        my_action.execute()

    def test_keyword_extra_args(self):
        my_task = FakeTask(['dependencies'], None, None, {'foo': 'bar'})
        got = []
        def py_callable(arg=None, **kwargs):
            got.append(kwargs)
        my_action = action.PythonAction(py_callable, (), {'b': 4}, task=my_task)
        my_action.execute()
        # meta args do not leak into kwargs
        assert got == [{'foo': 'bar', 'b': 4}]


    def test_named_extra_args(self, task_depchanged):
        got = []
        def py_callable(targets, dependencies, changed, task):
            got.append(targets)
            got.append(dependencies)
            got.append(changed)
            got.append(task)
        my_action = action.PythonAction(py_callable, task=task_depchanged)
        my_action.execute()
        assert got == [['targets'], ['dependencies'], ['changed'],
                       task_depchanged]

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

    def test_meta_arg_default_disallowed(self, task_depchanged):
        def py_callable(a, b, changed=None): pass
        my_action = action.PythonAction(py_callable, ('a', 'b'),
                                        task=task_depchanged)
        pytest.raises(action.InvalidTask, my_action.execute)

    def test_callable_obj(self, task_depchanged):
        got = []
        class CallMe(object):
            def __call__(self, a, b, changed):
                got.append(a)
                got.append(b)
                got.append(changed)
        my_action = action.PythonAction(CallMe(), ('a', 'b'),
                                        task=task_depchanged)
        my_action.execute()
        assert got == ['a', 'b', ['changed']]

    def test_method(self, task_depchanged):
        got = []
        class CallMe(object):
            def xxx(self, a, b, changed):
                got.append(a)
                got.append(b)
                got.append(changed)
        my_action = action.PythonAction(CallMe().xxx, ('a', 'b'),
                                        task=task_depchanged)
        my_action.execute()
        assert got == ['a', 'b', ['changed']]


    def test_task_options(self):
        got = []
        def py_callable(opt1, opt3):
            got.append(opt1)
            got.append(opt3)
        task = FakeTask([],[],[],{'opt1':'1', 'opt2':'abc def', 'opt3':3})
        my_action = action.PythonAction(py_callable, task=task)
        my_action.execute()
        assert ['1',3] == got, repr(got)

    def test_task_pos_arg(self):
        got = []
        def py_callable(pos):
            got.append(pos)
        task = FakeTask([],[],[],{}, 'pos', ['hi', 'there'])
        my_action = action.PythonAction(py_callable, task=task)
        my_action.execute()
        assert [['hi', 'there']] == got, repr(got)

    def test_option_default_allowed(self, task_depchanged):
        got = []
        def py_callable(opt2='ABC'):
            got.append(opt2)
        task = FakeTask([],[],[],{'opt2':'123'})
        my_action = action.PythonAction(py_callable, task=task)
        my_action.execute()
        assert ['123'] == got, repr(got)


    def test_kwonlyargs_minimal(self, task_depchanged):
        got = []
        scope = {'got': got}
        exec(textwrap.dedent('''
            def py_callable(*args, kwonly=None):
                got.append(args)
                got.append(kwonly)
        '''), scope)
        my_action = action.PythonAction(scope['py_callable'],
                                        (1, 2, 3), {'kwonly': 4},
                                        task=task_depchanged)
        my_action.execute()
        assert [(1, 2, 3), 4] == got, repr(got)


    def test_kwonlyargs_full(self, task_depchanged):
        got = []
        scope = {'got': got}
        exec(textwrap.dedent('''
            def py_callable(pos, *args, kwonly=None, **kwargs):
                got.append(pos)
                got.append(args)
                got.append(kwonly)
                got.append(kwargs['foo'])
        '''), scope)
        my_action = action.PythonAction(scope['py_callable'],
                                        [1,2,3], {'kwonly': 4, 'foo': 5},
                                        task=task_depchanged)
        my_action.execute()
        assert [1, (2, 3), 4, 5] == got, repr(got)

    def test_action_modifies_task_attributes(self, task_depchanged):
        def py_callable(targets, dependencies, changed, task):
            targets.append('new_target')
            dependencies.append('new_dependency')
            changed.append('new_changed')
        my_action = action.PythonAction(py_callable, task=task_depchanged)
        my_action.execute()

        assert task_depchanged.file_dep == ['dependencies', 'new_dependency']

        assert task_depchanged.targets == ['targets', 'new_target']

        assert task_depchanged.dep_changed == ['changed', 'new_changed']


##############


class TestCreateAction(object):
    class TaskStub(object):
        name = 'stub'
    mytask = TaskStub()

    def testBaseAction(self):
        class Sample(action.BaseAction): pass
        my_action = action.create_action(Sample(), self.mytask, 'actions')
        assert isinstance(my_action, Sample)
        assert self.mytask == my_action.task

    def testStringAction(self):
        my_action = action.create_action("xpto 14 7", self.mytask, 'actions')
        assert isinstance(my_action, action.CmdAction)
        assert my_action.shell == True

    def testListStringAction(self):
        my_action = action.create_action(["xpto", 14, 7], self.mytask, 'actions')
        assert isinstance(my_action, action.CmdAction)
        assert my_action.shell == False

    def testMethodAction(self):
        def dumb(): return
        my_action = action.create_action(dumb, self.mytask, 'actions')
        assert isinstance(my_action, action.PythonAction)

    def testTupleAction(self):
        def dumb(): return
        my_action = action.create_action((dumb,[1,2],{'a':5}), self.mytask,
                                         'actions')
        assert isinstance(my_action, action.PythonAction)

    def testTupleActionMoreThanThreeElements(self):
        def dumb(): return
        expected = "Task 'stub': invalid 'actions' tuple length"
        with pytest.raises(action.InvalidTask, match=expected):
            action.create_action((dumb,[1,2],{'a':5},'oo'), self.mytask,
                                 'actions')

    def testInvalidActionNone(self):
        expected = "Task 'stub': invalid 'actions' type. got: None"
        with pytest.raises(action.InvalidTask, match=expected):
            action.create_action(None, self.mytask, 'actions')

    def testInvalidActionObject(self):
        expected = "Task 'stub': invalid 'actions' type. got: <"
        with pytest.raises(action.InvalidTask, match=expected):
            action.create_action(self, self.mytask, 'actions')

    def test_invalid_action_task_param_name(self):
        expected = "Task 'stub': invalid 'clean' type. got: True"
        with pytest.raises(action.InvalidTask, match=expected):
            action.create_action(True, self.mytask, 'clean')
