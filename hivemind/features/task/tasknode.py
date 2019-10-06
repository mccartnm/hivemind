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
import inspect

from hivemind import _Node, RootController
from typing import Any

from hivemind.data.tables import NodeRegister

from hivemind.util.platformdict import pdict
from hivemind.util.taskyaml import TaskYaml
from .task import _Task, kTaskTypes
# from .tables import TaskRegister, TaskInfo

class TaskNode(_Node):
    """
    A utility node that lets us run tasks via a semi centralized
    hub (the root controller(s)) and provides simple-to-use, platform
    agnostic tools for all of it

    There are two ways we can use task nodes.

    - Via Subclassed Node:
        .. code-block:: python

            # In our hive nodes/sometasks/sometasks.py
            from hivemind.features.task import TaskNode

            class SomeTasks(TaskNode):
                # -- With a class attribute
                #    (path is relative to this one)
                use_config = 'myconfig.yaml'

    - ``hm`` command startup:
        .. code-block:: shell

            ~$> hm tasks --config myconfig.yaml

    .. tip::

        This is used in conjunction with the TaskFeature class to
        provide the full interface.

    """
    def __init__(self, name: str, config: (str, TaskYaml) = None, **kwargs) -> None:
        _Node.__init__(self, name, **kwargs)

        if config is None and hasattr(self, 'use_config'):
            path = os.path.dirname(
                inspect.getfile(self.__class__).replace('\\','/')
            )
            config = os.path.join(path, self.use_config)

        self._config = TaskYaml.load(config)
        self._valid = True
        self._tasks = []

    # -- Node Overrides

    def additional_registration(self, handler_class) -> None:
        """
        Register our tasks with the RootController
        :param handler_class: NodeSubscriptionHandler class
        :return: None
        """
        self.create_tasks()

        for task in self._tasks:
            handler_class.endpoints[task.endpoint] = task

            #
            # We add an endpoint to communicate back with results of
            # running our task. With the TaskFeature() enabled, this
            # will build the node-side interface it's expecting
            #
            result = self.register_task(task)
            # task.set_root_data(result)


    def on_shutdown(self):
        """
        Deregister any of our tasks!
        """
        for task in self._tasks:
            self.deregister_task(task)


    @property
    def valid(self) -> bool:
        return self._valid


    def create_tasks(self) -> None:
        """
        Iterate through our task descriptors in our TaskYaml and construct
        the _Task instances that will help power them.
        :return: None
        """
        for task_name, task_descriptor in self._config['tasks'].items():
            self._tasks.append(
                _Task(self, task_name, task_descriptor, self._config)
            )


    def verify_config(self) -> None:
        """
        Run a diagnostic on our task config to make sure all the
        components are there.
        :return: None
        """
        errors = []
        warnings = []

        #
        # Assert we have the minimum viable keys
        #
        required = ['name', 'tasks']

        for key in required:
            if self._config[key] is None:
                errors.append(f'Missing required key: {key}')

        #
        # Assert we have viable tasks
        #
        task_mapping = self._config['tasks']
        if task_mapping:
            if not isinstance(task_mapping, (dict, pdict)):
                errors.append(f'"tasks" must be a map. Got: {type(task_mapping)}')
            else:
                for task_name, task_data in task_mapping.items():

                    if ('type' not in task_data) or (not isinstance(task_data['type'], str)):
                        errors.append(f'Bad task type! Task: {task_name}. Must be a string.')

                    elif task_data['type'] not in kTaskTypes:
                        errors.append('Unknown task type! Task: '
                                      f'{task_name} - Type: {task_data["type"]}')

                    if 'help' in task_data:
                        if not isinstance(task_data['help'], str):
                            errors.append(f'Task {task_name} - help must be a string')

                    if 'parameters' in task_data:
                        if not isinstance(task_data['parameters'], list):
                            errors.append(f'Task {task_name} - parameters must be a list')
                        else:
                            for param in task_data['parameters']:
                                self._verify_param(task_name, param, errors, warnings)

        if errors:
            self._valid = False
            self.log_critical('Invalid task configuration!')
            for err in errors:
                self.log_critical('  - ' + err)
            return

        if warnings:
            for warning in warnings:
                self.log_warning(warning)


    def _verify_param(self, task_name: str, param: Any, errors: list, warnings: list) -> None:
        """
        Veify a particular parameter for a given task
        :param task_name: The name of the task we're intrspecting
        :param param: The parameter data we're working with
        :param errors: Any errors we find append here
        :param warnings: Any warning we find append here
        :return: None
        """
        if not isinstance(param, list):
            errors.append(f'Task: {task_name} - each parameter must be a list')
            return

        # TODO...

    # -- Registration functions for the node to reach the RootController

    def register_task(self, task):
        """
        Register a task within our node. This hijacks the
        ``RootController._register_post`` because it follows the
        same paradigm.

        :param task: _Task instance that we'll be using
        :return dict:
        """
        return RootController._register_post('task', {
            'node' : task.node.name,
            'name' : task.name,
            'type' : task.type,
            'endpoint' : task.endpoint,
            'port' : task.node.port,
            'status' : RootController.NODE_ONLINE
        })


    def deregister_task(self, task):
        """
        :param task: _Task instance that we'll be using
        :return dict:
        """
        return RootController._register_post('task', {
            'node': task.node.name,
            'name': task.name,
            'status': RootController.NODE_TERM
        })
