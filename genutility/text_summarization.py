from operator import itemgetter

import spacy

from .metrics import same_words_similarity
from .text_segmentation import split_paragraphs


def get_spacy_tokenizer(modelname, lemmatize=True):
	nlu = spacy.load(modelname)

	if lemmatize:
		return lambda text: (t.lemma_ for t in nlu(text))
	else:
		return lambda text: map(str, nlu(text))

class NoParagraphsFound(Exception):
	pass

class QueryBasedParagraphExtraction(object):

	def __init__(self, modelname="en_core_web_sm"):
		self.tokenizer = get_spacy_tokenizer(modelname)

	def extract(self, text, query):
		# type: (str, str) -> str

		paragraphs = split_paragraphs(text)
		it = ((same_words_similarity(p, query, self.tokenizer), p) for p in paragraphs)

		try:
			return max(it, key=itemgetter(0))[1]
		except ValueError:
			raise NoParagraphsFound()

from .test import MyTestCase


class TextSummarizationTests(MyTestCase):

	text = ["""Copyright laws are changing all over the world. Be sure to check the
copyright laws for your country before downloading or redistributing
this or any other Project Gutenberg eBook.
""", """This header should be the first thing seen when viewing this Project
Gutenberg file. Please do not remove it. Do not change or edit the
header without written permission.
""", """Please read the "legal small print," and other information about the
eBook and Project Gutenberg at the bottom of this file. Included is
important information about your specific rights and restrictions in
how the file may be used. You can also find out about how to make a
donation to Project Gutenberg, and how to get involved.
"""]

	def test_a(self):
		fulltext = "\n".join(self.text)

		pe = QueryBasedParagraphExtraction("en_core_web_sm")

		result = pe.extract(fulltext, "LAWS")
		self.assertEqual(self.text[0], result)

		result = pe.extract(fulltext, "legal law involve")
		self.assertEqual(self.text[2], result)

if __name__ == "__main__":

	import unittest
	unittest.main()
