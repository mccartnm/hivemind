

import os
import unittest

from hivemind.util import TaskYaml, pdict, ExpansionError

CONFIG_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), 'test_configs'
))

class TaskYamlTests(unittest.TestCase):
    """
    Tests for the config utility
    """
    def setUp(self):
        self._task_config = TaskYaml.load(os.path.join(CONFIG_DIR, 'config_a.yaml'))


    def test_basic_load(self):
        """
        Assert that simple dictionary style lookup works and we can
        grab names from the file.
        """
        self.assertEqual(self._task_config['name'], 'test-basics')


    def test_basic_expansion(self):
        """
        Assert that the config handles simple variable expansion
        """
        result = self._task_config.expand_property('test_variable')

        proper = pdict.quick({
            'windows' : 'test_on_win/test_2',
            'unix' : 'test_on_unix/test_2'
        })
        self.assertEqual(result, proper)

        result = self._task_config.expand_property('home_test')
        proper = pdict.quick({
            'windows' : os.environ.get('HOMEPATH'),
            'unix' : os.environ.get('HOME')
        })
        self.assertEqual(result, proper)


    def test_list_expansion(self):
        """
        Expansion can also work on strings
        """
        result = self._task_config.expand_property('list_test', rtype=list)
        self.assertEqual(result, ['foo', 'a_root_value'])

        result = self._task_config.expand_property('test_multipart', rtype=list)
        self.assertEqual(result, ['my', 'test', 'multipart'])


    def test_basic_expansion_failures(self):
        """
        Assert we fail gracefuly.
        """
        with self.assertRaises(ExpansionError):
            self._task_config.expand_property('test_multipart')

        self._bad_config = TaskYaml.load(os.path.join(CONFIG_DIR, 'bad_config.yaml'))
        with self.assertRaises(ExpansionError):
            self._bad_config.expand_property('rec_b_val')


    def test_basic_string_expressions(self):
        """
        String expressions! Wee!

        Here, things get interesting.
        """

        mapping = {
            'val_a' : 'value_a',
            'val_b' : 'VALUE_B',
            'val_c' : '    value_c   ',
            'val_d' : ['{val_a}', 'random_value']
        }

        with self._task_config.overload_data(mapping):

            result = self._task_config.expand(
                '{val_a|up}_{val_b|low}_{val_c|trim}({val_d|join(", ")})'
            )

            self.assertEqual(
                result,
                'VALUE_A_value_b_value_c(value_a, random_value)'
            )
