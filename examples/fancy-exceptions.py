from argparse import ArgumentParser

from genutility.json import json_lines
from genutility.rich import install_markdown_excepthook

parser = ArgumentParser()
parser.add_argument("--plain", action="store_true")
args = parser.parse_args()

if not args.plain:
    install_markdown_excepthook()
json_lines.from_path("s3://asd/qwe")
