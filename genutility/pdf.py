from contextlib import ExitStack
from os import PathLike
from pathlib import Path
from typing import Iterator, Optional, Union

from PyPDF2 import PdfReader, PdfWriter

PathType = Union[PathLike, str]


def join_pdfs_in_folder(
    path_in: Path,
    file_out: PathType,
    overwrite: bool = False,
    rotate: Optional[int] = None,
    password: Optional[Union[str, bytes]] = None,
) -> None:
    """Join all PDFs in `path_in` and write to `file_out`.
    `overwrite`: Overwrite existing output files
    `rotate`: Optionally rotate pages in 90 degree increments
    `password`: Optionally specify input file password
    """

    if not path_in.exists():
        raise FileNotFoundError(path_in)

    with ExitStack() as stack:
        paths = sorted(path_in.glob("*.pdf"))
        writer = PdfWriter()

        for path in paths:
            if path.is_file():
                fr = stack.enter_context(path.open("rb"))
                reader = PdfReader(fr, strict=True, password=password)
                for page in reader.pages:
                    if rotate is not None:
                        page = page.rotate(rotate)
                    writer.add_page(page)

        if overwrite:
            mode = "w"
        else:
            mode = "x"

        with open(file_out, mode + "b") as fw:
            writer.write_stream(fw)


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

    from genutility.args import is_dir

    parser = ArgumentParser(description="Merge pdf files in directory into one file.")
    parser.add_argument("dir", type=is_dir, help="input directory")
    parser.add_argument("out", type=Path, help="output file path")
    parser.add_argument("--rotate", type=int, help="Rotate in 90 degree increments")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files")
    parser.add_argument("--password", type=str, help="Input file password")
    args = parser.parse_args()

    join_pdfs_in_folder(args.dir, args.out, args.overwrite, args.rotate, args.password)
