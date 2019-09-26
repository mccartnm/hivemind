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

import queue
import logging
import fnmatch
import requests
import threading

# -- For Queue Prio
from dataclasses import dataclass, field
from typing import Any

import asyncio
from aiohttp import web

from . import log
from .base import _HivemindAbstractObject, _HandlerBase


class RootServiceHandler(_HandlerBase):
    """
    Web handler for the services in order to route the
    data through properly.
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


    async def register_task(self, request):
        """ Register a _Task """
        data = await request.json()
        task_connect = self.controller._register_task(data)
        return web.json_response(task_connect)


    async def heartbeat(self, request):
        """ Basic alive test """
        return web.json_response({'result' : True})


    async def service_dispatch(self, request):
        """ Dispatch service command """
        path = request.match_info['tail']
        data = await request.json()
        passback = self.controller._delegate(path, data)
        return web.json_response(passback)


    async def task_data_dispatch(self, request):
        # TODO
        pass


    async def index(self, request):
        return web.json_response({'result' : True})


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


class RootController(_HivemindAbstractObject):
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


    class SubscriptionInfo(object):
        """
        Subscription data held by the RootController
        """
        def __init__(self, endpoint, port, proxy):
            self._endpoint = endpoint
            self._port = port
            self._proxy = proxy

        @property
        def port(self):
            return self._port


        @property
        def endpoint(self):
            return self._endpoint


        @property
        def proxy(self):
            return self._proxy
        

    def __init__(self, **kwargs):
        _HivemindAbstractObject.__init__(
            self,
            logger=kwargs.get('logger', None)
        )

        self._settings = kwargs

        self._port_count = 0

        # Known nodes out in the ecosystem
        self._nodes = set()

        # Known services actively running
        self._services = {}

        # Requested subscriptions
        self._subscriptions = {}

        # Registered tasks
        self._tasks = {}

        # How we know to shut down our dispatch threads
        self._abort = False

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

        #
        # Startup utilities
        #
        self._startup_condition = kwargs.get('startup_condition', None)

        #
        # Data layer interface
        #
        # database_config = {
        #     'type' : 'sqlite',
        #     'name' : 'hivemind'
        # }
        # database_config.update(kwargs.get('database', {}))
        # self._database = _DatabaseScafolding.start_database(database_config)


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

        result = requests.post(
            f'http://127.0.0.1:{cls.default_port}/service/{service.name}',
            json=json_data
        )
        result.raise_for_status()
        return 0 # We'll need some kind of passback


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
    def register_task(cls, task):
        """
        Register a task. This is call from a _Node (specifically a TaskNode)

        :param task: _Task instance that we'll be using
        :return dict:
        """
        return cls._register_post('task', {
            'node' : task.node.name,
            'name' : task.name,
            'endpoint' : task.endpoint,
            'port' : task.node.port
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

    # -- Overloaded

    def run(self, loop=None):
        """
        Our run operation is built to handle the various incoming
        requests and respond to the required items in time.
        """
        self._app = None
        try:
            if not loop:
                loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            self._handler_class = RootServiceHandler()
            self._handler_class.controller = self # Reverse pointer

            self._app = web.Application(loop=loop)
            self._app.add_routes([
                web.post('/register/node',
                         self._handler_class.register_node),

                web.post('/register/service',
                         self._handler_class.register_service),

                web.post('/register/subscription',
                         self._handler_class.register_subscription),

                web.post('/register/task',
                         self._handler_class.register_task),

                web.get('/heartbeat',
                         self._handler_class.heartbeat),

                web.post('/heartbeat',
                         self._handler_class.heartbeat),

                web.post('/service/{tail:.*}',
                         self._handler_class.service_dispatch),

                web.post('/',
                         self._handler_class.index),
                web.get('/',
                         self._handler_class.index)
            ])

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


            self.log_info(f"Serving on {self.default_port}...")

            if self._startup_condition:
                # Alert waiting parties that we're ready
                with self._startup_condition:
                    self._startup_condition.notify_all()

            # Just keep serving!
            web.run_app(
                self._app,
                port=self.default_port,
                handle_signals=False,
                access_log=self.logger
            )

        except Exception as e:
            if not isinstance(e, KeyboardInterrupt):
                import traceback
                self.log_critical(traceback.format_exc())
                print (traceback.format_exc())

        finally:
            asyncio.run(self._shutdown())
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
            self.log_info(f"Register Node: {payload['name']}")
        else:
            self.log_info(f"Deregister Node: {payload['name']}")

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

            if proxy in self._tasks:
                self._tasks.pop(proxy)

            for filter_, subinfo in self._subscriptions.items():
                to_rem = []
                for d in subinfo:
                    if d.proxy == proxy:
                        to_rem.append(d)
                for d in to_rem:
                    subinfo.remove(d)


    def _register_service(self, payload):
        """
        Register a service
        """
        assert isinstance(payload, dict), \
            'Service Registration payload must be a dict'

        assert all(k in payload for k in ('node', 'name')), \
            'Service Registration payload missing "node" or "name"'

        self.log_info(f"Register Service: {payload['name']} to {payload['node']}")

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
            all(k in payload for k in ('node', 'filter', 'endpoint', 'port')), \
            'Subscription Registration payload missing "node", ' \
            ' "filter", "port" or "endpoint"'

        proxy = self.NodeProxy(payload['node'])

        self.log_info(
            f"Register Subscription: {payload['node']} to {payload['filter']}"
        )

        with self.lock:
            assert proxy in self._nodes, f'Node {payload["node"]} not found'
            known_subscriptions = self._subscriptions.setdefault(
                payload['filter'], []
            )
            known_subscriptions.append(
                self.SubscriptionInfo(
                    payload['endpoint'],
                    payload['port'],
                    proxy
                )
            )

        return 0


    def _register_task(self, payload):
        """
        Register a task
        """
        assert \
            isinstance(payload, dict), \
            'Task Registration payload must be a dict'
        assert \
            all(k in payload for k in ('node', 'filter', 'endpoint', 'port')), \
            'Task Registration payload missing "node", ' \
            ' "filter", "port" or "endpoint"'

        proxy = self.NodeProxy(payload['node'])

        self.log_info(
            f"Register Task: {payload['node']} to {payload['name']}"
        )

        task_required_data = {}

        with self.lock:
            assert proxy in self._nodes, f'Node {payload["node"]} not found'
            known_tasks = self._tasks.setdefault(proxy, {})

            assert \
                payload['name'] not in known_tasks, \
                f'The task {payload["name"]} already exists for {payload["node"]}'

            #
            # We have to do quite a few things here...
            # 1. Build an endpoint for the task
            # task_required_data['endpoint'] = 
            # 2. Based on the task info and any parameter definitions, we hold
            #    that until we request that action be taken
            # 3. Cron is obviously a little different but the idea is mostly the same
            #

        return task_required_data



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



    def _recieve_task_data(self, path, payload):
        """
        Based on the task information coming in, we store the information for
        our user to digest via the web server.
        :param path: The url path that we've entered with
        :param payload: The payload that we're given
        """
        return 0


    async def _shutdown(self):
        await self._app.shutdown()
        with self._response_condition:
            self._abort = True
            self._response_condition.notify_all()


    def _dispatch(self):
        """
        Based on what's available from the queue, ship out messages
        to any listening subsribers 
        """
        while True:

            with self._response_condition:
                while (not self._abort) and self._response_queue.empty():
                    self._response_condition.wait()

            dispatch_object = None
            with self._response_lock:
                if self._abort:
                    break

                try:
                    dispatch_object = self._response_queue.get_nowait()
                except queue.Empty:
                    continue # We must have missed it

            if not dispatch_object:
                continue # How??

            # We have a dispatch - locate any matching subscriptions
            for filter_ in self._subscriptions:
                if fnmatch.fnmatch(dispatch_object.name, filter_):

                    #
                    # We have a match - now it's time to ship this
                    # payload to the subscriptions undernearth
                    #
                    for si in self._subscriptions[filter_]:
                        url = f'http://127.0.0.1:{si.port}{si.endpoint}'
                        self._send_to_subscription(
                            url, dispatch_object.payload
                        )


    def _send_to_subscription(self, url, payload):
        result = requests.post(url, json=payload)
        try:
            result.raise_for_status()
        except Exception as e:
            print ("Sending to sub failed!") # FIXME
