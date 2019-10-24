"""
Copyright (c) 2019 Michael McCartney, Kevin McLoughlin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import logging
import threading

from .base import _HivemindAbstractObject
from .root import RootController

class _Service(_HivemindAbstractObject):
    """
    Service object that can ship messages over a select command
    channel
    """
    def __init__(self, node, name, function):
        _HivemindAbstractObject.__init__(self, logger=node._logger)
        self._node = node
        self._name = name
        self._function = function

        self._condition = threading.Condition(self.lock)
        self._thread = None # \see run()
        self._abort = False

    def __repr__(self):
        return f'<{self.__class__.__name__}({self._name})>'

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
        self.log_info(f"Aborting {self.name}...")
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

            result = func(self) # Fire!
            if result is None:
                result = 0

            if result > 0:
                self.abort() # What happens here
                break


    def run(self):
        """
        Overloaded from _HivemindAbstractObject
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
