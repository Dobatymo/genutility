import re

re_paragraphs = re.compile(r"((?:[^\n][\n]?)+)")

def split_paragraphs(text):
	# type: (str, ) -> List[str]

	return re_paragraphs.findall(text)
