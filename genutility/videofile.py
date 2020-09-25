from __future__ import absolute_import, division, print_function, unicode_literals

import logging
from datetime import timedelta
from fractions import Fraction
from typing import TYPE_CHECKING

from .compat import FileExistsError
from .compat.os import PathLike, fspath

if TYPE_CHECKING:
	from typing import Any, Iterator, Sequence, Tuple, Union

	import numpy as np

	from av import VideoFrame

	from .compat.pathlib import Path
	WsgiApp = Any

#if __debug__:
#	import av
#	import cv2

logger = logging.getLogger(__name__)

def _raise_exists(outpath, overwrite=False):
	# type: (Path, bool) -> None

	if not overwrite and outpath.exists():
		raise FileExistsError()

class NoGoodFrame(Exception):
	pass

class NoKeyFrame(Exception):
	pass

class BadFile(Exception):
	pass

class VideoBase(object):

	single_frame_ratio = 0.5

	def calculate_offsets(self, time_base, duration):
		# type: (Fraction, int) -> Iterator[int]

		raise NotImplementedError

	def _get_frame(self, offset, native=False):
		# type: (int, bool) -> Tuple[float, np.ndarray]

		raise NotImplementedError

	def _frame_to_file(self, frame, outpath):
		# type: (Any, PathLike) -> None

		raise NotImplementedError

	def iterate(self):
		# type: () -> Iterator[Tuple[float, np.ndarray]]

		for offset in self.calculate_offsets(self.time_base, self.native_duration):
			try:
				yield self._get_frame(offset)
			except NoKeyFrame as e:
				yield offset, e

	def save_frame_to_file(self, pos, outpath):
		# type: (float, PathLike) -> None

		frametime, frame = self._get_frame(int(self.native_duration * pos), native=True)
		self._frame_to_file(frame, outpath)

	def __enter__(self):
		return self

	def __exit__(self, *args):
		self.close()

def fourcc(integer):
	import struct
	return struct.pack("<i", integer)

	# return integer.to_bytes(4, "little") # python 3 only

class CvVideo(VideoBase):

	def __init__(self, path):
		# type: (Union[str, PathLike, int], ) -> None

		self.cv2 = self.import_backend()

		if isinstance(path, PathLike):
			path = fspath(path)

		self.cap = self.cv2.VideoCapture(path)

		frame_width = int(self.cap.get(self.cv2.CAP_PROP_FRAME_WIDTH))
		frame_height = int(self.cap.get(self.cv2.CAP_PROP_FRAME_HEIGHT))
		frame_count = int(self.cap.get(self.cv2.CAP_PROP_FRAME_COUNT))

		pixel_aspect_ratio = Fraction(
			int(self.cap.get(self.cv2.CAP_PROP_SAR_NUM)),
			int(self.cap.get(self.cv2.CAP_PROP_SAR_DEN))
		)

		if pixel_aspect_ratio == 0:
			pixel_aspect_ratio = Fraction(1, 1)

		display_aspect_ratio = pixel_aspect_ratio * Fraction(frame_width, frame_height)

		fps = self.cap.get(self.cv2.CAP_PROP_FPS)
		try:
			duration = timedelta(seconds=frame_count / fps)
		except ZeroDivisionError:
			raise BadFile("Cannot open {}".format(path))

		self.native_duration = frame_count # exclusive
		self.time_base = Fraction(1, 1)
		self.meta = {
			"width": frame_width,
			"height": frame_height,
			"duration": duration, # duration in seconds
			"fps": fps,
			"sample_aspect_ratio": pixel_aspect_ratio,
			"display_aspect_ratio": display_aspect_ratio,
			"format": fourcc(int(self.cap.get(self.cv2.CAP_PROP_CODEC_PIXEL_FORMAT))).decode("ascii"),
		}

	@staticmethod
	def import_backend():
		import cv2

		return cv2

	def time_to_seconds(self, offset):
		# type: (int, ) -> float

		return offset / self.meta["fps"]

	def _get_frame(self, offset, native=False):
		# type: (int, ) -> Tuple[float, np.ndarray]

		self.cap.set(self.cv2.CAP_PROP_POS_FRAMES, offset)

		ret, frame = self.cap.read()
		if ret:
			if not native:
				frame = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
			return self.time_to_seconds(offset), frame
		else:
			raise NoGoodFrame("Could not find good frame")

	def _frame_to_file(self, frame, outpath):
		# type: (np.ndarray, PathLike) -> None

		is_success, im_buf = self.cv2.imencode(outpath.suffix, frame) # type: Tuple[bool, np.ndarray]
		assert is_success
		im_buf.tofile(fspath(outpath)) # cv2.imwrite doesn't handle unicode paths correctly

	def close(self):
		# type: () -> None

		self.cap.release()

def object_attributes(obj):

	def asd():
		for attr in dir(obj):
			val = getattr(obj, attr)
			if not callable(val):
				yield attr, val

	return dict(asd())

class AvVideo(VideoBase):

	vcc_attrs = ["coded_height", "coded_width", "display_aspect_ratio", "encoded_frame_count", "format",
			"framerate", "gop_size", "has_b_frames", "height", "pix_fmt", "reformatter",
			"sample_aspect_ratio", "width"]

	def __init__(self, path, videostream=0):
		# type: (PathLike, int) -> None

		self.av = self.import_backend()

		if isinstance(path, PathLike):
			path = fspath(path)

		try:
			self.container = self.av.open(path, "r")
		except self.av.error.InvalidDataError:
			raise BadFile("Cannot open {}".format(path))

		if self.container.format.name == "matroska,webm":
			raise BadFile("Matroska files are currently not supported :(")

		self.vstream = self.container.streams.video[videostream]
		self.vstream.thread_type = "AUTO"

		duration = timedelta(seconds=self.container.duration / self.av.time_base)

		vcc = self.vstream.codec_context
		vcc = {attr:getattr(vcc, attr) for attr in self.vcc_attrs}
		del vcc["format"]

		self.native_duration = self.vstream.duration # exclusive
		self.time_base = self.vstream.time_base

		if not self.native_duration:
			self.native_duration = self.container.duration
			self.time_base = Fraction(1, self.av.time_base)
			logger.debug("Using container instead of video stream duration")

		if not self.native_duration:
			raise BadFile("Cannot open {}".format(path))

		# what to do with self.vstream.start_time?

		self.meta = {
			"width": vcc["width"],
			"height": vcc["height"],
			"duration": duration,
			"fps": vcc["framerate"],
			"sample_aspect_ratio": vcc["sample_aspect_ratio"] or Fraction(1, 1),
			"display_aspect_ratio": vcc["display_aspect_ratio"] or Fraction(vcc["width"], vcc["height"]),
			"format": vcc["pix_fmt"],
			#"containser_bit_rate": self.container.bit_rate,
		}

	@staticmethod
	def import_backend():
		import av

		return av

	def _get_frame(self, offset, native=False):
		# type: (int, bool) -> Tuple[float, np.ndarray]

		for i in range(1): # trying x times to find good frames
			try:
				self.container.seek(offset, backward=True, any_frame=False, stream=self.vstream) # this can silently fail for broken files
			except self.av.error.PermissionError:
				raise NoKeyFrame("Failed to seek to {} of {}.".format(offset, self.container.duration))

			try:
				for vframe in self.container.decode(self.vstream): # can raise
					if not vframe.is_corrupt:
						logger.debug("Grabbing frame at %.03fs from seek offset %.03fs", vframe.time, offset*self.time_base)

						if native:
							frame = vframe
						else:
							frame = vframe.to_ndarray(format="rgb24")

						return vframe.time, frame

					logger.debug("Skipping corrupt frame at %.03fs from seek offset %.03fs", vframe.time, offset*self.time_base)

			except (self.av.error.InvalidDataError, self.av.error.ValueError) as e:
				logger.warning("Skipping corrupt container position at seek offset %.03fs: %s", offset*self.time_base, e)
				offset += int(self.time_base.denominator / self.meta["fps"])
			else:
				raise NoGoodFrame("Could not find good frame after decoding full file")

		raise NoGoodFrame("Could not find good frame after trying various offsets")

	def _frame_to_file(self, frame, outpath):
		# type: (VideoFrame, Path) -> None

		frame.to_image(fspath(outpath))

	def close(self):
		# type: () -> None

		self.container.close()

def grab_pic(inpath, outpath, pos=0.5, overwrite=False, backend="cv"):
	# type: (Union[str, PathLike], Path, Union[float, Sequence[float]], bool, str) -> None

	if backend == "av":
		vf = AvVideo(inpath)
	elif backend == "cv":
		vf = CvVideo(inpath)
	else:
		raise ValueError("Unsupported backend: {}".format(backend))

	try:
		outpath.parent.mkdir(parents=True, exist_ok=True)

		if isinstance(pos, float):
			_raise_exists(outpath, overwrite)
			vf.save_frame_to_file(pos, outpath)
		elif isinstance(pos, list):
			for i, p in enumerate(pos):
				outpathseq = outpath.with_suffix(".{}{}".format(i, outpath.suffix))
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
