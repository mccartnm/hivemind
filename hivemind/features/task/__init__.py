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
from aiohttp import web
import aiohttp_jinja2

from hivemind import RootController
from hivemind.core.feature import _Feature
from hivemind.data.tables import NodeRegister

# This is a bit of a weird case because we define
from .task import _Task
from .tasknode import TaskNode
from .tables import TaskRegister, TaskInfo


class TaskFeature(_Feature):
    """
    Define the tasks plugin.

    .. tip::

        This is for the controller interface. For the node interface,
        check out the tasknode.py file next to this one.

    Tasks are a simple use case of the hivemind system. By creating
    nodes with individual tasks that can be executed via a user
    input on the web interface or via a cronjob-like system under
    the hood.

    All of this information and logging is then sent through to our
    core controller and database to be inspected.
    """
    name = 'tasks'

    # -- _Feature overrides

    def endpoints(self) -> tuple:
        """
        Plugin function. Get any endpoints this feature includes
        for the root controller web server

        :return: list(tuple(rest_method:str,
                            endpoint_path:str,
                            callback: callable))
        """
        return [
            ('post', '/register/task', self.register_task),
            ('get', '/tasks', self.index),
            ('post', '/tasks/execute', self.execute_task)
        ]


    def tables(self) -> list:
        """
        Plugin function.

        :return: list of tables we need made for the
                 tasks feature
        """
        return [TaskRegister, TaskInfo]

    # -- End overrides

    # -- Endpoints

    async def register_task(self, request):
        """ Register a _Task """
        data = await request.json()
        if data.get('status') == RootController.NODE_TERM:
            self._deregister_task(data)
            return web.json_response({'result' : True})
        else:
            task_connect = self._register_task(data)
            return web.json_response(task_connect)


    @aiohttp_jinja2.template('tasks/tasks_index.html')
    async def index(self, request):
        """
        The endpoint we use for task management.

        .. note::

            This is used via the RootController rather than the node.
            This way the root controller web interface can host all
            tasks rather than having to visit a website for each of
            them.

        :param request: aiohttp request
        :return: context for the jijna2 task template
        """
        return self.controller.base_context()


    async def execute_task(self, request):
        """
        Request a task to be executed on a given node.
        """
        data = await request.json()

        required = ('node', 'name', 'parameters')
        self._validate_keys(data, required, 'Task Execution')

        res = self._node_and_task(data)
        if not res: # pragma: no cover
            msg = f'Node {data["node"]} or ' + \
                  f'task {data["name"]} not found'
            assert False, msg # ??

        node, task = res
        self.controller.log_info(
            f"Execute Task: {task.name} from {node.name}"
        )

        #
        # -- Queue this up with the controller. This is better
        #    than trying to send on a thread that could be busy
        #    doing other things. Our dispatchers are built for this
        #
        self.controller.dispatch_one(
            node,
            task.endpoint,
            data['parameters']
        )
        return web.json_response({'result' : True})


    async def tasks_update(self, request):
        """
        Update tasks based on the request payload.

        The task update payload can take a few different forms. The payload should
        contain the following:

        ``node``: The name of the node we're attached to

        ``name``: The name of the task our node understands

        ``type``: The type of the update that we're applying.
            - "started" : We've just started executing this task
            - "info" : We have information on this task as it runs
            - "error" : We have something going wrong with this task
            - "completed" : We've completed the task successfully

        type == "started"
            - ??

        type == "info"
            - 

        :param controller: The RootController instance running the web server
        :return: ?
        """
        data = await request.json()

        # if not TaskNode.verify_task_update(data):
            # return # ??




    async def task_data_dispatch(self, request):
        # TODO
        pass


    # -- Private Methods


    def _node_and_task(self, data) -> (tuple, None):
        """
        Get the node and task required based on the data passed in

        :return: None if cannot be found or (NodeRegister, TaskRegister)
        """
        try:
            node = self.controller.database.new_query(
                NodeRegister, name=data['node']
            ).get()
        except NodeRegister.DoesNotExist: # pragma: no cover
            return # ???/

        try:
            task = self.controller.database.new_query(
                TaskRegister, node=node, name=data['name']
            ).get()
        except TaskRegister.DoesNotExist: # pragma: no cover
            return # -- need an error of some sort

        return node, task


    def _validate_keys(self, payload, keys, name):
        """
        Do a simple validation on a given payload
        """
        assert \
            isinstance(payload, dict), \
            f'{name} payload must be a dict'

        assert \
            all(k in payload for k in keys), \
            f'{name} payload missing one or more required key'


    def _deregister_task(self, payload):
        """
        Remove a task from the registery
        """

        required = ('node', 'name')
        self._validate_keys(payload, required, 'Task Deregistration')

        node = self.controller.get_node(payload['node'])
        assert node, f'Node {payload["node"]} not found'

        self.controller.log_info(
            f"Remove Task: {payload['name']} from {node.name}"
        )

        try:
            task_registry = self.database.new_query(
                TaskRegister, node=node, name=payload['name']
            ).get()
        except TaskRegister.DoesNotExist: # pragma: no cover
            return

        self.database.delete(task_registry)


    def _register_task(self, payload):
        """
        Register a task. This generates the proper
        """
        required = ('node', 'name', 'type', 'endpoint', 'port')
        self._validate_keys(payload, required, 'Task Registration')

        node = self.controller.get_node(payload['node'])
        assert node, f'Node {payload["node"]} not found'

        self.controller.log_info(
            f"Register Task: {node.name} to {payload['name']}"
        )

        task_required_data = {}

        with self.lock:
            new_task, _ = self.database.get_or_create(
                TaskRegister,
                node=node,
                name=payload['name'],
                endpoint=payload['endpoint'],
                type=payload['type']
            )

            # print ('registered task', payload['name'])

            #
            # We have to do quite a few things here...
            #
            # 2. Based on the task info and any parameter definitions, we hold
            #    that until we request that action be taken
            # 3. Cron is obviously a little different but the idea is mostly the same
            #

        return task_required_data