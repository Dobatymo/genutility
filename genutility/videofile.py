import logging
from datetime import timedelta
from fractions import Fraction
from os import PathLike, fspath
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, Sequence, Tuple, Union

import numpy as np
from typing_extensions import Self

if TYPE_CHECKING:
    from av import VideoFrame

# if __debug__:
#     import av
#     import cv2

logger = logging.getLogger(__name__)


def _raise_exists(outpath: Path, overwrite: bool = False) -> None:
    if not overwrite and outpath.exists():
        raise FileExistsError()


class NoGoodFrame(Exception):
    pass


class NoKeyFrame(Exception):
    pass


class BadFile(Exception):
    pass


class VideoBase:
    single_frame_ratio = 0.5  # fixme: what is this used for?
    time_base: Fraction
    native_duration: int

    def calculate_offsets(self, time_base: Fraction, duration: int) -> Iterator[int]:
        raise NotImplementedError

    def _frame_range(self, time_base: Fraction, duration: int) -> Iterator[int]:
        raise NotImplementedError

    def frame_range(self) -> Iterator[int]:
        return self._frame_range(self.time_base, self.native_duration)

    def _get_frame(self, offset: int, native: bool = False) -> Tuple[float, np.ndarray]:
        raise NotImplementedError

    def _frame_to_file(self, frame: Any, outpath: PathLike) -> None:
        raise NotImplementedError

    def iterate(self) -> Iterator[Tuple[float, np.ndarray]]:
        for offset in self.calculate_offsets(self.time_base, self.native_duration):
            try:
                yield self._get_frame(offset)
            except NoKeyFrame as e:
                yield offset, e

    def iterall(self, native: bool = False) -> Iterator[Tuple[float, np.ndarray]]:
        raise NotImplementedError

    def save_frame_to_file(self, pos: float, outpath: PathLike) -> None:
        frametime, frame = self._get_frame(int(self.native_duration * pos), native=True)
        self._frame_to_file(frame, outpath)

    def close(self) -> None:
        raise NotImplementedError

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def fourcc(integer):
    import struct

    return struct.pack("<i", integer)

    # return integer.to_bytes(4, "little") # python 3 only


class CvVideo(VideoBase):
    def __init__(self, path: Union[str, PathLike, int]) -> None:
        self.cv2 = self.import_backend()

        if isinstance(path, PathLike):
            path = fspath(path)

        self.cap = self.cv2.VideoCapture(path)
        if not self.cap.isOpened():
            raise ValueError("Could not open file")
        logger.debug("Reading video using backend: %s", self.cap.getBackendName())

        frame_width = int(self.cap.get(self.cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(self.cap.get(self.cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count = int(self.cap.get(self.cv2.CAP_PROP_FRAME_COUNT))

        if frame_width == 0 or frame_height == 0:
            raise ValueError(f"Invalid video file (zero frame dimensions): {path}")

        if frame_count == 0:
            raise ValueError(f"Invalid video file (zero frame count): {path}")

        pixel_aspect_ratio = Fraction(
            int(self.cap.get(self.cv2.CAP_PROP_SAR_NUM)), int(self.cap.get(self.cv2.CAP_PROP_SAR_DEN))
        )

        if pixel_aspect_ratio == 0:
            pixel_aspect_ratio = Fraction(1, 1)

        display_aspect_ratio = pixel_aspect_ratio * Fraction(frame_width, frame_height)

        fps = self.cap.get(self.cv2.CAP_PROP_FPS)
        try:
            duration = timedelta(seconds=frame_count / fps)
        except ZeroDivisionError:
            raise BadFile(f"Cannot open {path}")

        self.native_duration = frame_count  # exclusive
        self.time_base = Fraction(1 / fps)

        self.meta = {
            "width": frame_width,
            "height": frame_height,
            "duration": duration,  # container duration in seconds
            "fps": fps,
            "sample_aspect_ratio": pixel_aspect_ratio,
            "display_aspect_ratio": display_aspect_ratio,
            "format": fourcc(int(self.cap.get(self.cv2.CAP_PROP_CODEC_PIXEL_FORMAT))).decode("ascii"),
        }

    @staticmethod
    def import_backend():
        import cv2

        return cv2

    def iterall(self, native: bool = False) -> Iterator[Tuple[float, np.ndarray]]:
        while True:
            retval, image = self.cap.read()
            offset = self.cap.get(self.cv2.CAP_PROP_POS_FRAMES)
            if retval:
                if not native:
                    image = self.cv2.cvtColor(image, self.cv2.COLOR_BGR2RGB)
                yield self.time_to_seconds(offset), image
            else:
                break

    def show(self, title: str = "iter_video") -> Iterator[np.ndarray]:
        """Show video. Quit using key 'q'"""

        try:
            for _time, image in self.iterall(native=True):
                yield image
                self.cv2.imshow(title, image)
                if self.cv2.waitKey(1) & 0xFF == ord("q"):
                    return
        finally:
            self.cv2.destroyAllWindows()

    def time_to_seconds(self, offset: int) -> float:
        return offset / self.meta["fps"]

    def _get_frame(self, offset: int, native: bool = False) -> Tuple[float, np.ndarray]:
        self.cap.set(self.cv2.CAP_PROP_POS_FRAMES, offset)

        ret, frame = self.cap.read()
        if ret:
            if not native:
                frame = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
            return self.time_to_seconds(offset), frame
        else:
            raise NoGoodFrame("Could not find good frame")

    def _frame_to_file(self, frame: np.ndarray, outpath: Path) -> None:
        is_success: bool
        im_buf: np.ndarray

        is_success, im_buf = self.cv2.imencode(outpath.suffix, frame)
        assert is_success
        im_buf.tofile(fspath(outpath))  # cv2.imwrite doesn't handle unicode paths correctly

    def close(self) -> None:
        self.cap.release()


def object_attributes(obj):
    def inner():
        for attr in dir(obj):
            val = getattr(obj, attr)
            if not callable(val):
                yield attr, val

    return dict(inner())


class AvVideo(VideoBase):
    vcc_attrs = [
        "coded_height",
        "coded_width",
        "display_aspect_ratio",
        "encoded_frame_count",
        "format",
        "framerate",
        "has_b_frames",
        "height",
        "pix_fmt",
        "reformatter",
        "sample_aspect_ratio",
        "width",
    ]

    def __init__(self, path: Union[str, PathLike], videostream: int = 0) -> None:
        self.av = self.import_backend()

        if isinstance(path, PathLike):
            path = fspath(path)

        try:
            self.container = self.av.open(path, "r")
        except self.av.error.InvalidDataError:
            raise BadFile(f"Cannot open {path}")

        # why was this here in the first place?
        # if self.container.format.name == "matroska,webm":
        #     raise BadFile("Matroska files are currently not supported :(")

        self.vstream = self.container.streams.video[videostream]
        self.vstream.thread_type = "AUTO"

        duration = timedelta(seconds=self.container.duration / self.av.time_base)

        vcc = self.vstream.codec_context
        vcc = {attr: getattr(vcc, attr) for attr in self.vcc_attrs}
        del vcc["format"]

        vcc["average_rate"] = getattr(self.vstream, "average_rate", None)  # for av>=10.0.0

        self.native_duration = self.vstream.duration  # exclusive
        self.time_base = self.vstream.time_base

        if not self.native_duration:  # if stream duration is not available, use container duration
            self.native_duration = self.container.duration
            self.time_base = Fraction(1, self.av.time_base)
            logger.debug("Using container instead of video stream duration")

        if not self.native_duration:
            raise BadFile(f"Cannot open {path}")

        # what to do with self.vstream.start_time?

        self.meta = {
            "width": vcc["width"],
            "height": vcc["height"],
            "duration": duration,  # container duration in seconds
            "fps": vcc["framerate"] or vcc["average_rate"],
            "sample_aspect_ratio": vcc["sample_aspect_ratio"] or Fraction(1, 1),
            "display_aspect_ratio": vcc["display_aspect_ratio"] or Fraction(vcc["width"], vcc["height"]),
            "format": vcc["pix_fmt"],
            # "container_bit_rate": self.container.bit_rate,
        }

    @staticmethod
    def import_backend():
        import av

        return av

    def iterall(self, native: bool = False) -> Iterator[Tuple[float, np.ndarray]]:
        for vframe in self.container.decode(self.vstream):  # can raise
            if native:
                frame = vframe
            else:
                frame = vframe.to_ndarray(format="rgb24")
            yield vframe.time, frame

    def _get_frame(self, offset: int, native: bool = False) -> Tuple[float, np.ndarray]:
        # if the stream duration could not be read, convert the offset from container time_base to stream time_base
        offset_in_corrected_time_base = int(offset * self.time_base / self.vstream.time_base)

        for _i in range(1):  # trying x times to find good frames
            try:
                self.container.seek(
                    offset_in_corrected_time_base, backward=True, any_frame=False, stream=self.vstream
                )  # this can silently fail for broken files
            except self.av.error.PermissionError:
                raise NoKeyFrame(f"Failed to seek to {offset} of {self.container.duration}.")

            try:
                for vframe in self.container.decode(self.vstream):  # can raise
                    if not vframe.is_corrupt:
                        logger.debug(
                            "Grabbing frame at %.03fs from seek offset %.03fs", vframe.time, offset * self.time_base
                        )

                        if native:
                            frame = vframe
                        else:
                            frame = vframe.to_ndarray(format="rgb24")

                        return vframe.time, frame

                    logger.debug(
                        "Skipping corrupt frame at %.03fs from seek offset %.03fs", vframe.time, offset * self.time_base
                    )

            except (self.av.error.InvalidDataError, self.av.error.ValueError) as e:
                logger.warning(
                    "Skipping corrupt container position at seek offset %.03fs: %s", offset * self.time_base, e
                )
                offset += int(self.time_base.denominator / self.meta["fps"])
            else:
                raise NoGoodFrame("Could not find good frame after decoding full file")

        raise NoGoodFrame("Could not find good frame after trying various offsets")

    def _frame_to_file(self, frame: "VideoFrame", outpath: Path) -> None:
        frame.to_image(fspath(outpath))

    def close(self) -> None:
        self.container.close()


def grab_pic(
    inpath: Union[str, PathLike],
    outpath: Path,
    pos: Union[float, Sequence[float]] = 0.5,
    overwrite: bool = False,
    backend: str = "cv",
) -> None:
    vf: VideoBase

    if backend == "av":
        vf = AvVideo(inpath)
    elif backend == "cv":
        vf = CvVideo(inpath)
    else:
        raise ValueError(f"Unsupported backend: {backend}")

    try:
        outpath.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(pos, float):
            _raise_exists(outpath, overwrite)
            vf.save_frame_to_file(pos, outpath)
        elif isinstance(pos, list):
            for i, p in enumerate(pos):
                outpathseq = outpath.with_suffix(f".{i}{outpath.suffix}")
                _raise_exists(outpathseq, overwrite)
                vf.save_frame_to_file(p, outpathseq)
        else:
            raise TypeError("pos")

    finally:
        vf.close()


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()

    with CvVideo(args.path) as vf:
        print(vf.meta)

    with AvVideo(args.path) as vf:
        print(vf.meta)
