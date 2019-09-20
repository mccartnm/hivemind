"""
Tests for the platform aware dictionary tools
"""
import unittest

from hivemind.util import PlatformAwareDict, pdict

class TestPlatformAwareDict(unittest.TestCase):

    def test_pdict_is_class(self):
        """
        Make sure pdict is mearly a pointer to the
        full object
        """
        self.assertTrue(PlatformAwareDict == pdict)


    def test_basic_existence(self):
        """
        Make sure an emptry pdict is false
        """
        empty = pdict()
        self.assertFalse(empty)

        basic = pdict({"foo" : "bar"})
        self.assertTrue(basic)

