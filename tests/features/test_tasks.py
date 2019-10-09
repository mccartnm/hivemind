"""
Tests for the optional tasks featureset
"""
import os
import copy
import time
import platform
import unittest
import requests

from hivemind.core import log
from hivemind.util import global_settings
from hivemind.util.misc import temp_dir
from hivemind.util.hivecontroller import HiveController
from hivemind.util.cliparse import build_hivemind_parser

from hivemind.features.task import TaskNode

class ATaskNode(TaskNode):
    use_config = 'sampledata/tasks_a.yaml'

class BadTaskNode(TaskNode):
    use_config = 'sampledata/badtasks.yaml'

def _within_test_hive(func):
    """
    Wrapper function to build a text hive and
    run a function within it
    """
    def _hive_func(self):

        parser = build_hivemind_parser()
        with temp_dir() as hive_dir:
            string_args = ['new', 'testhive']
            args = parser.parse_args(string_args)
            args.func(args)

            # Now move into said hive
            os.chdir('testhive')

            func(self)

    return _hive_func


class TestTasks(unittest.TestCase):

    @_within_test_hive
    def test_task_initial(self):
        """
        Test we can handle a basic task execute
        """
        hive_controller = HiveController(
            os.getcwd(),
            nodes=[ATaskNode],
            augment_settings={
                'hive_features' : [
                    # Need to turn the feature on
                    'hivemind.features.task'
                ],
                'default_port' : 9999
            }
        )

        with hive_controller.async_exec_():
            time.sleep(2.0)
            # -- TODO: Make this a better test and augment
            # the task funciton to create a file we can read
            # or something like that

            port = hive_controller.settings['default_port']

            def fire():
                requests.post(f'http://127.0.0.1:{port}/tasks/execute',
                               json={
                                   'node': 'ATaskNode',
                                   'name': 'test_task_a',
                                   'parameters' : {}
                               })

            for i in range(1):
                fire()

            res = requests.get(f'http://127.0.0.1:{port}/tasks')
            res.raise_for_status()


    @_within_test_hive
    def test_task_feature_required(self):
        """
        Test that we fail when trying to run task nodes without
        the feature
        """
        hive_controller = HiveController(
            os.getcwd(),
            nodes=[ATaskNode],
            augment_settings={
                # Make sure the feature is off
                'hive_features' : [
                    # 'hivemind.features.task'
                ],
                'default_port' : 10455
            }
        )

        with self.assertRaises(EnvironmentError):
            hive_controller.exec_(1.0)


    def test_task_node_validation(self):
        """
        Given a set of task nodes, validate them.
        """
        settings = {
            'hive_features' : ['hivemind.features.task']
        }

        with global_settings.override(settings):
            bad = BadTaskNode(name='testme')
            errors, warnings = bad.verify_config(chatty=False)
            self.assertFalse(bad.valid)
