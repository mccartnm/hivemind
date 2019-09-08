import os
import sys

# Get to the right path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hivemind import RootController, _Node

import unittest

class HiveMindTests(unittest.TestCase):
    """
    TODO
    """
    def test_foo(self):
        pass


# ----------------------------------------------------------------------------------------------
# -- Main Function to run tests
# ----------------------------------------------------------------------------------------------
if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(HiveMindTests))
    unittest.TextTestRunner(verbosity=2).run(suite)
