from genutility.callbacks import Progress
from genutility.test import MyTestCase, parametrize


class TextCallbacks(MyTestCase):
    @parametrize((True,), (False,))
    def test_progress_track(self, transient):
        truth = [1, 2, 3]
        p = Progress()
        result = list(p.track(truth, description="unittest", transient=transient))
        self.assertEqual(truth, result)
        result = list(p.track(truth, description="unittest", transient=transient, kwarg=1))
        self.assertEqual(truth, result)

    @parametrize((True,), (False,))
    def test_progress_task(self, transient):
        p = Progress()
        with p.task(description="unittest", transient=transient) as task:
            task.advance(1)
        with p.task(description="unittest", transient=transient, kwarg=1) as task:
            task.advance(1)

    def test_progress_print(self):
        p = Progress()
        p.print("unittest")
        p.print("unittest", kwarg=1)


if __name__ == "__main__":
    import unittest

    unittest.main()
