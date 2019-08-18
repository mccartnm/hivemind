"""

"""

import logging
import requests
from http.server import ThreadingHTTPServer

from robx.core.base import _RobXObject, _HandlerBase


class RootServiceHandler(_HandlerBase):
    """
    Web handler for the services in order to route the
    data through properly.
    """
    def do_POST(self):
        """
        When we POST, if we're registering data we handle that accordingly.

        Otherwise we have the controller ship out the message to any listening
        services
        """
        self._set_headers()
        if self.path == '/register/node':
            port = self.controller._register_node(self.data)
            self.write_to_response({ 'result' : port })

        elif self.path == '/register/service':
            self.controller._register_service(self.data)
            self.write_to_response({ 'result' : True })

        elif self.path == '/register/subscription':
            self.controller._register_subscription(self.data)
            self.write_to_response({ 'result' : True })

        elif self.path == '/core/heartbeat':
            self.write_to_response({'result' : True})

        else:
            passback = self.controller._delegate(self.path, self.data)
            self.write_to_response(passback)
        # return '<none>'

    def do_GET(self):
        self._set_headers()
        self.write_to_response({'result' : True})


class RootController(_RobXObject):
    """
    Basic impl of subscription service handler
    """
    default_port = 9476

    #
    # The node states that determine how we handle them.
    #
    NODE_PENDING = 'pending'
    NODE_ONLINE  = 'online'
    NODE_TERM    = 'terminate'


    class NodeProxy(object):
        """
        Proxy object that contains the status of a given node as well as
        the port it resides on. This provides us the port location of a
        node for URL building as well. In the long run, we can probably
        look into also including the IP for cross machine processes
        """
        def __init__(self, name, status=None, port=None):
            self._name = name
            self._status = status
            self._port = port


        def __eq__(self, other):
            return self._name == other._name


        def __hash__(self):
            return hash(self._name)


    def __init__(self, **kwargs):
        _RobXObject.__init__(self)

        self._port_count = 0

        # Known nodes out in the ecosystem
        self._nodes = set()

        # Known services actively running
        self._services = {}

        # Requested subscriptions
        self._subscriptions = {}


    @classmethod
    def _register_post(cls, type_, json_data):
        """
        Utility for running a POST at the controller service
        """
        result = requests.post(
            f'http://127.0.0.1:{cls.default_port}/register/{type_}',
            json=json_data
        )
        result.raise_for_status()
        return result.json() # Should be the port

    # -- Registration Methods (Called from the _Node classes)

    @classmethod
    def register_node(cls, node):
        """
        Add the node to our root (if not already there). If it is,
        we simply ignore the request.
        """
        return cls._register_post('node', {
            'name' : node.name,
            'status': cls.NODE_PENDING
        })


    @classmethod
    def deregister_node(cls, node):
        """
        Dismantel a node
        """
        return cls._register_post('node', {
            'name'  : node.name,
            'status': cls.NODE_TERM
        })


    @classmethod
    def enable_node(cls, node):
        """
        Enable the node
        """
        return cls._register_post('node', {
            'name' : node.name,
            'status': cls.NODE_ONLINE
        })


    @classmethod
    def register_service(cls, service):
        """
        :param service: The _Service instance that contains the required
        info.
        """
        return cls._register_post('service', {
            'node' : service.node.name,
            'name' : service.name,
        })


    @classmethod
    def register_subscription(cls, subscription):
        """
        :param service: The _Subscription instance that contains the required
        info.
        """
        return cls._register_post('subscription', {
            'node' : service.node.name,
            'name' : subscription.name,
            'endpoint' : service.endpoint
        })

    @staticmethod
    def exec_():
        """
        Generic call used by most entry scripts to start the root without
        having to create a custom local instance
        """
        controller = RootController()
        controller.run()
        return controller

    # -- Overloaded

    def run(self):
        """
        Our run operation is built to handle the various incoming
        requests and respond to the required items in time.
        """
        self._server = None
        try:
            self._handler_class = RootServiceHandler
            self._handler_class.controller = self # Reverse pointer

            self._server = ThreadingHTTPServer(
                ('', self.default_port), self._handler_class
            )

            logging.info(f"Serving on {self.default_port}...")

            # Just keep serving
            self._server.serve_forever()

        except KeyboardInterrupt as err:
            self._server.shutdown()
            return

    # -- Private Interface (reserved for running instance)

    def _register_node(self, payload):
        """
        Register a node with our setup
        """
        assert \
            isinstance(payload, dict), \
            'Registration payload must be a dict'
        assert \
            all(k in payload for k in ('name', 'status')), \
            'Registration payload missing name or status'

        test = self.NodeProxy(payload['name'])
        if payload['status'] != self.NODE_TERM:
            logging.info(f"Register Node: {payload['name']}")
        else:
            logging.info(f"Deregister Node: {payload['name']}")

        with self.lock:
            if test not in self._nodes:

                if payload['status'] == self.NODE_TERM:
                    # We're removing the node. Shouldn't be
                    # here
                    return 0

                self._port_count += 1
                port = self.default_port + self._port_count
                proxy = self.NodeProxy(
                    name=payload['name'],
                    status=payload['status'],
                    port=port
                )

                self._nodes.add(proxy)
                return port

            else:
                destroy = None

                # We've seen this node before (at least - we should
                # have)
                for proxy in self._nodes:
                    if proxy._name == payload['name']:

                        if payload['status'] == self.NODE_TERM:
                            # Clean up this node
                            destroy = proxy
                            break

                        proxy._status = payload['status']
                        return proxy._port

                if destroy:
                    self._remove_node(destroy)
                    return 0


    def _remove_node(self, proxy):
        """
        Terminate all connections with a node. Because we base everything
        off the proxy, this becomes doable without too much headache.
        """
        with self.lock: # reentrant
            self._nodes.remove(proxy)

            if proxy in self._services:
                self._services.pop(proxy)

            if proxy in self._subscriptions:
                self._services.pop(proxy)


    def _register_service(self, payload):
        """
        Register a service
        """
        assert isinstance(payload, dict), \
            'Service Registration payload must be a dict'

        assert all(k in payload for k in ('node', 'name')), \
            'Service Registration payload missing "node" or "name"'

        logging.info(f"Register Service: {payload['name']} to {payload['node']}")

        proxy = self.NodeProxy(payload['node']) # We just need the hash

        with self.lock:

            assert proxy in self._nodes, f'Node {payload["node"]} not found'
            known_services = self._services.setdefault(proxy, {})

            assert \
                payload['name'] not in known_services, \
                f'The service {payload["name"]} already exists for {payload["node"]}'
            known_services[payload['name']] = payload

        return 0


    def _register_subscription(self, payload):
        """
        Register a subscription
        """
        assert \
            isinstance(payload, dict), \
            'Subscription Registration payload must be a dict'
        assert \
            all(k in payload for k in ('node', 'filter')), \
            'Subscription Registration payload missing "node" or "filter"'

        proxy = self.NodeProxy(payload['node'])

        with self.lock:
            assert proxy in self._nodes, f'Node {payload["node"]} not found'
            known_subscriptions = self._subscriptions.setdefault(proxy, {})
            known_subscriptions.setdefault(payload['name'], []).append(payload)


    def _delegate(self, path, payload):
        """
        Based on the path, we have to handle our work accordingly.
        """
        pass
