import os
import unittest
import platform

from hivemind.util import TaskYaml, pdict
from hivemind.util import CommandParser, CommandError
from hivemind.util import ExpansionError, ComputeError

from hivemind.util.misc import run_process

CONFIG_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), 'test_configs'
)).replace('\\', '/')

class CommandTests(unittest.TestCase):
    """
    Some initial tests for the task utility that is the
    command processing
    """
    def setUp(self):
        self._config = TaskYaml.load(CONFIG_DIR + '/config_a.yaml')


    def test_run_basic_commands(self):
        """
        Some basic echoing should be fine to test out. Test the
        conditional section as well
        """
        commands = [
            'echo foo',
            'echo bar',
            {
                'if' : 'True',
                'than' : 'echo baz'
            },
            {
                'if' : 'False',
                'than' : ':fail',
                'else': 'echo ok'
            }
        ]
        parser = CommandParser(commands, task_data=self._config)
        parser.compute()


    def test_fail_command(self):
        """
        Test that the fail command is running and fails as expected
        """
        commands = [
            ':fail because'
        ]
        parser = CommandParser(commands, task_data=self._config)

        with self.assertRaises(CommandError):
            parser.compute()


    def test_method_command(self):
        """
        The method command is vital to even-keel growth
        """
        commands = [
            ':method run_simple_echo({helper})'
        ]
        parser = CommandParser(commands, task_data=self._config)
        parser.compute()


    def _compute(self, commands: list) -> None:
        """
        Helper function
        """
        parser = CommandParser(commands, task_data=self._config)
        parser.compute()


    def test_set_and_return_command(self):
        """
        Make sure we can set a value properly, also test that
        we can return from a func. Puting this together to make
        the testing easier
        """
        self._compute([
            ':set -g new_prop {helper}_extra'
        ])
        self.assertEqual(self._config.properties['new_prop'],
                         'a_root_value_extra')

        self._compute([
            ':set wont_prop {helper}_foo'
        ])
        self.assertTrue(self._config.properties['wont_prop'] is None)

        self._compute([
            ':set -g new_prop PRE_VALUE',
            ':return',
            ':set -g new_proper POST_VALUE'
        ])
        self.assertEqual(self._config.properties['new_prop'],
                         'PRE_VALUE')

    def test_source_command(self):
        """
        Make sure, in the same process, we can update our environment
        from another file and we can pull it in our expansion process
        """
        script_type = 'bat' if platform.system() == 'Windows' else 'sh'

        self._compute([
            ':source ' + CONFIG_DIR + '/test_env.' + script_type,
            ':set -g test_var {testenvvar}'
        ])

        self.assertEqual(self._config.properties['test_var'],
                         '/foo/bar')
