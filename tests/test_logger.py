import StringIO

from doit import logger

msg = []
for i in range(1,4):
    msg.append("message %d\n"%i)

class TestLogger:

    def setUp(self):
        # make sure we have a brand new logger for each test
        logger._theLogger = logger.Logger()

    # log messages are saved to any channel without expliciting creating them.
    def test_log(self):        
        logger.log("channel1", msg[0])
        logger.log("channel2", msg[1])
        logger.log("channel1", msg[2])
        assert msg[0]+msg[2] == logger._theLogger.channel['channel1'].getvalue()
        assert msg[1] == logger._theLogger.channel['channel2'].getvalue()


    def test_clear(self):
        logger.log("channel1", msg[0])
        logger.clear("channel1")
        logger.log("channel1", msg[1])
        assert msg[1] == logger._theLogger.channel['channel1'].getvalue()
        
    # clearing an inexistent channel does nothing
    def test_clear_inexistent(self):
        logger.clear("channelX")


    def test_flush(self):
        logger.log("channel1", msg[0])
        logger.log("channel1", msg[1])
        out = StringIO.StringIO()
        logger.flush("channel1",out)
        assert msg[0]+msg[1] == out.getvalue()

    # when a flush is performed the log is cleared.
    def test_flush_clear(self):
        
        logger.log("channel1", msg[0])
        logger.flush("channel1",StringIO.StringIO())

        logger.log("channel1", msg[1])
        out = StringIO.StringIO()
        logger.flush("channel1",out)
        assert msg[1] == out.getvalue()

    
    # flushing an inexistent channel does nothing
    def test_flush_inexistent(self):
        logger.flush("channelX",StringIO.StringIO())
