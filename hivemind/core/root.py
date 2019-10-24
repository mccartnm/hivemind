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

import os
import queue
import inspect
import logging
import fnmatch
import requests
import functools
import threading
import importlib
from itertools import islice


# -- For Queue Prio
from dataclasses import dataclass, field
from typing import Any

import asyncio
from aiohttp import web
import jinja2
import aiohttp_jinja2

from . import log
from .feature import _Feature
from .base import _HivemindAbstractObject, _HandlerBase
from .node_endpoints import RootNodeHandler
from hivemind.util import global_settings
from hivemind.util.misc import requests_retry_session
from hivemind.util import _webtoolkit

from hivemind.data.abstract.scafold import _DatabaseIntegration

# -- Bsaeic tables required by the system
from hivemind.data.tables import (
    TableDefinition, RequiredTables, NodeRegister, NodeMeta
)

# -- Populate known database mappings
from hivemind.data.contrib import interfaces


class RootServiceHandler(_HandlerBase):
    """
    Web handler for the services in order to route the
    data through properly.

    # TODO: Move this away from here
    """
    async def register_node(self, request):
        """ Register a _Node """
        data = await request.json()
        port = self.controller._register_node(data)
        return web.json_response({ 'result' : port })


    async def register_service(self, request):
        """ Register a _Service """
        data = await request.json()
        self.controller._register_service(data)
        return web.json_response({ 'result' : True })


    async def register_subscription(self, request):
        """ Register a _Subscription """
        data = await request.json()
        self.controller._register_subscription(data)
        return web.json_response({ 'result' : True })


    async def heartbeat(self, request):
        """ Basic alive test """
        return web.json_response({'result' : True})


    async def service_dispatch(self, request):
        """ Dispatch service command """
        path = request.match_info['tail']
        data = await request.json()
        passback = self.controller._delegate(path, data)
        return web.json_response(passback)


    async def index_post(self, request):
        # FIXME: Why do we need this?
        return web.json_response({'result': True})


    async def favicon(self, request):
        return web.FileResponse(
            global_settings['static_dirs'][0] + '/favicon.ico'
        )


    async def api(self, request):
        """
        Provided utility endpoint for abstract data gathering,
        content rendering, etc.
        """
        query = request.query
        path = request.match_info['api_path']
        return _webtoolkit.api_request(path, self.controller, query)


    @aiohttp_jinja2.template("hive_index.html")
    async def index(self, request):
        """
        The Landing page of the root controller
        """
        return self.controller.base_context()


@dataclass(order=True)
class PrioritizedDispatch:
    """
    Item used to identify the prio of arbitrary payload
    data from our services. Ripped from py docs.
    """
    priority: int
    name: Any=field(compare=False)
    node: Any=field(compare=False)
    payload: Any=field(compare=False)


@dataclass(order=True)
class SingleDispatch:
    """
    Similiar to the PrioritizedDispatch, this is used to
    queue requests but are used for non-service/subscription
    dispatching
    """
    priority: int
    node: Any=field(compare=False)
    endpoint: str=field(compare=False)
    payload: Any=field(compare=False)


class RootController(_HivemindAbstractObject):
    """
    Basic impl of subscription service handler
    """

    #
    # The node states that determine how we handle them.
    #
    NODE_PENDING = 'pending'
    NODE_ONLINE  = 'online'
    NODE_TERM    = 'terminate'

    class SubscriptionInfo(object):
        """
        Subscription data held by the RootController
        """
        def __init__(self, endpoint, port, node):
            self._endpoint = endpoint
            self._port = port
            self._node = node

        @property
        def port(self):
            return self._port


        @property
        def endpoint(self):
            return self._endpoint


        @property
        def node(self):
            return self._node


    def __init__(self, **kwargs):
        _HivemindAbstractObject.__init__(
            self,
            logger=kwargs.get('logger', None)
        )

        self._settings = kwargs

        self._port_count = 0

        # Known nodes out in the ecosystem
        # self._nodes = set()

        # Known services actively running
        self._services = {}

        # Requested subscriptions
        self._subscriptions = {}

        # How we know to shut down our dispatch threads
        self._abort = False
        self._done = False

        #
        # To avoid bogging down slow processing subscriptions,
        # we use a set of response threads to make sure things
        # stay nice and light as well as handle instances of
        # bugged nodes without halting the rest of the execution
        # state.
        #
        self._response_threads = []
        self._response_lock = threading.RLock()
        self._response_condition = threading.Condition(self._response_lock)
        self._response_queue = queue.PriorityQueue()
        self._single_dispatch_queue = queue.PriorityQueue()

        #
        # Startup utilities
        #
        self._startup_condition = kwargs.get('startup_condition', None)
        self._startup_event = kwargs.get('startup_event', None)
        self._abort_condition = kwargs.get('abort_condition', None)
        self._abort_event = kwargs.get('abort_event', None)

        #
        # We don't start the database until we're within the run() command
        # to make sure all database interactions with this object happen
        # on the same node.
        #
        self._database = None

        #
        # Features are essential tools for adding customization and allowing
        # the core to stay as lean as possible when they're not required.
        # Because the _Feature class in on a registry system, we only need
        # to import them to build our registry
        #
        # :see: hivemind.util.misc.SimpleRegistry for more
        #
        self._features = []
        for feature in global_settings['hive_features']:
            importlib.import_module(feature)

        for _, feature_class in _Feature._simple_registry.items():
            self._features.append(feature_class(self))


    @classmethod
    def send_to_controller(cls, service, payload):
        """
        Utility for shipping messages to our controller which
        will then route to the various subscribers (alternate
        thread)
        """
        json_data = {
            'service' : service.name,
            'node' : service.node.name,
            'payload' : payload,
            'priority' : 1 # TODO
        }

        default_port = global_settings['default_port']
        result = requests.post(
            f'http://127.0.0.1:{default_port}/service/{service.name}',
            json=json_data,
            verify=False
        )
        result.raise_for_status()
        return 0 # We'll need some kind of passback


    @classmethod
    def _register_post(cls, type_, json_data):
        """
        Utility for running a POST at the controller service
        """
        default_port = global_settings['default_port']

        result = requests_retry_session().post(
            f'http://127.0.0.1:{default_port}/register/{type_}',
            json=json_data,
            verify=False
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
            'meta' : node.metadata(),
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
    def register_service(cls, service) -> dict:
        """
        Register a service. This is called from a _Node

        :param service: The _Service instance that contains
                        the required info.
        :return: dict
        """
        return cls._register_post('service', {
            'node' : service.node.name,
            'name' : service.name,
        })


    @classmethod
    def register_subscription(cls, subscription) -> dict:
        """
        Register a subscription. This is called from a _Node

        :param subscription: The _Subscription instance that contains
                             the required info.
        :return: dict
        """
        return cls._register_post('subscription', {
            'node' : subscription.node.name,
            'filter' : subscription.filter,
            'endpoint' : subscription.endpoint,
            'port' : subscription.node.port
        })


    @classmethod
    def exec_(cls, logging=None):
        """
        Generic call used by most entry scripts to start the root without
        having to create a custom local instance
        """
        log.start(logging is not None)
        controller = cls()
        controller.run()
        return controller

    @property
    def database(self):
        return self._database
    

    # -- Virtual Interface

    def additional_routes(self) -> list:
        """
        Overload for customized routes.
        :return: list[tuple(rest_method:str, path:str, endpoint:func)]
        """
        return []

    # -- Overloaded

    def run(self, loop=None):
        """
        Our run operation is built to handle the various incoming
        requests and respond to the required items in time.
        """
        with self.lock:
            self._done = False

        self._app = None
        try:
            if not loop:
                loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            #
            # Data layer interface
            #
            self._init_database()

            self._handler_class = RootServiceHandler()
            self._node_handler = RootNodeHandler()
            self._handler_class.controller = self # Reverse pointer
            self._node_handler.controller = self

            self._app = web.Application(loop=loop)

            #
            # Visual templates for our features
            #
            template_loaders = [
                jinja2.FileSystemLoader(
                    global_settings['hive_root'] + '/static/templates'
                ),
            ]
            for dir_ in global_settings['template_dirs']:
                template_loaders.append(jinja2.FileSystemLoader(dir_))

            for feature in self._features:
                if not feature.static_files:
                    continue

                path = os.path.dirname(
                    inspect.getfile(feature.__class__).replace('\\','/')
                )

                template_loaders.append(jinja2.FileSystemLoader(
                    os.path.join(path, feature.static_files)
                ))

            # Setup the template engine
            aiohttp_jinja2.setup(
                self._app,
                loader=jinja2.ChoiceLoader(template_loaders)
            )

            self._app.add_routes([
                web.post('/register/node',
                         self._handler_class.register_node),

                web.post('/register/service',
                         self._handler_class.register_service),

                web.post('/register/subscription',
                         self._handler_class.register_subscription),

                web.get('/heartbeat',
                         self._handler_class.heartbeat),

                web.post('/heartbeat',
                         self._handler_class.heartbeat),

                web.post('/service/{tail:.*}',
                         self._handler_class.service_dispatch),

                web.post('/',
                         self._handler_class.index_post),
                web.get('/',
                         self._handler_class.index),

                # -- For development - need a "collectstatic" eq
                web.static('/static',
                           global_settings['static_dirs'][0],
                           follow_symlinks=True),
                web.get('/favicon.ico',
                        self._handler_class.favicon)
            ])

            self._node_handler.register_routes(self._app)
            self._install_utility_endpoints(self._app)

            for method, path, endpoint in self.additional_routes():
                self._app.add_routes([getattr(web, method)(path, endpoint)])

            self._install_feature_enpoints(self._app)

            #
            # Before running our server, let's start our queue threads
            # that deal with linking back to other services.
            #
            for i in range(self._settings.get('response_threads', 2)):
                res_thread = threading.Thread(
                    target=self._dispatch,
                    name=f'response_thread_{i}'
                )
                res_thread.start()
                self._response_threads.append(res_thread)


            default_port = global_settings['default_port']
            self.log_info(f"Serving on {default_port}...")

            if self._startup_condition:
                # Alert waiting parties that we're ready
                with self._startup_condition:
                    self._startup_condition.notify_all()

            if self._startup_event:
                with self.lock:
                    self._startup_event.set()

            # Just keep serving!
            web.run_app(
                self._app,
                port=default_port,
                handle_signals=False,
                access_log=self.logger,
                print=self.log_info,
                abort_condition=self._abort_condition,
                # reuse_port=True
            )

        except Exception as e: # pragma: no cover
            if not isinstance(e, KeyboardInterrupt):
                import traceback
                self.log_critical(traceback.format_exc())
                print (traceback.format_exc())

        finally:
            with self.lock:
                asyncio.run(self._shutdown())

                if self._startup_condition:
                    # Make sure we clean up if something went wrong too
                    with self._startup_condition:
                        self._startup_condition.notify_all()

                if self._abort_event:
                    self._abort_event.set()

                self._done = True

            return


    def base_context(self):
        """
        The initial context we use when rendering jinja2 templates
        for use in the hive webfront
        :return: dict
        """
        return {
            '_hive_name' : global_settings['name']
        }


    def get_node(self, name: str) -> (None, NodeRegister):
        """
        Aquire a node if it exists. Otherwise return None
        :param name: The name of the node to search for
        :return: NodeRegister|None
        """
        return self._database.new_query(
            NodeRegister, name=name
        ).get_or_null()


    def dispatch_one(self, node, endpoint, payload) -> None:
        """
        Queue a singluar dispatch to a node.

        :return: None
        """

        self.log_debug(f"Single Dispatch: {endpoint}")
        self._single_dispatch_queue.put(SingleDispatch(
            payload.pop('dispatch_priority', 1),
            node,
            endpoint,
            payload
        ))

        with self._response_condition:
            self._response_condition.notify()


    def service_count(self, node) -> int:
        """
        Query for the number of services this node consumes

        :param node: ``NodeRegister``
        :return: ``int``
        """
        # This will eventually make it's way to the database
        return len(self._services.get(node, {}))


    def subscription_count(self, node) -> int:
        """
        Query for the number of subscriptions this node consumes

        :param node: ``NodeRegister``
        :return: ``int``
        """
        # This will eventually make it's way to the database
        count = 0
        for filter_ in self._subscriptions:
            for si in self._subscriptions[filter_]:
                if node == si.node:
                    count += 1
        return count


    def node_log(self, node, lineno, raw=False) -> list:
        """
        Based on the node passed in, get the log that goes with it
        and return the lines from that lineno.

        .. note::

            This needs a completely different approach. It should be
            streaming this rather than reading the file every few
            seconds.

            See: aiohttp.web.WebSocket

        :param node: ``NodeRegister``
        :param lineno: The line that we want to read from
        :param raw: Push together as one string in the first
                    element of the list
        :return: tuple(new_line_no, list[str,])
        """
        log_path = os.path.join(
            global_settings['log_location'], node.name + '.log'
        )

        if not os.path.isfile(log_path):
            return None

        def _seek_to_line(handle, n):
            for ignored in islice(handle, n - 1):
                pass # Seek away

        with open(log_path, 'r') as f:
            if lineno == 0 and raw:
                # We want the whole file
                return (0, [f.read()])

            elif lineno < 0:
                # We want to obtain lines from bottom up
                total_lines = 0
                for line in f:
                    total_lines += 1

                lineno = max(0, total_lines + lineno)
                f.seek(0)

            if lineno > 0:
                _seek_to_line(f, lineno)

            output = []
            if raw:
                output[0] = ''
                for line in f:
                    output[0] += line + '\n'
            else:
                for line in f:
                    output.append(line)

            return (lineno + len(output), output)


    # -- Private Interface (reserved for running instance)

    def _node_exists(self, name):
        """
        Check the database for the node
        """
        query = self._database.new_query(
            NodeRegister, NodeRegister.name.equals(name)
        )
        return (query.count() > 0)


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

        if payload['status'] != self.NODE_TERM:
            self.log_info(f"Register Node: {payload['name']}")
        else:
            self.log_info(f"Deregister Node: {payload['name']}")

        node = self.get_node(payload['name'])

        with self.lock:
            with self.database.transaction:
                if not node:

                    if payload['status'] == self.NODE_TERM: # pragma: no cover
                        # We're removing the node. Shouldn't be
                        # here
                        return 0

                    self._port_count += 1
                    port = global_settings['default_port'] + self._port_count
                    node = self._database.create(
                        NodeRegister,
                        name=payload['name'],
                        status=payload['status'],
                        port=port
                    )

                    # Populate any metadata
                    for key, value in payload.get('meta', {}).items():
                        self._database.create(
                            NodeMeta,
                            node=node,
                            key=key,
                            value=str(value)
                        )

                    return port

                else:
                    destroy = None

                    # We've seen this node before (at least - we should
                    # have)
                    if payload['status'] == self.NODE_TERM:
                        # Clean up this node
                        self._remove_node(node)
                        return 0
                    else:
                        node.status = payload['status']
                        self._database.save(node)
                        return node.port


    def _remove_node(self, node_instance: NodeRegister) -> None:
        """
        Terminate all connections with a node. Because we base everything
        off the proxy, this becomes doable without too much headache.
        """
        with self.lock: # reentrant

            if node_instance in self._services:
                self._services.pop(node_instance)

            for filter_, subinfo in self._subscriptions.items():
                to_rem = []
                for d in subinfo:
                    if d.node == node_instance:
                        to_rem.append(d)
                for d in to_rem:
                    subinfo.remove(d)

            self._database.delete(node_instance)


    def _register_service(self, payload):
        """
        Register a service
        """
        assert isinstance(payload, dict), \
            'Service Registration payload must be a dict'

        assert all(k in payload for k in ('node', 'name')), \
            'Service Registration payload missing "node" or "name"'

        self.log_info(f"Register Service: {payload['name']} to {payload['node']}")

        node = self.get_node(payload['node'])
        assert node, f'Node {payload["node"]} not found'

        with self.lock:
            known_services = self._services.setdefault(node, {})

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
            all(k in payload for k in ('node', 'filter', 'endpoint', 'port')), \
            'Subscription Registration payload missing "node", ' \
            ' "filter", "port" or "endpoint"'

        node = self.get_node(payload['node'])
        assert node, f'Node {payload["node"]} not found'

        self.log_info(
            f"Register Subscription: {payload['node']} to {payload['filter']}"
        )

        with self.lock:

            known_subscriptions = self._subscriptions.setdefault(
                payload['filter'], []
            )
            known_subscriptions.append(
                self.SubscriptionInfo(
                    payload['endpoint'],
                    payload['port'],
                    node
                )
            )

        return 0


    def _delegate(self, path, payload):
        """
        Based on the path, we have to handle our work accordingly.
        """
        service_name = path.split('/')[-1]
        self.log_debug(f"Message from: {service_name}")

        self._response_queue.put(PrioritizedDispatch(
            payload.get('priority', 1),  # Prio (lower is higher prio!)
            service_name,                # Name
            payload.get('node', None),   # Node
            payload.get('payload', None) # Payload
        ))

        with self._response_condition:
            self._response_condition.notify()

        return { 'result' : True } # For now



    async def _shutdown(self):
        if self._app:
            await self._app.shutdown()
        with self._response_condition:
            self._abort = True
            self._response_condition.notify_all()
        self._database.disconnect()


    def _dispatch(self):
        """
        Based on what's available from the queue, ship out messages
        to any listening subsribers 
        """
        while True:

            with self._response_condition:
                while (not self._abort) and (
                    self._response_queue.empty() and self._single_dispatch_queue.empty()
                ):
                    self._response_condition.wait()

            dispatch_object = None
            with self._response_lock:
                if self._abort:
                    break

                try:
                    dispatch_object = self._response_queue.get_nowait()
                except queue.Empty:
                    pass # We may just have a single dispatch to fire

            if dispatch_object:
                # We have a dispatch - locate any matching subscriptions
                for filter_ in self._subscriptions:
                    if fnmatch.fnmatch(dispatch_object.name, filter_):

                        #
                        # We have a match - now it's time to ship this
                        # payload to the subscriptions undernearth
                        #
                        for si in self._subscriptions[filter_]:

                            node = self.get_node(si.node.name) # cache?
                            if node and node.status != self.NODE_ONLINE:
                                continue

                            url = f'http://127.0.0.1:{si.port}{si.endpoint}'
                            self._ship(
                                url, dispatch_object.payload, subinfo=(filter_, si)
                            )
            else:
                # Check if we have single dispatch commands to run
                single_dispatch = None
                with self._response_lock:
                    if self._abort:
                        break

                    try:
                        single_dispatch = self._single_dispatch_queue.get_nowait()
                    except queue.Empty:
                        continue # No worries.

                if not single_dispatch: # pragma: no cover
                    continue # Shouldn't be possible

                node = single_dispatch.node
                path = single_dispatch.endpoint
                self._ship(
                    f'http://127.0.0.1:{node.port}{path}',
                    single_dispatch.payload
                )


    def _ship(self, url, payload, subinfo=None) -> None:
        """
        Do a basic POST operation
        """
        try:
            result = requests.post(url, json=payload, verify=False)
            result.raise_for_status()
        except Exception as e:
            #
            # TESTME:
            # Ideally we never get here. Hitting this in the tests
            # will be a specific kind of challenge. One that I would
            # rather spend elsewhere but it's too much code to pragma
            # away
            #
            do_log = False
            with self.lock:
                if self._done:
                    return

                filter_, si = subinfo
                if filter_ in self._subscriptions:
                    if si in self._subscriptions:
                        do_log = True

            if do_log:
                self.log_error(f"POST to {url} failed!")
                self.log_error("  `-> " + str(e)) # ??


    def _init_database(self) -> None:
        """
        Initialize the database and make sure we have all the right bits
        :return: None
        """
        self._database = _DatabaseIntegration.start_database(
            global_settings['database']
        )

        active_tables = self._database.get_table_names()

        if TableDefinition.db_name() not in active_tables:
            #
            # The table definition is a rather vital table
            # We need to make sure it's available
            #
            self._database._create_table(TableDefinition)
            active_tables.append(TableDefinition.db_name())

        for name, table in RequiredTables:

            if name not in active_tables:
                self._database._create_table(table)
                TableDefinition.register_table(self._database, table)

            # else:
            #     TODO
            #     TableDefinition.validate_table(table)

        #
        # Build any feature requested tables
        #
        for feature in self._features:
            for table in feature.tables():
                if table.db_name() not in active_tables:
                    self._database._create_table(table)


    def _install_utility_endpoints(self, app: web.Application) -> None:
        """
        Utility endpoints provide a few user-oriented endpoints for use
        with the web interface.
        """
        self._app.add_routes([
            web.get('/api/{api_path:.*}', self._handler_class.api)
        ])


    def _install_feature_enpoints(self, app: web.Application) -> None:
        """
        Various components can be (en|dis)abled and, when they
        are active, we add them here.

        :param app: The aiohttp web application that we're adding
                    routes to
        :return: None
        """
        for feature_inst in self._features:
            for method, path, endpoint in feature_inst.endpoints():
                self._app.add_routes(
                    [getattr(web, method)(path, endpoint)]
                )
