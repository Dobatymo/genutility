from genutility.downloadmanager import DownloadTask
from genutility.test import MyTestCase


class DownloadManagerTest(MyTestCase):
    def test_download_task(self):
        task = DownloadTask("https://example.invalid/file", "file")
        task.start()
        task.downloaded = 3
        task.done()

        self.assertIsNotNone(task.dt_started)
        self.assertEqual(3, task.downloaded)
        self.assertEqual(hash(("https://example.invalid/file", "file")), hash(task))


if __name__ == "__main__":
    import unittest

    unittest.main()
