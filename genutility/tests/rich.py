from rich.markdown import Markdown
from rich.progress import Progress as RichProgress
from rich.text import Text

from genutility.rich import MarkdownHighlighter, Progress, StripAnsiHighlighter
from genutility.test import MyTestCase


class RichTest(MyTestCase):
    def test_progress(self):
        with RichProgress(disable=True) as p:
            progress = Progress(p)
            self.assertEqual([1, 2], list(progress.track([1, 2], transient=True)))
            with progress.task(total=1, transient=True) as task:
                task.advance(1)
                task.update(completed=1, total=1, description="done")

    def test_highlighters(self):
        self.assertIsInstance(MarkdownHighlighter()("**x**"), Markdown)
        self.assertEqual(Text("red"), StripAnsiHighlighter()("\x1b[31mred\x1b[0m"))


if __name__ == "__main__":
    import unittest

    unittest.main()
