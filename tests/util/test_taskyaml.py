

import os
import unittest
import platform

from hivemind.util import TaskYaml, pdict, ExpansionError
from hivemind.util._expressions.expr import (
    ExpressionError, _VariableExpansionExpression
)

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
            'val_d' : ['{val_a}', 'random_value'],
            'val_e' : 'foobarbazscmhoookayblarg'
        }

        with self._task_config.overload_data(mapping):

            # Just to test the function
            _VariableExpansionExpression._get_expressions_layout()

            result = self._task_config.expand(
                '{val_a|up}_{val_b|low}_{val_c|trim}({val_d|join(", ")})_{val_e|trunc(5)}'
            )

            self.assertEqual(
                result,
                'VALUE_A_value_b_value_c(value_a, random_value)_fooba'
            )

            self.assertEqual(
                self._task_config.expand('{val_e|quote()}'),
                f'"{mapping["val_e"]}"'
            )

            self.assertEqual(
                self._task_config.expand("{val_e|quote(M)}"),
                f"M{mapping['val_e']}M"
            )

            self.assertEqual(
                self._task_config.expand("{val_e|trunc(5, True)}"),
                mapping['val_e'][5:]
            )

            result = self._task_config.expand(
                '{innermapping:a_test_key:inner_key}'
            )
            self.assertEqual(result, 'myval')

            with self.assertRaises(ExpressionError):
                self._task_config.expand('{val_e|notafunc}')

            with self.assertRaises(ExpansionError):
                self._task_config.expand('{notakey:innerkey}')

            with self.assertRaises(ExpansionError):
                self._task_config.expand('{innermapping:a_test_key:not_ok}')

            with self.assertRaises(ExpansionError):
                self._task_config.expand('{doesntexist}')

            with self.assertRaises(ExpansionError):
                self._task_config.expand('{cyclic_a}')


    def test_overload_with_pdict(self):
        """
        Simple test to make sure the raw pdict data gets overloaded
        too.
        """
        other_mapping = pdict({"foo" : "bar"})
        with self._task_config.overload_data(other_mapping):
            self.assertEqual(self._task_config.properties['foo'], 'bar')


    def test_yaml_validity(self):
        """
        Test that we raise a flag in the event of an invalid yaml file
        """
        with self.assertRaises(OSError):
            TaskYaml.load('most_surely_not_a_file.yaml', chatty=False)

        self.assertTrue('TaskYaml' in self._task_config.__repr__())


    def test_yaml_platform_overrive(self):
        """
        Make sure we can swap platforms
        """
        if platform.system() == 'Windows':
            other = 'unix'
        else:
            other = 'windows'

        with self._task_config.using_platform(other):
            res = self._task_config.properties['ptest']

            if platform.system() == 'Windows':
                self.assertEqual(res, 'unix')
            else:
                self.assertEqual(res, 'win')


    def test_task_yaml_env(self):
        """
        Test that we can use the env section to properly
        populate an environemtn.
        """
        env = {
            'PATH' : 'initial/path',
            'MY_CUSTOM_VAL': "bar"
        }

        self._task_config.task_environment(env)

        self.assertEqual(
            env['PATH'],
            f'initial/path{os.pathsep}somepath/please'
        )

        self.assertEqual(env['MY_CUSTOM_VAL'], 'foo')
        self.assertEqual(env['A_DICT_VAL'], 'cool_beans')
