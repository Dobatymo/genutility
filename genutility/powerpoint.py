from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

from pptx import Presentation  # python-pptx

if TYPE_CHECKING:
	from typing import Iterator, List

def read_ppt(path):
	# type: (str, ) -> Iterator[List[str]]

	prs = Presentation(path)
	for slide in prs.slides:
		shapes = [shape.text for shape in slide.shapes if hasattr(shape, "text")]
		yield shapes
