

import os
import unittest
import platform

from hivemind.util import misc


class UtilMiscTests(unittest.TestCase):

    # -- Dictionaries to test features with

    def d1(self):
        return {
            "foo" : {
                "bar" : [{ "key" : "value" }],
                "baz" : "meeks",
                "anotha" : "rabbit"
            }
        }


    def d2(self):
        return {
            "foo" : {
                "bar" : [{ "key" : "another" }],
                "baz" : "schmoo",
                "bloog" : "blarg"
            }
        }


    def test_merge_dictionaries(self):

        a = self.d1()
        b = self.d2()

        output = dict(misc.merge_dicts(a, b))

        self.assertTrue(type(output), dict)

        # We always take the second entry
        self.assertEqual(output['foo']['baz'], 'schmoo')
        self.assertEqual(output['foo']['bloog'], 'blarg')
        self.assertEqual(output['foo']['anotha'], 'rabbit')
        self.assertEqual(output['foo']['bar'], [{"key" : "another"}])


    def test_merge_lists_within(self):
        """
        This is a crappy test.
        """
        a = self.d1()
        b = self.d2()

        output = dict(
            misc.merge_dicts(a, b, combine_keys={'bar' : "key" })
        )


    def test_levenshtein(self):
        """
        Test our fuzzmy match algo
        """
        real_word = 'MyWord'

        tests = [
            'mdwork',
            'Myword',
            'wordmy',
            'foo',
            'whatisthis',
            ''
        ]

        result = list(map(
            lambda x: misc.levenshtein(real_word, x), tests)
        )
        self.assertTrue(min(result) == 1)
        self.assertEqual(max(result), len('whatisthis'))
        self.assertEqual(tests[result.index(min(result))], 'Myword')
