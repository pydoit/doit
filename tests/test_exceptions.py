from doit import exceptions


class TestCatchedException(object):
    def test_name(self):
        class XYZ(exceptions.CatchedException):
            pass
        my_excp = XYZ("hello")
        assert 'XYZ' == my_excp.get_name()
        assert 'XYZ' in str(my_excp)
        assert 'XYZ' in repr(my_excp)

    def test_msg_notraceback(self):
        my_excp = exceptions.CatchedException('got you')
        msg = my_excp.get_msg()
        assert 'got you' in msg

    def test_exception(self):
        try:
            raise IndexError('too big')
        except Exception, e:
            my_excp = exceptions.CatchedException('got this', e)
        msg = my_excp.get_msg()
        assert 'got this' in msg
        assert 'too big' in msg
        assert 'IndexError' in msg

    def test_catched(self):
        try:
            raise IndexError('too big')
        except Exception, e:
            my_excp = exceptions.CatchedException('got this', e)
        my_excp2 = exceptions.CatchedException('handle that', my_excp)
        msg = my_excp2.get_msg()
        assert 'handle that' in msg
        assert 'got this' not in msg # could be there too...
        assert 'too big' in msg
        assert 'IndexError' in msg


class TestAllCatched(object):
    def test(self):
        assert issubclass(exceptions.TaskFailed, exceptions.CatchedException)
        assert issubclass(exceptions.TaskError, exceptions.CatchedException)
        assert issubclass(exceptions.SetupError, exceptions.CatchedException)
        assert issubclass(exceptions.DependencyError,
                          exceptions.CatchedException)
