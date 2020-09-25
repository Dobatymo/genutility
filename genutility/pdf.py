from __future__ import absolute_import, division, print_function, unicode_literals

from io import open
from typing import TYPE_CHECKING

from PyPDF2 import PdfFileMerger, PdfFileReader

from .compat import FileNotFoundError
from .compat.contextlib import ExitStack
from .compat.pathlib import Path

if TYPE_CHECKING:
	from typing import Iterator, Union

	from .compat.os import PathLike

def join_pdfs_in_folder(path_in, file_out, overwrite=False):
	# type: (Path, Union[PathLike, str]) -> None

	""" Join all PDFs in `path_in` and write to `file_out`. """

	merger = PdfFileMerger(strict=True)

	if not path_in.exists():
		raise FileNotFoundError(path_in)

	with ExitStack() as stack:
		for path in path_in.glob("*.pdf"):
			if path.is_file():
				fr = stack.enter_context(path.open("rb")) # open does not support Path in <3.6
				merger.append(fr)

		if overwrite:
			mode = "w"
		else:
			mode = "x"

		with open(file_out, mode+"b") as fw:
			merger.write(fw)

def iter_pdf_text(path):
	# type: (str, ) -> Iterator[str]

	with open(path, "rb") as fr:
		pdf = PdfFileReader(fr)
		for i in range(pdf.getNumPages()):
			page = pdf.getPage(i)
			yield page.extractText()

def _read_pdf_pdfminer(path):
	from pdfminer.high_level import extract_text

	return extract_text(path)

def _read_pdf_tika(path):
	from tika import parser

	raw = parser.from_file(path)

	#return raw["metadata"]
	return raw["content"]

def read_pdf(path, engine="pdfminer"):
	# type: (str, str) -> str

	try:
		func = {
			"pdfminer": _read_pdf_pdfminer,
			"tika": _read_pdf_tika,
		}[engine]
	except KeyError:
		raise ValueError("Engine {} doesn't exist".format(engine))

	return func(path)

if __name__ == "__main__":
	from argparse import ArgumentParser

	parser = ArgumentParser(description="Merge pdf files in directory into one file.")
	parser.add_argument("dir", help="input directory")
	parser.add_argument("out", help="output file path")
	args = parser.parse_args()

	join_pdfs_in_folder(args.dir, args.out)
