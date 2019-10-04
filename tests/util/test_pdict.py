"""
Tests for the platform aware dictionary tools
"""
import copy
import platform
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


    def test_type_error(self):
        """
        Only accept dict and PlatformAwareDict info
        """
        with self.assertRaises(TypeError):
            pdict(1)

        with self.assertRaises(TypeError):
            pdict(True)

        with self.assertRaises(TypeError):
            pdict("test")

        # This is fine!
        pdict(pdict({}))


    def test_alt_platform(self):
        """
        Test that platform can be switched
        """
        if platform.system() in ("Linux", "Darwin"):
            proper = 'bar'
            opo_platform = "Windows"
            alt = 'foo'
        else:
            proper = 'foo'
            opo_platform = "Linux"
            alt = 'bar'

        test_dict = pdict({
            "schmoo" : {
                "windows" : "foo",
                "unix" : "bar"
            }
        })
        self.assertTrue(test_dict.platform == platform.system())

        self.assertEqual(test_dict['schmoo'], proper)
        test_dict.set_platform(opo_platform)
        self.assertEqual(test_dict['schmoo'], alt)


    def test_unix(self):
        """
        Test that the unix marker works
        """
        test_dict = pdict({}, platform_='Linux')
        self.assertTrue(test_dict.is_unix)
        test_dict = pdict({}, platform_='Darwin')
        self.assertTrue(test_dict.is_unix)
        test_dict = pdict({}, platform_='unix')
        self.assertTrue(test_dict.is_unix)

        test_dict = pdict({}, platform_='Windows')
        self.assertFalse(test_dict.is_unix)


    def test_quick(self):
        """
        Test the quick functionality of the PlatformAwareDict
        """
        mapping = {
            'windows' : 'foo',
            'unix' : 'bar'
        }
        val = PlatformAwareDict.quick(mapping)

        if platform.system() == 'Windows':
            self.assertEqual(val, 'foo')
        else:
            self.assertEqual(val, 'bar')


    def test_raw_command(self):
        """
        Test that we can grab the underlying dictionary object
        """
        d = {"foo" : "bar"}
        test_dict = pdict(d)

        self.assertTrue(test_dict != d)
        self.assertTrue(test_dict.raw() == d)

        # Check the copy option
        self.assertTrue(id(test_dict.raw(copy=True)) != id(d))


    def test_deepcopy(self):
        """
        Test that we can in fact deepcopy this instance
        """
        d = {"foo" : {"bar" : "baz"}}
        test_dict = pdict(d)
        self.assertEqual(
            test_dict.raw(),
            copy.deepcopy(test_dict).raw()
        )


    def test_iteration(self):
        """
        Test that we can iterate through a given pdict
        """
        d = {
            "foo" : "bar",
            "baz" : "spanner",
            "glorb" : "gotcha",
        }
        test_dict = pdict(d)

        for k, v in test_dict.items():
            self.assertEqual(test_dict[k], v)


    def test_getset(self):
        """
        Test the good ole' getting and settings commands
        """
        test_dict = pdict({"foo" : "bar"})
        self.assertEqual(
            test_dict.get('not in there', None),
            None
        )
        self.assertEqual(test_dict["foo"], "bar")
        test_dict['its in now'] = True
        self.assertTrue(test_dict["its in now"])
