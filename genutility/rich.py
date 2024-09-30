import logging
import re
import sys
from string import Formatter
from traceback import format_exception
from typing import IO, Any, Callable, Dict, Iterable, List, Optional, Sequence, Union

from rich.console import Console, Group, JustifyMethod, OverflowMethod, Style
from rich.highlighter import Highlighter
from rich.markdown import Markdown
from rich.progress import BarColumn
from rich.progress import Progress as _RichProgress
from rich.progress import ProgressColumn, ProgressType, RenderableType
from rich.progress import Task as RichTask
from rich.progress import TaskID, TimeElapsedColumn
from rich.table import Column
from rich.text import Text
from typing_extensions import Self

from ._files import PathType
from .callbacks import BaseTask
from .callbacks import Progress as _Progress
from .file import copen
from .typing import SizedIterable

logger = logging.getLogger(__name__)


class NoneFormatter(Formatter):
    def __init__(self, default: Any) -> None:
        self.default = default
        super().__init__()

    def format_field(self, value, spec):
        if value is None:
            value = self.default
        return super().format_field(value, spec)


class DoubleFormatTextColumn(ProgressColumn):
    def __init__(
        self, text_format: str = "{task.description}", default: Any = 0.0, table_column: Optional[Column] = None
    ) -> None:
        self.text_format = text_format
        self.formatter = NoneFormatter(default)
        super().__init__(table_column=table_column or Column(no_wrap=True))

    def render(self, task: RichTask) -> Text:
        out = self.text_format.format(task=task)
        return Text(self.formatter.format(out, task=task))


def get_double_format_columns() -> List[ProgressColumn]:
    return [DoubleFormatTextColumn(), BarColumn(), TimeElapsedColumn()]


def install_markdown_excepthook(console: Optional[Console] = None) -> Callable:
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


class Task(BaseTask):
    def __init__(
        self, progress: _RichProgress, total: Optional[float] = None, description: Optional[str] = None, **fields: Any
    ) -> None:
        self.progress = progress
        description = description or "Working..."
        self.task_id = self.progress.add_task(description, total=total, **fields)

    @property
    def description(self) -> str:
        return self.progress._tasks[self.task_id].description

    def remove(self) -> None:
        self.progress.remove_task(self.task_id)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.remove()

    def advance(self, delta: float) -> None:
        self.progress.advance(self.task_id, advance=delta)

    def update(
        self,
        *,
        completed: Optional[float] = None,
        total: Optional[float] = None,
        description: Optional[str] = None,
        **fields: Any,
    ) -> None:
        self.progress.update(self.task_id, completed=completed, total=total, description=description, **fields)


class Progress(_Progress):
    def __init__(self, progress: _RichProgress) -> None:
        self.progress = progress
        self.prolog: Optional[RenderableType] = None
        self.epilog: Optional[RenderableType] = None

        # patch `live.get_renderable` which is usually set to `rich.progress.Progress.get_renderable`
        self.progress.live.get_renderable = self.get_renderable

    def track(
        self,
        sequence: Union[Iterable[ProgressType], Sequence[ProgressType]],
        total: Optional[float] = None,
        description: Optional[str] = None,
        transient: bool = False,
        **fields: Any,
    ) -> Iterable[ProgressType]:
        description = description or "Working..."
        task_id = self.progress.add_task(description, total=total, **fields)
        try:
            yield from self.progress.track(sequence, task_id=task_id)
        finally:
            if transient:
                self.progress.remove_task(task_id)

    def track_auto(
        self,
        sequence: SizedIterable[ProgressType],
        description: Optional[str] = None,
        **fields: Any,
    ) -> Iterable[ProgressType]:
        description = description or "Working..."
        with self.task(description=description, **fields) as task:
            for completed, item in enumerate(sequence):
                total = len(sequence)
                task.update(completed=completed, total=total)
                yield item

    def task(self, total: Optional[float] = None, description: str = "Working...", **fields: Any):
        return Task(self.progress, total, description, **fields)

    def get_renderable(self) -> RenderableType:
        renderables = []
        if self.prolog:
            renderables.append(self.prolog)
        if self.progress.tasks:
            renderables.append(self.progress.get_renderable())
        if self.epilog:
            renderables.append(self.epilog)

        return Group(*renderables)

    def set_prolog(self, prolog: Optional[RenderableType] = None) -> None:
        """Use to add arbitrary renderables before the progress to the live display.
        Pass None to disable.
        """

        self.prolog = prolog

    def set_epilog(self, epilog: Optional[RenderableType] = None) -> None:
        """Use to add arbitrary renderables after the progress to the live display.
        Pass None to disable.
        """

        self.epilog = epilog

    def print(self, s: str, end="\n") -> None:
        """Print a renderable to the console. It will not be part of the live/progress display,
        but printed to the normal console display. It will be done safely,
        i.e. not interrupting the progress display.
        """

        self.progress.print(
            s,
            end=end,
            markup=False,
            highlight=False,
            soft_wrap=True,
        )

    def refresh(self) -> None:
        self.progress.refresh()


class RichAriaProgress:
    """To be used with `genutility.aria.AriaDownloader` `active_callback` arguments."""

    def __init__(self, progress: _RichProgress) -> None:
        self.progress = progress
        self.tasks: Dict[str, TaskID] = {}  # gid to task_id

    def __call__(self, entries: Dict[str, Any]) -> None:
        existing = self.tasks.keys() & entries.keys()  # in both
        new = entries.keys() - self.tasks.keys()  # only in entries
        old = self.tasks.keys() - entries.keys()  # only in tasks

        for gid in existing:
            self.progress.update(
                self.tasks[gid],
                total=int(entries[gid]["totalLength"]),
                completed=int(entries[gid]["completedLength"]),
            )

        for gid in new:
            self.tasks[gid] = self.progress.add_task(
                gid,
                start=True,
                total=int(entries[gid]["totalLength"]),
                completed=int(entries[gid]["completedLength"]),
            )

        for gid in old:
            self.progress.remove_task(self.tasks[gid])
            del self.tasks[gid]


class StdoutFile:

    def __init__(
        self,
        console: Optional[Console] = None,
        path: Optional[PathType] = None,
        mode: str = "xt",
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
        compresslevel: int = 9,
        style: Optional[Union[str, Style]] = None,
        justify: Optional[JustifyMethod] = None,
        overflow: Optional[OverflowMethod] = None,
        no_wrap: Optional[bool] = None,
        emoji: Optional[bool] = None,
        markup: Optional[bool] = None,
        highlight: Optional[bool] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        crop: bool = True,
        soft_wrap: Optional[bool] = None,
        new_line_start: bool = False,
    ) -> None:
        if console is None and path is None:
            raise ValueError("console and path cannot both be None")

        assert mode in ("wt", "at", "xt")
        encoding = encoding or "utf-8"

        if path is not None:
            self.fp: Optional[IO] = copen(
                path, mode, encoding=encoding, errors=errors, newline=newline, compresslevel=compresslevel
            )

            def _write(text: str) -> None:
                self.fp.write(text)

        else:
            assert console is not None  ## for mypy
            self.fp = None

            def _write(text: str) -> None:
                console.print(
                    text,
                    end="",
                    style=style,
                    justify=justify,
                    overflow=overflow,
                    no_wrap=no_wrap,
                    emoji=emoji,
                    markup=markup,
                    highlight=highlight,
                    width=width,
                    height=height,
                    crop=crop,
                    soft_wrap=soft_wrap,
                    new_line_start=new_line_start,
                )

        self.write = _write

    def __enter__(self) -> Self:
        return self

    def close(self) -> None:
        if self.fp is not None:
            self.fp.close()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class StdoutFileNoStyle(StdoutFile):
    def __init__(self, *args, **kwargs) -> None:
        _kwargs = dict(
            encoding="utf-8",
            markup=False,
            highlight=False,
            soft_wrap=True,
        )
        _kwargs.update(kwargs)
        super().__init__(*args, **_kwargs)


class MarkdownHighlighter(Highlighter):
    def __call__(self, text: Union[str, Text]) -> Union[Text, Markdown]:
        if isinstance(text, str):
            return Markdown(text)
        elif isinstance(text, Text):
            return text
        else:
            raise TypeError(f"str or Text instance required, not {text!r}")

    def highlight(self, text: Text) -> None:
        """Not called"""


class StripAnsiHighlighter(Highlighter):
    # https://stackoverflow.com/a/14693789
    ansi_escape = re.compile(
        r"""
        \x1B  # ESC
        (?:   # 7-bit C1 Fe (except CSI)
            [@-Z\\-_]
        |     # or [ for CSI, followed by a control sequence
            \[
            [0-?]*  # Parameter bytes
            [ -/]*  # Intermediate bytes
            [@-~]   # Final byte
        )
    """,
        re.VERBOSE,
    )

    def __call__(self, text: Union[str, Text]) -> Text:
        if isinstance(text, str):
            return Text(self.ansi_escape.sub("", text))
        elif isinstance(text, Text):
            return text
        else:
            raise TypeError(f"str or Text instance required, not {text!r}")

    def highlight(self, text: Text) -> None:
        """Not called"""


if __name__ == "__main__":
    install_markdown_excepthook()

    MARKDOWN = """
# This is an h1

Rich can do a pretty *decent* job of rendering markdown.

1. This is a list item
2. This is another list item
"""

    raise ValueError(MARKDOWN)
