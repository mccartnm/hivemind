"""
Rough out of a comm chain between different nodes

A (~series of) _Service(s) can be started by a _Node which are run in
tandem of multiple threads of a process. This requires a decent understanding
of locks for data saftey when using multiple _but_ the idea is that we have
the services on different threads while the main thread, once initialized,
starts its web server that waits for anything it's subscribed to in order to
relay/store that information for it's own services. 


The RootController is where we relay messages between services and subscriptions
as well as control the larger dataset that all nodes can access.
"""

import os
import sys
import time
import logging
import threading

if __name__ == '__main__':
    sys.path.append(os.path.abspath(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    ))

from robx.core import log
from robx.core.root import RootController
from robx.core.node import _Node


def proc_1(num=0):

    class SendTask(_Node):
        """ A simple service that ships out a message every few seconds """
        def services(self):
            self._my_service = self.add_service(
                'my-service',
                self._send_message
                # priority=0 # TODO
            )

        def _send_message(self):
            self._my_service.send('A Message For More!')
            # The service shouldn't spam. Only when data is required
            time.sleep(1)
            return 0

    a_task = SendTask(f'message_task_{num}')
    a_task.run()

def proc_2():

    class ReceiveTask(_Node):

        def subscriptions(self):
            self._my_subscription = self.add_subscription('my-service',
                                                          self._receive_message)

        def _receive_message(self, payload: str):
            if not isinstance(payload, str):
                return
            logging.info(payload)

    this_task = ReceiveTask('listen_task')
    this_task.run()

if __name__ == '__main__':
    log.start(verbose=True)

    if sys.argv[-1] == '1':
        proc_1()
    elif sys.argv[-1] == '2':
        proc_2()
    elif sys.argv[-1] == '3':
        proc_1(1)
    else:
        RootController.exec_()
