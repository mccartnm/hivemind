

class _Subscription(object):
    """
    The low level unit for subscribing to a service
    """
    def __init__(self, node, filter_, function):
        self._node = node
        self._filter = filter_
        self._function = function


    @property
    def node(self):
        return self._node


    @property
    def filter(self):
        return self._filter


    @property
    def function(self):
        return self._function
