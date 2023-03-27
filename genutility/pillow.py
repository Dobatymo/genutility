from typing import Any, Dict, Tuple, Union

import piexif
from PIL import Image, ImageDraw, ImageFont
from PIL.ExifTags import GPSTAGS, TAGS

from .exceptions import NoActionNeeded

Color = Union[str, Tuple[int, int, int]]


def multiline_textsize(text: str, ttf: ImageFont, spacing: int = 4) -> Tuple[int, int]:
    lines = text.splitlines()

    width = 0
    height = (len(lines) - 1) * spacing

    for line in lines:
        w, h = ttf.getsize(line)
        width = max(width, w)
        height = height + h

    return width, height


def exifinfo(image: Image.Image) -> Dict[str, Any]:
    ret: Dict[str, Any] = {}

    exifd = image._getexif()

    if exifd is None:
        return {}

    for k, v in exifd.items():
        try:
            tag = TAGS[k]
            if tag == "GPSInfo":
                ret[tag] = {}
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


def text_with_outline(
    draw: ImageDraw,
    pos: Tuple[int, int],
    text: str,
    font: ImageFont,
    fillcolor: Color,
    outlinecolor: Color,
    outlinesize: int = 1,
) -> None:
    x, y = pos
    delta = outlinesize

    # thin border
    draw.text((x - delta, y), text, font=font, fill=outlinecolor)
    draw.text((x + delta, y), text, font=font, fill=outlinecolor)
    draw.text((x, y - delta), text, font=font, fill=outlinecolor)
    draw.text((x, y + delta), text, font=font, fill=outlinecolor)

    # thicker border
    draw.text((x - delta, y - delta), text, font=font, fill=outlinecolor)
    draw.text((x + delta, y - delta), text, font=font, fill=outlinecolor)
    draw.text((x - delta, y + delta), text, font=font, fill=outlinecolor)
    draw.text((x + delta, y + delta), text, font=font, fill=outlinecolor)

    # now draw the text over it
    draw.text((x, y), text, font=font, fill=fillcolor)


def write_text(
    img: Image.Image,
    text: str,
    alignment: str = "TL",
    fillcolor: Color = (255, 255, 255),
    outlinecolor: Color = (0, 0, 0),
    fontsize: Union[float, int] = 0.03,
    padding: Union[float, Tuple[int, int]] = (5, 5),
) -> None:
    if alignment not in {"TL", "TC", "TR", "BL", "BC", "BR"}:
        raise ValueError(f"Invalid alignment: {alignment}")

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


def _fix_orientation(img: Image.Image, orientation: int) -> Image.Image:
    if orientation == 1:
        raise NoActionNeeded("File already properly rotated")
    elif orientation == 2:
        img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    elif orientation == 3:
        img = img.transpose(Image.Transpose.ROTATE_180)
    elif orientation == 4:
        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    elif orientation == 5:
        img = img.transpose(Image.Transpose.TRANSPOSE)
    elif orientation == 6:
        img = img.transpose(Image.Transpose.ROTATE_270)
    elif orientation == 7:
        img = img.transpose(Image.Transpose.TRANSVERSE)
    elif orientation == 8:
        img = img.transpose(Image.Transpose.ROTATE_90)
    else:
        raise ValueError("Unsupported orientation")

    return img


def fix_orientation(img: Image.Image, exif: dict) -> Image.Image:
    orientation = exif["0th"][piexif.ImageIFD.Orientation]
    img = _fix_orientation(img, orientation)
    exif["0th"][piexif.ImageIFD.Orientation] = 1

    return img
