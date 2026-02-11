import unittest

from doit import exceptions


class TestInvalidCommand(unittest.TestCase):
    def test_just_string(self):
        exception = exceptions.InvalidCommand('whatever string')
        self.assertEqual('whatever string', str(exception))

    def test_task_not_found(self):
        exception = exceptions.InvalidCommand(not_found='my_task')
        exception.cmd_used = 'build'
        self.assertIn('command `build` invalid parameter: "my_task".', str(exception))

    def test_param_not_found(self):
        exception = exceptions.InvalidCommand(not_found='my_task')
        exception.cmd_used = None
        want = 'Invalid parameter: "my_task". Must be a command,'
        self.assertIn(want, str(exception))
        self.assertIn('Type "doit help" to see', str(exception))

    def test_custom_binary_name(self):
        exception = exceptions.InvalidCommand(not_found='my_task')
        exception.cmd_used = None
        exception.bin_name = 'my_tool'
        self.assertIn('Type "my_tool help" to see ', str(exception))


class TestBaseFail(unittest.TestCase):
    def test_name(self):
        class XYZ(exceptions.BaseFail):
            pass
        my_excp = XYZ("hello")
        self.assertEqual('XYZ', my_excp.get_name())
        self.assertIn('XYZ', str(my_excp))
        self.assertIn('XYZ', repr(my_excp))

    def test_msg_notraceback(self):
        my_excp = exceptions.BaseFail('got you')
        msg = my_excp.get_msg()
        self.assertIn('got you', msg)

    def test_exception(self):
        try:
            raise IndexError('too big')
        except Exception as e:
            my_excp = exceptions.BaseFail('got this', e)
        msg = my_excp.get_msg()
        self.assertIn('got this', msg)
        self.assertIn('too big', msg)
        self.assertIn('IndexError', msg)

    def test_caught(self):
        try:
            raise IndexError('too big')
        except Exception as e:
            my_excp = exceptions.BaseFail('got this', e)
        my_excp2 = exceptions.BaseFail('handle that', my_excp)
        msg = my_excp2.get_msg()
        self.assertIn('handle that', msg)
        self.assertNotIn('got this', msg)  # could be there too...
        self.assertIn('too big', msg)
        self.assertIn('IndexError', msg)


class TestAllCaught(unittest.TestCase):
    def test(self):
        self.assertTrue(issubclass(exceptions.TaskFailed, exceptions.BaseFail))
        self.assertTrue(issubclass(exceptions.TaskError, exceptions.BaseFail))
        self.assertTrue(issubclass(exceptions.SetupError, exceptions.BaseFail))
        self.assertTrue(issubclass(exceptions.DependencyError, exceptions.BaseFail))
