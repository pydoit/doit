"""Logger with channel support."""

import StringIO

class Logger(object):
    """A simple logger with channels.

    @ivar channel: (dict) key: channel name. value: StringIO with logged
    messages.
    """

    def __init__(self):
        """Init."""
        self.channel = {}

    def __del__(self):
        """Close StringIO's."""
        for c in self.channel.itervalues():
            c.close()

    def log(self,channel,text):
        """Log text in channel.

        If channel does not exist a new channel is created.
        @param channel: (string) channel name.
        @param text: (string) text to be logged.
        """
        # create channel if new channel
        if channel not in self.channel:
            self.channel[channel] = StringIO.StringIO()
        self.channel[channel].write(text)


    def clear(self,channel):
        """Clear all logged messages from channel.

        Do nothing (raise nothing) if channel doesnt exist.
        @param channel: (string) channel name.
        """
        if channel in self.channel:
            # delete and create a new one
            self.channel[channel].close()
            self.channel[channel] = StringIO.StringIO()


    def flush(self,channel,stream):
        """write logged content from channel to 'stream' and clear log.

        Do nothing (raise nothing) if channel doesnt exist.
        @param channel: (string) channel name.
        @param stream: anything that implements a 'write' method.
        """
        if channel in self.channel:
            stream.write(self.channel[channel].getvalue())
            self.clear(channel)


#: default unamed global logger
_theLogger = Logger()

# is this user friendly or stupid?
def log(channel,text):
    """L{Logger.log} shortcut for global logger."""
    _theLogger.log(channel,text)

def clear(channel):
    """L{Logger.clear} shortcut for global logger."""
    _theLogger.clear(channel)

def flush(channel,stream):
    """L{Logger.clear} shortcut for global logger."""
    _theLogger.flush(channel,stream)
