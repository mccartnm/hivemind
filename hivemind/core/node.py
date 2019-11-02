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

from . import log
from .base import _HivemindAbstractObject, _HandlerBase
from .root import RootController
from .service import _Service
from .subscription import _Subscription

import asyncio
from aiohttp import web

from ..util.misc import BasicRegistry

class NodeSubscriptionHandler(_HandlerBase):
    """
    Handler for communications back and forth from the RootController
    to the various subscriptions we have. This is lightweight and
    rather loose to keep the flexibility at an all time high.
    """
    async def node_post(self, request):
        """
        The POST operation for a node subscription
        """
        data = await request.json()
        path = '/' + request.match_info['fullpath']

        if not hasattr(self, 'endpoints'):
            return web.json_response(None) # Nothing to do...

        if isinstance(data, _HandlerBase.Error):
            # This is an errored response from our root. We need
            # to abort now
            return web.json_response(None) # Nothing to do...

        for endpoint, callback in self.endpoints.items():
            if path == endpoint:
                # Fire up the execution function
                callback.function(data)

        return web.json_response(None)


class _Node(_HivemindAbstractObject, metaclass=BasicRegistry):
    """
    Virtual class that requires overloading to have any real
    funcionality.

    Object that can communicate with other nodes via basic protocols
    after registering with the RootController anything it hosts.
    """
    def __init__(self, name=None, **kwargs):
        _HivemindAbstractObject.__init__(
            self,
            logger=kwargs.get('logger', None)
        )

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

        self._registered = False

        # The web server
        self._app = None

        self._abort_condition = kwargs.get('abort_condition', None)
        self._abort_event = kwargs.get('abort_event', None)

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

    # -- Overloaded from _HivemindAbstractObject

    def run(self, loop=None):
        """
        Boot up the registered services and subscriptions.
        """
        try:
            if not loop:
                loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # The first thing we do is register the node with our
            # root object. It goes into a pending completion state
            # until actually online
            result = RootController.register_node(self)
            if result:
                self._port = result['result'] # TODO: Clean this up
                self._registered = True

            for service in self._services:
                RootController.register_service(service)

            #
            # We generate a duplicate of the handler class in the event that
            # multiple nodes are being serviced on the same process (future).
            # This lets us generate a custom set of paths to handle at the
            # class level without compromising the original class
            #
            # Wth aiohttp, we may not need this any longer because we can
            # attach endpoints to the specific instance of the handler class
            #
            self._handler_class = type(
                f'NodeSubscriptionHandler_{self.name}',
                NodeSubscriptionHandler.__bases__,
                dict(NodeSubscriptionHandler.__dict__)
            )

            # Create independently to avoid reference mixup
            self._handler_class.endpoints = {}

            # Route our logging facilities per-node for when the handler
            # recieves some form of log request
            node_ = self
            self._handler_class._log_function = \
                lambda _, x, node_=node_: node_._log('debug', x)

            for subscription in self._subscriptions:    
                #
                # For each subscription, we add their endpoints to
                # our soon-to-be server
                #
                self._handler_class.endpoints[
                    subscription.endpoint
                ] = subscription
                RootController.register_subscription(subscription)

            self.additional_registration(self._handler_class)

            RootController.enable_node(self)
            self._set_enabled()

            self._serve(loop)

        except Exception as err:
            if not isinstance(err, KeyboardInterrupt):
                import traceback
                self.log_critical(traceback.format_exc())
                print (traceback.format_exc())

        finally:
            self.shutdown()

            if self._abort_event:
                self._abort_event.set()
            return

    # -- Virtual Interface

    def services(self):
        """ Register any default services here """
        return


    def subscriptions(self):
        """ Register any default subscriptions here """
        return


    def additional_registration(self, handler_class) -> None:
        """
        This is called before we start the internal node server and after
        initial services/subscriptions have been registered.
        
        Overload this to accomidate additional functionality with the
        RootController.

        :param handler_class: NodeSubscriptionHandler class
        :return: None
        """
        return


    def metadata(self) -> dict:
        """
        Optional, use to include additional metadata for this node to
        aid in querying or otherwise.

        :return: dict[str:str]
        """
        return {}


    @classmethod
    def mark_abstract(cls, node_class):
        """
        Mark a particular node class as abstract
        """
        if node_class in cls._registry:
            cls._registry.remove(node_class)


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

        if self._registered:
            self.on_shutdown()
            RootController.deregister_node(self)


    def on_shutdown(self):
        """
        Overload where needed to shut down any additional parts of the
        nodes that are running.

        This is called _before_ we deregister from the root
        """
        pass


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


    def _serve(self, loop):
        """
        Here's where the main node thread starts up and runs whatever
        functionality is required.
        """
        self.log_debug(f"Node subscription set: {self._port}")

        self._handler_instance = self._handler_class()
        self._app = web.Application(loop=loop)

        self._app.add_routes([
            web.post('/{fullpath:.*}', self._handler_instance.node_post)
        ])

        web.run_app(
            self._app,
            port=self._port,
            handle_signals=False,
            access_log=self.logger,
            abort_condition=self._abort_condition,
            print=self.log_info,
            # reuse_port=True # ??
        )

    # -- Web API utils

    @classmethod
    def wapi_query_for_nodes(cls, controller, querydict):
        """
        :return: ``list[NodeRegister]`` for all nodes matching the filters
        """
        # TODO: Actually build the filters...

        from hivemind.data.tables import NodeRegister
        return controller.database.new_query(NodeRegister).objects()


    @classmethod
    def wapi_lookup_for_basic_info(cls, controller, querydict):
        """
        Lookup function to provide context for rendering different elements
        """
        nodes = cls.wapi_query_for_nodes(controller, querydict)

        output = []
        for node in nodes:
            output.append({
                'id' : node.id,
                'ip' : node.ip if hasattr(node, 'ip') else '0.0.0.0',
                'node' : node,
                'name' : node.name,
                'infos' : [
                    { 'status' : 'Online' if node.status == 'online' else 'Offline'}
                ],
                'service_count' : controller.service_count(node),
                'sub_count' : controller.subscription_count(node),
                'url' : f'/nodes/{node.name}'
            })

        return output


# -- Web API (probably move?)

from hivemind.util._webtoolkit import API

# -- Basic Card And Chip Rendering
API.register_to_category('topics', 'node',
    {
        'title' : 'Nodes',
        'description' : 'Dive into active nodes and their current processes',
        'index_url' : '/nodes',
        'index_url_title' : 'Go To Nodes'
    },
    no_lookup = True
)


# -- Ability to generate node cards
API.register_to_category('nodes', 'node',
    {
        'table' : 'NodeRegister',
        'function' : _Node.wapi_lookup_for_basic_info
    }
)