import re
from typing import List

re_paragraphs = re.compile(r"((?:[^\n][\n]?)+)")


def split_paragraphs(text: str) -> List[str]:
    return re_paragraphs.findall(text)
