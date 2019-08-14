from __future__ import absolute_import, division, print_function, unicode_literals

from io import open
from pathlib import Path
try:
	from contextlib import ExitStack
except ImportError:
	from contextlib2 import ExitStack

from PyPDF2 import PdfFileMerger

from .twothree import FileNotFoundError

def join_pdfs_in_folder(path_in, file_out, overwrite=False):
	# type: (Union[Path, str], Union[Path, str]) -> None

	""" Join all PDFs in `path_in` and write to `file_out`. """

	if not isinstance(path_in, Path):
		path_in = Path(path_in)

	merger = PdfFileMerger(strict=True)

	if not path_in.exists():
		raise FileNotFoundError(path_in)

	with ExitStack() as stack:
		for path in path_in.glob("*.pdf"):
			if path.is_file():
				fr = stack.enter_context(open(path, "rb"))
				merger.append(fr)

		if overwrite:
			mode = "w"
		else:
			mode = "x"

		with open(file_out, mode+"b") as fw:
			merger.write(fw)

if __name__ == "__main__":
	from argparse import ArgumentParser

	parser = ArgumentParser(description='Merge pdf files in directory into one file.')
	parser.add_argument('dir', help='input directory')
	parser.add_argument('out', help='output file path')
	args = parser.parse_args()

	join_pdfs_in_folder(args.dir, args.out)
