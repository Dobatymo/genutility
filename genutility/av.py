from __future__ import generator_stop

from typing import Iterator

import numpy as np

import av


class CorruptFile(Exception):
    pass


def iter_video(path: str) -> Iterator[np.ndarray]:

    """Yield frames from a video file. For video device support see `genutility.cv.iter_video`."""

    with av.open(path, "r") as container:

        vs = container.streams.video[0]
        vs.thread_type = "AUTO"

        for frame in container.decode(vs):
            if frame.is_corrupt:
                raise CorruptFile("Frame %s at %s of %s is corrupt", frame.index, frame.time, path)
            yield frame.to_ndarray()  # or frame.to_rgb()
