from __future__ import generator_stop

from genutility.nlp import detokenize, resembles_english_word, tokenize
from genutility.test import MyTestCase, parametrize


class NLPTest(MyTestCase):
    @parametrize(
        ("How are you?",),
        ('What "are" you?',),
        ("Hello (world)",),
    )
    def test_tokenize_detokenize(self, truth):
        result = detokenize(tokenize(truth))
        self.assertEqual(truth, result)

    @parametrize(
        ("English", True),
        ("française", False),
    )
    def test_resembles_english_word(self, word, truth):
        result = resembles_english_word(word)
        self.assertEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
