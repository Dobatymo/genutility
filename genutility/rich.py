import logging
import sys
from traceback import format_exception
from typing import Any, Callable, Iterable, List, Optional, Sequence, Union

from rich.console import Console
from rich.markdown import Markdown
from rich.progress import BarColumn
from rich.progress import Progress as RichProgress
from rich.progress import ProgressColumn, ProgressType
from rich.progress import Task as RichTask
from rich.progress import TimeElapsedColumn
from rich.table import Column
from rich.text import Text

from .callbacks import BaseTask
from .callbacks import Progress as _Progress

logger = logging.getLogger(__name__)

from string import Formatter


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
        self, progress: RichProgress, total: Optional[float] = None, description: Optional[str] = None, **fields: Any
    ) -> None:
        self.progress = progress
        description = description or "Working..."
        self.task_id = self.progress.add_task(description, total=total, **fields)

    def __enter__(self) -> BaseTask:
        return self

    def __exit__(self, *args):
        self.progress.remove_task(self.task_id)

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
    def __init__(self, progress: RichProgress) -> None:
        self.progress = progress

    def track(
        self,
        sequence: Union[Iterable[ProgressType], Sequence[ProgressType]],
        total: Optional[float] = None,
        description: Optional[str] = None,
        **fields: Any,
    ) -> Iterable[ProgressType]:
        description = description or "Working..."
        task_id = self.progress.add_task(description, total=total, **fields)
        try:
            yield from self.progress.track(sequence, task_id=task_id)
        finally:
            self.progress.remove_task(task_id)

    def task(self, total: Optional[float] = None, description: str = "Working...", **fields: Any):
        return Task(self.progress, total, description, **fields)

    def print(self, s: str, end="\n") -> None:
        self.progress.print(s, end=end)


if __name__ == "__main__":
    install_markdown_excepthook()

    MARKDOWN = """
# This is an h1

Rich can do a pretty *decent* job of rendering markdown.

1. This is a list item
2. This is another list item
"""

    raise ValueError(MARKDOWN)
