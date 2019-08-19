
import uuid
import logging
import traceback

from http.server import ThreadingHTTPServer

from . import log
from .base import _RobXObject, _HandlerBase
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


class _Node(_RobXObject):
    """
    Virtual class that requires overloading to have any real
    funcionality.

    Object that can communicate with other nodes via basic protocols
    after registering with the RootController anything it hosts.
    """

    def __init__(self, name=None):
        _RobXObject.__init__(self)

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

    # -- Overloaded from _RobXObject

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

    # -- Public Methods

    def add_service(self, service_name, function):
        """
        Generates a _Service with the given name. This will
        initialize the thread that the service "lives" on
        and begin it's functionality.
        """
        service = _Service(
            self, service_name, function
        )
        with self.lock:
            self._services.append(service)
            service.run() # _RobXObject
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
