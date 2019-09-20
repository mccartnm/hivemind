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

import uuid
import logging
import traceback

from http.server import ThreadingHTTPServer

from . import log
from .base import _HivemindAbstractObject, _HandlerBase
from .root import RootController
from .service import _Service
from .subscription import _Subscription


class NodeSubscriptionHandler(_HandlerBase):
    """
    Handler for communications back and forth from the RootController
    to the various subscriptions we have. This is lightweight and
    rather loose to keep the flexibility at an all time high.
    """
    def do_POST(self):
        """
        The POST operation for a node subscription
        """
        self._set_headers()

        if not hasattr(self, 'endpoints'):
            return None # Nothing to do...

        if isinstance(self.data, _HandlerBase.Error):
            # This is an errored response from our root. We need
            # to abort now
            return None

        # TODO!
        # if self.path == '/shutdown':
        #     self._node.shutdown()

        for endpoint, subscription in self.endpoints.items():
            if self.path == endpoint:
                # Fire op that subscription function
                subscription.function(self.data)


class _Node(_HivemindAbstractObject):
    """
    Virtual class that requires overloading to have any real
    funcionality.

    Object that can communicate with other nodes via basic protocols
    after registering with the RootController anything it hosts.
    """

    def __init__(self, name=None):
        _HivemindAbstractObject.__init__(self)

        # The name of this node
        self._name = name or uuid.uuid4()

        # The port assigned by the root node
        self._port = None

        # Activation achieved through the master node
        self._enabled = False

        # Known _Service objects attached to this node
        self._services = []

        # Known _Subscription objects attached to this node
        self._subscriptions = []

        self.services()
        self.subscriptions()
        self.data_tables()


    @property
    def name(self):
        return self._name


    @property
    def port(self):
        return self._port


    @classmethod
    def exec_(cls, name=None, logging=None):
        log.start(logging is not None)
        instance = cls(name)
        instance.run()
        return instance

    # -- Overloaded from _HivemindAbstractObject

    def run(self):
        """
        Boot up the registered services and subscriptions.
        """
        try:
            # The first thing we do is register the node with our
            # root object. It goes into a pending completion state
            # until actually online
            result = RootController.register_node(self)
            if result:
                self._port = result['result'] # TODO: Clean this up

            for service in self._services:
                RootController.register_service(service)

            #
            # We generate a duplicate of the handler class in the event that
            # multiple nodes are being serviced on the same process (future).
            # This lets us generate a custom set of paths to handle at the
            # class level without compromising the original class
            #
            self._handler_class = type(
                f'NodeSubscriptionHandler_{self.name}',
                NodeSubscriptionHandler.__bases__,
                dict(NodeSubscriptionHandler.__dict__)
            )

            # Create independently to avoid reference mixup
            self._handler_class.endpoints = {}

            for subscription in self._subscriptions:
                #
                # For each subscription, we add their endpoints to
                # our soon-to-be server
                #
                self._handler_class.endpoints[
                    subscription.endpoint
                ] = subscription
                RootController.register_subscription(subscription)

            for data_table in self._data_tables:

                self._handler_class.endpoints[
                    data_table.endpoint
                ] = subscription
                RootController.register_data_table(data_table)

            RootController.enable_node(self)
            self._set_enabled()
            self._serve()
            return

        except KeyboardInterrupt as err:
            RootController.deregister_node(self)
            self.shutdown()
            return

        except Exception as e:
            logging.critical("Issue with executing node.")
            list(map(logging.critical,
                     traceback.format_exc().split('\n')))
            self.shutdown()
            return

    # -- Virtual Interface

    def services(self):
        """ Register any default services here """
        return


    def subscriptions(self):
        """ Register any default subscriptions here """
        return


    def data_tables(self):
        """ Register and default data tables for this now """
        return

    # -- Public Methods

    def add_service(self, name, function):
        """
        Generates a _Service with the given name. This will
        initialize the thread that the service "lives" on
        and begin it's functionality.
        """
        service = _Service(
            self, name, function
        )
        with self.lock:
            self._services.append(service)
            service.run() # _HivemindAbstractObject
        return service


    def add_subscription(self, subscription_filter, function, name=None):
        """
        Generates a _Subscription with the given name. This becomes
        an enpoint on our local server 
        """
        subscription = _Subscription(
            self, subscription_filter, function, name=name
        )
        with self.lock:
            self._subscriptions.append(subscription)
        return subscription


    def add_data_table(self, table_class):
        """
        Add an object to the data layer for persistent data control
        """
        endpoint = _Endpoint(self, table_class)
        with self.lock:
            self._endpoints.append(endpoint)
        return endpoint


    def query(self, filters, callback):
        """
        Ask our RootController database for some information.

        Everything we do has to be async. That's vital. So - make
        sure we have some form of callback system.
        """
        RootController.submit_query(filters, callback)


    def shutdown(self):
        for service in self._services:
            service.shutdown()

    def is_running(self):
        with self.lock:
            return self._enabled

    # -- Private Methods


    def _set_enabled(self):
        """
        Enable the node, alert the services that we're up and running
        """
        with self.lock:
            self._enabled = True

            for service in self._services:
                service.alert()


    def _serve(self):
        """
        Here's where the main node thread starts up and runs whatever
        functionality is required.
        """

        logging.debug(f"Node subscription set: {self._port}")
        server_adress = ('', self._port)
        httpd = ThreadingHTTPServer(
            server_adress, self._handler_class
        )
        httpd.serve_forever()
