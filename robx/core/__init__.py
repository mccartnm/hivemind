# """
# Rough out of a comm chain between different nodes

# A (~series of) _Service(s) can be started by a _Node which are run in
# tandem of multiple threads of a process. This requires a decent understanding
# of locks for data saftey when using multiple _but_ the idea is that we have
# the services on different threads while the main thread, once initialized,
# starts its web server that waits for anything it's subscribed to in order to
# relay/store that information for it's own services. 


# The RootController is where we relay messages between services and subscriptions
# as well as control the larger dataset that all nodes can access.
# """

# import os
# import sys
# import time
# import logging
# import threading

# if __name__ == '__main__':
#     sys.path.append(os.path.abspath(
#         os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
#     ))

from . import log

# All robx primitives
from .root import RootController
from .node import _Node
from .service import _Service
from .subscription import _Subscription
