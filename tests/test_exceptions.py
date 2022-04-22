from doit import exceptions


class TestInvalidCommand(object):
    def test_just_string(self):
        exception = exceptions.InvalidCommand('whatever string')
        assert 'whatever string' == str(exception)

    def test_task_not_found(self):
        exception = exceptions.InvalidCommand(not_found='my_task')
        exception.cmd_used = 'build'
        assert 'command `build` invalid parameter: "my_task".' in str(exception)

    def test_param_not_found(self):
        exception = exceptions.InvalidCommand(not_found='my_task')
        exception.cmd_used = None
        want = 'Invalid parameter: "my_task". Must be a command,'
        assert want in str(exception)
        assert 'Type "doit help" to see' in str(exception)

    def test_custom_binary_name(self):
        exception = exceptions.InvalidCommand(not_found='my_task')
        exception.cmd_used = None
        exception.bin_name = 'my_tool'
        assert 'Type "my_tool help" to see ' in str(exception)



class TestBaseFail(object):
    def test_name(self):
        class XYZ(exceptions.BaseFail):
            pass
        my_excp = XYZ("hello")
        assert 'XYZ' == my_excp.get_name()
        assert 'XYZ' in str(my_excp)
        assert 'XYZ' in repr(my_excp)

    def test_msg_notraceback(self):
        my_excp = exceptions.BaseFail('got you')
        msg = my_excp.get_msg()
        assert 'got you' in msg

    def test_exception(self):
        try:
            raise IndexError('too big')
        except Exception as e:
            my_excp = exceptions.BaseFail('got this', e)
        msg = my_excp.get_msg()
        assert 'got this' in msg
        assert 'too big' in msg
        assert 'IndexError' in msg

    def test_caught(self):
        try:
            raise IndexError('too big')
        except Exception as e:
            my_excp = exceptions.BaseFail('got this', e)
        my_excp2 = exceptions.BaseFail('handle that', my_excp)
        msg = my_excp2.get_msg()
        assert 'handle that' in msg
        assert 'got this' not in msg # could be there too...
        assert 'too big' in msg
        assert 'IndexError' in msg


class TestAllCaught(object):
    def test(self):
        assert issubclass(exceptions.TaskFailed, exceptions.BaseFail)
        assert issubclass(exceptions.TaskError, exceptions.BaseFail)
        assert issubclass(exceptions.SetupError, exceptions.BaseFail)
        assert issubclass(exceptions.DependencyError, exceptions.BaseFail)
