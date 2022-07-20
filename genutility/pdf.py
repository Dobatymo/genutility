from __future__ import generator_stop

from contextlib import ExitStack
from os import PathLike
from pathlib import Path
from typing import Iterator, Union

from PyPDF2 import PdfMerger, PdfReader

PathType = Union[PathLike, str]


def join_pdfs_in_folder(path_in: Path, file_out: PathType, overwrite: bool = False) -> None:

    """Join all PDFs in `path_in` and write to `file_out`."""

    merger = PdfMerger(strict=True)

    if not path_in.exists():
        raise FileNotFoundError(path_in)

    with ExitStack() as stack:
        paths = sorted(path_in.glob("*.pdf"))
        for path in paths:
            if path.is_file():
                fr = stack.enter_context(path.open("rb"))
                merger.append(fr)

        if overwrite:
            mode = "w"
        else:
            mode = "x"

        with open(file_out, mode + "b") as fw:
            merger.write(fw)


def iter_pdf_text(path: str) -> Iterator[str]:

    with open(path, "rb") as fr:
        pdf = PdfReader(fr)
        for page in pdf.pages:
            yield page.extract_text()


def _read_pdf_pdfminer(path: str) -> str:
    from pdfminer.high_level import extract_text

    return extract_text(path)


def _read_pdf_tika(path: str) -> str:
    from tika import parser

    raw = parser.from_file(path)

    # return raw["metadata"]
    return raw["content"]


def read_pdf(path: str, engine: str = "pdfminer") -> str:

    try:
        func = {
            "pdfminer": _read_pdf_pdfminer,
            "tika": _read_pdf_tika,
        }[engine]
    except KeyError:
        raise ValueError(f"Engine {engine} doesn't exist")

    return func(path)


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Merge pdf files in directory into one file.")
    parser.add_argument("dir", help="input directory")
    parser.add_argument("out", help="output file path")
    args = parser.parse_args()

    join_pdfs_in_folder(args.dir, args.out)
