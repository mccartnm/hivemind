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

from hivemind import _Node, RootController
from typing import Any

from .platformdict import pdict
from .taskyaml import TaskYaml


# -- Constants
kTaskTypes = [
    'request', #< A job set up with our controllers that can be activated
    'cron'     #< A cron utility that runs at a given time
]


class TaskNode(_Node):
    """
    A utility node that lets us run tasks via a semi centralized
    hub (the root controller(s)) and provides simple-to-use, platform
    agnostic tools for all of it
    """
    def __init__(self, name: str, config: (str, TaskYaml)) -> None:
        _Node.__init__(self, name)

        self._config = TaskYaml.load(config)
        self._valid = True
        self._tasks = []


    def additional_registration(self, handler_class) -> None:
        """
        Register our tasks with the RootController
        :param handler_class: NodeSubscriptionHandler class
        :return: None
        """
        for task in self._tasks:
            handler_class.endpoints[task.endpoint] = task

            #
            # We add an endpoint to communicate back with results of
            # running our task.
            #
            task.set_root_endpoint_data(RootController.register_task(task))


    @property
    def valid(self):
        return self._valid


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
