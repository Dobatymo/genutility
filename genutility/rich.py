import sys
from traceback import format_exception

from rich.console import Console
from rich.markdown import Markdown


def install_markdown_excepthook(console=None):
    console_ = console or Console(file=sys.stderr)

    def excepthook(exc_type, exc_value, exc_traceback):
        lines = list(format_exception(exc_type, exc_value, exc_traceback))
        for line in lines[:-1]:
            console_.print(line, end="")

        args = [Markdown(arg) for arg in exc_value.args]
        if args:
            console_.print(f"{exc_type.__qualname__}:", *args)
        else:
            console_.print(f"{exc_type.__qualname__}")

    old_excepthook = sys.excepthook
    sys.excepthook = excepthook
    return old_excepthook


if __name__ == "__main__":

    install_markdown_excepthook()

    MARKDOWN = """
# This is an h1

Rich can do a pretty *decent* job of rendering markdown.

1. This is a list item
2. This is another list item
"""

    raise ValueError(MARKDOWN)
