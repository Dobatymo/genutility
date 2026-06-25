import os
from tempfile import TemporaryDirectory

from genutility.fileformats.srt import SRTFile
from genutility.fileformats.srt import Subtitle as SRTSubtitle
from genutility.fileformats.sub import Sub
from genutility.test import MyTestCase


class FileFormatsTest(MyTestCase):
    def test_srt(self):
        with TemporaryDirectory() as tempdir:
            path = os.path.join(tempdir, "test.srt")
            subtitle = SRTSubtitle()
            subtitle.num = 7
            subtitle.set_times("00:00:01,000", "00:00:02,500")
            subtitle.append("hello")

            with SRTFile(path, "w") as srt:
                srt.write_subtitle(subtitle)
            with SRTFile(path) as srt:
                result = next(srt)

        self.assertEqual((7, 1000, 2500, ["hello"]), (result.num, result.start, result.end, result.lines))

    def test_sub(self):
        with TemporaryDirectory() as tempdir:
            path = os.path.join(tempdir, "test.sub")
            with open(path, "w", encoding="utf-8") as fw:
                fw.write("{1}{2}hello|world\n")
            with Sub(path) as sub:
                result = sub.readline()

        self.assertEqual((1, 2, ["hello", "world"]), (result.start, result.end, result.lines))


if __name__ == "__main__":
    import unittest

    unittest.main()
