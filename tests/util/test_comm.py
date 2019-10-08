import os
import zipfile
import unittest
import platform

from hivemind.util import TaskYaml, pdict
from hivemind.util import CommandParser, CommandError
from hivemind.util import ExpansionError, ComputeError
from hivemind.util.compression import ZFile

from hivemind.util.misc import run_process, temp_dir

CONFIG_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), 'test_configs'
)).replace('\\', '/')

from hivemind.util import global_settings

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
        # For this test, no internal comands used
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
            ':fail Because I said so!'
        ]
        parser = CommandParser(commands, task_data=self._config)

        with self.assertRaises(CommandError):
            parser.compute()


    def test_method_command(self):
        """
        The method command is vital to even-keel growth

        Our test yaml defines this function
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

        # Test that, by default, we keep properties within their scope
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


    def _touch(self, file: str) -> None:
        """
        Helper function to generate a file
        :param file: filepath to write to
        :return: None
        """
        with open(file, 'w') as f:
            f.write('')


    def test_copy_delete_command(self):
        """
        We all need copies and moves
        """
        with temp_dir() as source_dir:
            source_dir = source_dir.replace('\\', '/')

            # -- Let's write some simple files
            os.makedirs(source_dir + '/test_directory')
            self._touch(source_dir + '/foo.txt')
            self._touch(source_dir + '/bar.log')
            self._touch(source_dir + '/test_directory/schmoo.txt')
            self._touch(source_dir + '/test_directory/schmoo_2.txt')

            # -- copy tests
            with temp_dir() as dest_dir:
                dest_dir = dest_dir.replace('\\', '/')

                #
                # Let's start with the simplist case, a 1:1 copy
                #
                self._compute([
                    f':copy {source_dir}/foo.txt {dest_dir}/foo.txt'
                ])
                self.assertTrue(
                    os.path.isfile(f'{source_dir}/foo.txt') and \
                    os.path.isfile(f'{dest_dir}/foo.txt')
                )

                #
                # Now, let's clean that single item up
                #
                self._compute([
                    f':rm {dest_dir}/foo.txt'
                ])
                self.assertFalse(os.path.exists(f'{dest_dir}/foo.txt'))

                #
                # Let's test out our directory -> directory move
                #
                self._compute([
                    f':copy {source_dir}/test_directory {dest_dir}/test_directory'
                ])
                self.assertTrue(
                    os.path.isfile(f'{dest_dir}/test_directory/schmoo.txt') and \
                    os.path.isfile(f'{dest_dir}/test_directory/schmoo_2.txt')
                )

                #
                # Now, let's clean that whole directory up
                #
                self._compute([
                    f':rm {dest_dir}/test_directory'
                ])
                self.assertFalse(os.path.isdir(f'{dest_dir}/test_directory'))

                #
                # Now, let's test the glob!
                #
                self._compute([
                    f':copy {source_dir}/* {dest_dir}'
                ])
                self.assertTrue(
                    os.path.isfile(f'{dest_dir}/foo.txt') and \
                    os.path.isfile(f'{dest_dir}/bar.log') and \
                    os.path.isfile(f'{dest_dir}/test_directory/schmoo.txt') and \
                    os.path.isfile(f'{dest_dir}/test_directory/schmoo_2.txt')
                )

                # Glob remove
                self._compute([
                    f':rm {dest_dir}/*'
                ])
                self.assertTrue(len(os.listdir(dest_dir)) == 0)

                # Let's try ignoring some files
                self._compute([
                    f':copy -x *.txt {source_dir}/* {dest_dir}'
                ])

                # We could the directory (should we?)
                self.assertTrue(len(os.listdir(dest_dir)) == 2 and \
                                os.path.isfile(f'{dest_dir}/bar.log'))


    def test_move_delete_command(self):
        """
        Similar to the copy command, we should verify that the move
        has similar semantics
        """
        with temp_dir() as source_dir:
            source_dir = source_dir.replace('\\', '/')

            # -- Let's write some simple files
            os.makedirs(source_dir + '/test_directory')
            self._touch(source_dir + '/foo.txt')
            self._touch(source_dir + '/bar.log')
            self._touch(source_dir + '/test_directory/schmoo.txt')
            self._touch(source_dir + '/test_directory/schmoo_2.txt')

            with temp_dir() as dest_dir:
                dest_dir = dest_dir.replace('\\', '/')

                self._compute([
                    f':move {source_dir}/foo.txt {dest_dir}/foo.txt'
                ])

                self.assertTrue(
                    (not os.path.isfile(f'{source_dir}/foo.txt')) and \
                    os.path.isfile(f'{dest_dir}/foo.txt')
                )


    def test_read_global_settings(self):
        """
        We set this value long ago - just make sure the global settings stick with
        us.
        """
        self.assertEqual(global_settings['test_global_settings'], 'a value')


    def test_zip_basics(self):
        """
        The zip command is quite intense and has a good chunk of
        options. Let's just try a few.
        """
        with temp_dir() as source_dir:
            source_dir = source_dir.replace('\\', '/')

            os.makedirs(source_dir + '/test_directory')
            self._touch(source_dir + '/foo.txt')
            self._touch(source_dir + '/bar.log')
            self._touch(source_dir + '/test_directory/schmoo.txt')
            self._touch(source_dir + '/test_directory/schmoo_2.txt')

            with temp_dir() as dest_dir:
                dest_dir = dest_dir.replace('\\', '/')

                self._compute([
                    f':cd {dest_dir}',
                    f':zip myzip.zip --file {source_dir}'
                ])

                output = f'{dest_dir}/myzip.zip'
                self.assertTrue(
                    os.path.isfile(output)
                )

                with ZFile(output, 'r') as zfile:
                    infos = list(zfile.infolist())
                    self.assertEqual(len(infos), 4)

                self._compute([
                    f':cd {dest_dir}',
                    f':zip -x myzip.zip -o myzip'
                ])

                self.assertTrue(
                    os.path.isdir(f'{dest_dir}/myzip')
                )
                self.assertTrue(
                    os.path.isdir(f'{dest_dir}/myzip/test_directory')
                )
