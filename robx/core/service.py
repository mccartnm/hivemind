
import logging
import threading

from .base import _RobXObject

class _Service(_RobXObject):
    """
    Service object that can ship messages over a select command
    channel
    """
    def __init__(self, node, name, function):
        _RobXObject.__init__(self)
        self._node = node
        self._name = name
        self._function = function

        self._condition = threading.Condition(self.lock)
        self._thread = None # \see run()
        self._abort = False

    @property
    def node(self):
        return self._node


    @property
    def name(self):
        return self._name


    @property
    def function(self):
        return self._function


    def abort(self):
        logging.info(f"Aborting {self.name}...")
        with self.lock:
            self._abort = True


    def shutdown(self):
        self.abort()
        with self._condition:
            self._condition.notify_all()


    def alert(self):
        """
        When we have a change on the service we need to know about
        it.
        """
        with self._condition:
            self._condition.notify_all()


    def _node_not_started(self):
        return (not self._node.is_running())


    def _internal_execute(self, func):
        """
        The _Service controls the execution loop of our
        function.
        """
        with self._condition:
            while (not self._abort) and self._node_not_started():
                self._condition.wait()

        while True:
            with self.lock:
                if self._abort:
                    break # Service is terminating

            result = func() # Fire!
            if result > 0:
                self.abort()
                break


    def run(self):
        """
        Overloaded from _RobXObject
        Begin a thread that will control the runtime of our
        service.

        :return: None
        """
        with self.lock:
            self._abort = False
            self._thread = threading.Thread(
                target=self._internal_execute,
                name=self.name,
                args = (self._function,)
            )
            self._thread.start()
