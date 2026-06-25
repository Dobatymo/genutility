from unittest import SkipTest

from genutility.test import MyTestCase


class RichTest(MyTestCase):
    def test_progress(self):
        try:
            from rich.progress import Progress as RichProgress

            from genutility.rich import Progress
        except ModuleNotFoundError as e:
            raise SkipTest(str(e))

        progress = Progress(RichProgress(disable=True))
        self.assertEqual([1, 2], list(progress.track([1, 2], transient=True)))
        with progress.task(total=1, transient=True) as task:
            task.advance(1)
            task.update(completed=1, total=1, description="done")

    def test_highlighters(self):
        try:
            from rich.markdown import Markdown
            from rich.text import Text

            from genutility.rich import MarkdownHighlighter, StripAnsiHighlighter
        except ModuleNotFoundError as e:
            raise SkipTest(str(e))

        self.assertIsInstance(MarkdownHighlighter()("**x**"), Markdown)
        self.assertEqual(Text("red"), StripAnsiHighlighter()("\x1b[31mred\x1b[0m"))


if __name__ == "__main__":
    import unittest

    unittest.main()
