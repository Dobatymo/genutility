import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import List

re_paragraphs = re.compile(r"((?:[^\n][\n]?)+)")

def split_paragraphs(text):
	# type: (str, ) -> List[str]

	return re_paragraphs.findall(text)
