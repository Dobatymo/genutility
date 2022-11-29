from __future__ import generator_stop

import unittest
from datetime import timedelta
from fractions import Fraction

from packaging import version

from genutility.test import MyTestCase, parametrize
from genutility.videofile import AvVideo, CvVideo

try:
    import av  # noqa: F401

    av_available = True
except ImportError:
    av_available = False

try:
    import cv2  # noqa: F401

    cv_available = True
except ImportError:
    cv_available = False


class VideofileTest(MyTestCase):
    @unittest.skipUnless(av_available, "PyAV required")
    @parametrize(
        (
            "testfiles/video/empty.mp4",
            {
                "width": 320,
                "height": 240,
                "duration": timedelta(microseconds=40000),
                "fps": Fraction(25, 1),
                "sample_aspect_ratio": Fraction(1, 1),
                "display_aspect_ratio": Fraction(4, 3),
                "format": "yuv420p",
            },
        ),
    )
    def test_AvVideo(self, path, truth):
        with AvVideo(path) as vf:
            self.assertEqual(truth, vf.meta)

    @unittest.skipUnless(
        av_available and version.parse("10.0.0") <= version.parse(av.__version__), "PyAV>=10.0.0 required"
    )
    @parametrize(
        (
            "testfiles/video/com.apple.quicktime.artwork.mp4",
            {
                "width": 320,
                "height": 240,
                "duration": timedelta(microseconds=40000),
                "fps": Fraction(25, 1),
                "sample_aspect_ratio": Fraction(1, 1),
                "display_aspect_ratio": Fraction(4, 3),
                "format": "yuv420p",
            },
        ),
    )
    def test_AvVideo_fail(self, path, truth):
        with AvVideo(path) as vf:
            self.assertEqual(truth, vf.meta)

    @unittest.skipUnless(cv_available, "OpenCV required")
    @parametrize(
        (
            "testfiles/video/com.apple.quicktime.artwork.mp4",
            {
                "width": 320,
                "height": 240,
                "duration": timedelta(microseconds=40000),
                "fps": 25.0,
                "sample_aspect_ratio": Fraction(1, 1),
                "display_aspect_ratio": Fraction(4, 3),
                "format": "I420",
            },
        ),
        (
            "testfiles/video/empty.mp4",
            {
                "width": 320,
                "height": 240,
                "duration": timedelta(microseconds=40000),
                "fps": 25.0,
                "sample_aspect_ratio": Fraction(1, 1),
                "display_aspect_ratio": Fraction(4, 3),
                "format": "I420",
            },
        ),
    )
    def test_CvVideo(self, path, truth):
        with CvVideo(path) as vf:
            self.assertEqual(truth, vf.meta)


if __name__ == "__main__":
    import unittest

    unittest.main()
