"""Counter synchronization"""
import gevent
import gevent.event

class Counter:
    """Create a counter with an initial value. If not specified, the
    value defaults to 0.
    """
    def __init__(self, value=0):
        self.value = value
        self._event = gevent.event.Event()

    def set(self, value=None):
        """Set the counter to a value. If not specified, the
        internal counter will be incremented by 1.
        """
        if value is None:
            self.value += 1
        else:
            self.value = value
        self._event.set()
        self._event.clear()

    def wait(self, value=None, timeout=None):
        """Wait until the counter becomes greater than a value, and
        return the current value of the counter. If the value is not
        specified, the current value of the counter is returned
        immediately.
        """
        if value is not None:
            with gevent.Timeout(timeout):
                while self.value <= value:
                    self._event.wait()
        return self.value
