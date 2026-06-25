from unittest import SkipTest

from genutility.test import MyTestCase


class TqdmTest(MyTestCase):
    def test_progress(self):
        try:
            from genutility.tqdm import Progress
        except ModuleNotFoundError as e:
            raise SkipTest(str(e))

        progress = Progress()
        self.assertEqual([1, 2], list(progress.track([1, 2], transient=True, disable=True)))
        with progress.task(total=1, transient=True, disable=True) as task:
            task.advance(1)
            task.update(completed=1)


if __name__ == "__main__":
    import unittest

    unittest.main()
