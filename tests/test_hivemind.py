import os
import sys

# Make sure we can import hivemind proper
TEST_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(TEST_BASE_DIR))

from hivemind import RootController, _Node

import unittest

class HiveMindTests(unittest.TestCase):
    """
    TODO
    """
    def test_foo(self):

        class MyNode(_Node):
            foo = "bar"


# ----------------------------------------------------------------------------------------------
# -- Main Function to run tests
# ----------------------------------------------------------------------------------------------
if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(HiveMindTests))

    # Test the util library
    suite.addTests(loader.discover(
        TEST_BASE_DIR + '/util'
    ))

    unittest.TextTestRunner(verbosity=2).run(suite)
