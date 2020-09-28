from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

import piexif
from PIL import Image, ImageDraw, ImageFont
from PIL.ExifTags import GPSTAGS, TAGS

from .exceptions import NoActionNeeded

if TYPE_CHECKING:
	from typing import Any, Dict, Tuple, Union
	Color = Union[str, Tuple[int, int, int]]

def multiline_textsize(text, ttf, spacing=4):
	# type: (str, ImageFont, int) -> Tuple[int, int]

	lines = text.splitlines()

	width = 0
	height = (len(lines) - 1) * spacing

	for line in lines:
		w, h = ttf.getsize(line)
		width = max(width, w)
		height = height + h

	return width, height

def exifinfo(image):
	# type: (Image, ) -> Dict[str, Any]

	ret = dict()

	exifd = image._getexif()

	if exifd is None:
		return dict()

	for k, v in exifd.items():
		try:
			tag = TAGS[k]
			if tag == "GPSInfo":
				ret[tag] = dict()
				for k, v in v.items():
					try:
						gpstag = GPSTAGS[k]
						ret[tag][gpstag] = v
					except KeyError:
						pass
			else:
				ret[tag] = v
		except KeyError:
			pass

	return ret

def text_with_outline(draw, pos, text, font, fillcolor, outlinecolor, outlinesize=1):
	# type: (ImageDraw, Tuple[int, int], str, ImageFont, Color, Color, int) -> None

	x, y = pos
	delta = outlinesize

	# thin border
	draw.text((x-delta, y), text, font=font, fill=outlinecolor)
	draw.text((x+delta, y), text, font=font, fill=outlinecolor)
	draw.text((x, y-delta), text, font=font, fill=outlinecolor)
	draw.text((x, y+delta), text, font=font, fill=outlinecolor)

	# thicker border
	draw.text((x-delta, y-delta), text, font=font, fill=outlinecolor)
	draw.text((x+delta, y-delta), text, font=font, fill=outlinecolor)
	draw.text((x-delta, y+delta), text, font=font, fill=outlinecolor)
	draw.text((x+delta, y+delta), text, font=font, fill=outlinecolor)

	# now draw the text over it
	draw.text((x, y), text, font=font, fill=fillcolor)

def write_text(img, text, alignment="TL", fillcolor=(255, 255, 255), outlinecolor=(0, 0, 0), fontsize=0.03, padding=(5, 5)):
	# (Image, str, str, Color, Color, Union[float, int], Union[float, Tuple[int, int]]) -> None

	if alignment not in {"TL", "TC", "TR", "BL", "BC", "BR"}:
		raise ValueError("Invalid alignment: {}".format(alignment))

	if isinstance(fontsize, int):
		pass
	elif isinstance(fontsize, float):
		fontsize = int(img.height * fontsize)
	else:
		raise ValueError("fontsize must be float or int")

	if isinstance(padding, tuple):
		pass
	elif isinstance(padding, float):
		padding = int(img.width * padding), int(img.height * padding)
	else:
		raise ValueError("padding must be float or Tuple[int, int]")

	font = ImageFont.truetype("arial.ttf", fontsize)

	d = ImageDraw.Draw(img)
	size_text = d.textsize(text, font=font)

	if alignment == "TL":
		pos = padding
	elif alignment == "TC":
		pos = (img.width // 2 - size_text[0] // 2, padding[1])
	elif alignment == "TR":
		pos = (img.width - padding[0] - size_text[0], padding[1])
	elif alignment == "BL":
		pos = (padding[0], img.height - padding[1] - size_text[1])
	elif alignment == "BC":
		pos = (img.width // 2 - size_text[0] // 2, img.height - padding[1] - size_text[1])
	elif alignment == "BR":
		pos = (img.width - padding[0] - size_text[0], img.height - padding[1] - size_text[1])

	text_with_outline(d, pos, text, font, fillcolor, outlinecolor, 2)

def _fix_orientation(img, orientation):
	# type (Image, int) -> Image

	if orientation == 1:
		raise NoActionNeeded("File already properly rotated")
	elif orientation == 2:
		img = img.transpose(Image.FLIP_LEFT_RIGHT)
	elif orientation == 3:
		img = img.transpose(Image.ROTATE_180)
	elif orientation == 4:
		img = img.transpose(Image.FLIP_TOP_BOTTOM)
	elif orientation == 5:
		img = img.transpose(Image.TRANSPOSE)
	elif orientation == 6:
		img = img.transpose(Image.ROTATE_270)
	elif orientation == 7:
		img = img.transpose(Image.TRANSVERSE)
	elif orientation == 8:
		img = img.transpose(Image.ROTATE_90)
	else:
		raise ValueError("Unsupported orientation")

	return img

def fix_orientation(img, exif):
	# type (Image, dict) -> Image

	orientation = exif["0th"][piexif.ImageIFD.Orientation]
	img = _fix_orientation(img, orientation)
	exif["0th"][piexif.ImageIFD.Orientation] = 1

	return img
