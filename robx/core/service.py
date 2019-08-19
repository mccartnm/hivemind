
import logging
import threading

from .base import _RobXObject
from .root import RootController

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
        """ The _Node instance that onws this Service """
        return self._node


    @property
    def name(self):
        """ The name of the service """
        return self._name


    @property
    def function(self):
        """ The executable that we run with our service """
        return self._function


    def sleep_for(self, timeout):
        """
        Conditionaly sleep the service thread. Will eject if
        abort is called.

        :param timeout: The sleep time (float in seconds
        or part thereof)
        :return: Boolean - False if abort() was called while waiting
        """
        with self._condition:
             self._condition.wait(timeout)

        ab = False
        with self.lock:
            ab = self._abort
        return (not ab)


    def send(self, payload):
        """
        When the service wants to transmit data to any subscribers,
        we use this to pass along the information
        """
        RootController.send_to_controller(self, payload)


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
                self.abort() # What happens here
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
