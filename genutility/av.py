from typing import Iterator

import numpy as np

from .videofile import AvVideo, BadFile  # noqa: F401


class CorruptFile(Exception):
    pass


def iter_video(path: str) -> Iterator[np.ndarray]:
    """Yield frames from a video file. For video device support see `genutility.cv.iter_video`."""

    with AvVideo(path) as video:
        for _time, frame in video.iterall(native=True):
            if frame.is_corrupt:
                raise CorruptFile("Frame %s at %s of %s is corrupt", frame.index, frame.time, path)
            yield frame.to_ndarray()
