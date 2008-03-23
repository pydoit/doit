import StringIO

class Logger(object):
    """A very simple logger with channel support"""

    def __init__(self):
        # key: channel name. value: StringIO with logged messages
        self.channel = {}

    def __del__(self):
        # close StringIO's
        for c in self.channel.itervalues():
            c.close()

    def log(self,channel,text):
        """log text in channel"""

        # create channel if new channel
        if channel not in self.channel:
            self.channel[channel] = StringIO.StringIO()
        # write
        self.channel[channel].write(text)


    def clear(self,channel):
        """clear all logged messages from channel

        do nothing (raise nothing) if channel doesnt exist.
        """
        if channel in self.channel:
            # delete and create a new one
            self.channel[channel].close()
            self.channel[channel] = StringIO.StringIO()


    def flush(self,channel,stream):
        """write logged content from channel to 'stream' and clear log.

        do nothing (raise nothing) if channel doesnt exist.
        @param stream anything that implements a 'write' method"""
        if channel in self.channel:
            stream.write(self.channel[channel].getvalue())
            self.clear(channel)

# default unamed logger 
_theLogger = Logger()

# is this user friendly or stupid?
def log(channel,text):
    _theLogger.log(channel,text)

def clear(channel):
    _theLogger.clear(channel)

def flush(channel,stream):
    _theLogger.flush(channel,stream)
