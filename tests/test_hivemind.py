import os
import sys
import unittest
import argparse
import threading

# Make sure we can import hivemind proper
TEST_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(TEST_BASE_DIR))

from hivemind import RootController, _Node

from hivemind.core import log
from hivemind.util import global_settings
from hivemind.util.misc import temp_dir
from hivemind.util.hivecontroller import HiveController
from hivemind.util.cliparse import build_hivemind_parser

global_settings.set({
    'test_global_settings' : 'a value'
})

class HiveMindTests(unittest.TestCase):
    """
    Initial tests for hivemind
    """
    def test_simple_network(self):

        class SendNode(_Node):
            def services(self):
                self._ping = self.add_service('ping', self._ping_func)

            def _ping_func(self, service):
                service.send('test')
                service.sleep_for(1.0)
                return 0

        class RecNode(_Node):
            def subscriptions(self):
                self._sub =self.add_subscription('ping', self._sub_func)

            def _sub_func(self, payload):
                if not isinstance(payload, str):
                    return

                global_settings.set({'__the_answer' : 42})

        parser = build_hivemind_parser()
        with temp_dir() as hive_dir:
            string_args = ['new', 'testhive']
            args = parser.parse_args(string_args)
            args.func(args)

            # Now move into said hive
            os.chdir('testhive')

            hive_controller = HiveController(os.getcwd(),
                                             nodes=[SendNode, RecNode])

            hive_controller.exec_(2.0)

            self.assertEqual(global_settings['__the_answer'], 42)



def build_test_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--test', action='append', help='Test select directories at a time')
    return parser


# ----------------------------------------------------------------------------------------------
# -- Main Function to run tests
# ----------------------------------------------------------------------------------------------
if __name__ == "__main__":
    log.start(False)
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    parser = build_test_parser()

    args, unknown = parser.parse_known_args()

    if args.test:
        for t in args.test:
            suite.addTests(loader.discover(
                TEST_BASE_DIR + '/' + t
            ))
    else:
        suite.addTests(loader.loadTestsFromTestCase(HiveMindTests))

        # Test the util library
        suite.addTests(loader.discover(
            TEST_BASE_DIR + '/util'
        ))

    res = unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
    sys.exit(1 if not res else 0)
