
import uuid

class _Subscription(object):
    """
    The low level unit for subscribing to a service
    """
    def __init__(self, node, filter_, function, name=None):
        self._node = node
        self._filter = filter_
        self._function = function
        self._name = name or uuid.uuid4()

    @property
    def node(self):
        return self._node


    @property
    def filter(self):
        return self._filter


    @property
    def function(self):
        return self._function


    @property
    def endpoint(self):
        return f'/sub/{self.node.name}/{self._name}'
 