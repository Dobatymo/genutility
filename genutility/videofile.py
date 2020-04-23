from __future__ import absolute_import, division, print_function, unicode_literals

import logging
from datetime import timedelta
from fractions import Fraction

from .compat.os import PathLike, fspath

#if __debug__:
#	import av
#	import cv2

class NoGoodFrame(Exception):
	pass

class NoKeyFrame(Exception):
	pass

class BadFile(Exception):
	pass

class VideoBase(object):

	single_frame_ratio = 0.5

	def calculate_step(self, time_base, duration):
		# type: (Fraction, int) -> int

		raise NotImplementedError

	def _get_frame(self, offset, rgb=True):
		# type: (int, bool) -> Tuple[float, np.ndarray]

		raise NotImplementedError

	def _yield_frames(self, start, stop, step):
		# type: (int, int, int) -> Iterator[Tuple[float, np.ndarray]]

		""" start, stop, step are in frames """

		for offset in range(start, stop, step):
			try:
				yield self._get_frame(offset)
			except NoKeyFrame as e:
				yield offset, e

	def iterate(self):
		# type: () -> Iterator[Tuple[float, np.ndarray]]

		step = self.calculate_step(self.time_base, self.native_duration)
		if step:
			for tf in self._yield_frames(0, self.native_duration, step):
				yield tf
		else:
			yield self.grab_frame(self.single_frame_ratio) # if only 1 frame is requested, return one from the middle

	def grab_frame(self, pos):
		# type: (float, ) -> np.ndarray

		frametime, frame = self._get_frame(int(self.native_duration * pos))
		return frame

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

		self.native_duration = frame_count
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

	def time_to_seconds(self, frame):
		return frame / self.meta["fps"]

	def _get_frame(self, offset, rgb=True):
		# type: (int, ) -> Tuple[float, np.ndarray]

		self.cap.set(self.cv2.CAP_PROP_POS_FRAMES, offset)

		ret, frame = self.cap.read()
		if ret:
			if rgb:
				frame = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
			return self.time_to_seconds(offset), frame
		else:
			raise NoGoodFrame("Could not find good frame")

	def frame_to_file(self, outpath, frame):
		# type: (Path, np.ndarray) -> None

		self.cv2.imwrite(fspath(outpath), frame)

	def close(self):
		# type: () -> None

		self.cap.release()

class AvVideo(VideoBase):

	vcc_attrs = ["coded_height", "coded_width", "display_aspect_ratio", "encoded_frame_count", "format",
			"framerate", "gop_size", "has_b_frames", "height", "pix_fmt", "reformatter",
			"sample_aspect_ratio", "width"]

	def __init__(self, path, videostream=0):
		# type: (str, int) -> None

		self.av = self.import_backend()

		if isinstance(path, PathLike):
			path = fspath(path)

		self.container = self.av.open(path, "r")

		self.vstream = self.container.streams.video[0]
		self.vstream.thread_type = "AUTO"

		duration = timedelta(seconds=self.container.duration / self.av.time_base)

		vcc = self.vstream.codec_context
		vcc = {attr:getattr(vcc, attr) for attr in self.vcc_attrs}
		del vcc["format"]

		self.native_duration = self.vstream.duration
		if not self.native_duration:
			raise BadFile("Cannot open {}".format(path))

		self.time_base = self.vstream.time_base

		self.meta = {
			"width": vcc["width"],
			"height": vcc["height"],
			"duration": duration,
			"fps": vcc["framerate"],
			"sample_aspect_ratio": vcc["sample_aspect_ratio"] or Fraction(1, 1),
			"display_aspect_ratio": vcc["display_aspect_ratio"] or Fraction(vcc["width"], vcc["height"]),
			"format": vcc["pix_fmt"],
		}

	@staticmethod
	def import_backend():
		import av

		return av

	def _get_frame(self, offset, rgb=True):
		# type: (int, ) -> Tuple[float, np.ndarray]

		try:
			self.container.seek(offset, backward=True, any_frame=False, stream=self.vstream) # this can silently fail for broken files
		except self.av.error.PermissionError:
			raise NoKeyFrame("Failed to seek to {} of {}.".format(offset, self.container.duration))

		for vframe in self.container.decode(self.vstream): # can raise av.error.InvalidDataError
			if not vframe.is_corrupt:
				logging.debug("Grabbing frame at %.02fs (%d)", vframe.time, offset)

				if rgb:
					frame = vframe.to_rgb().to_ndarray()
				else:
					frame = vframe.to_ndarray()

				return vframe.time, frame

			logging.debug("Skipping corrupt frame at %.02fs (%d)", vframe.time, offset)

		raise NoGoodFrame("Could not find good frame")

	def frame_to_file(self, outpath, frame):
		# type: (Path, np.ndarray) -> None

		from PIL import Image
		Image.fromarray(frame).save(fspath(outpath))

	def close(self):
		# type: () -> None

		self.container.close()

def grab_pic(inpath, outpath, pos=0.5, overwrite=False, backend="av"):
	# type: (Union[str, Path], Path, float) -> None

	if not overwrite and outpath.exists():
		raise RuntimeError("File already exists")

	if backend == "av":
		vf = AvVideo(inpath)
	elif backend == "cv":
		vf = CvVideo(inpath)
	else:
		raise InputError("Unsupported backend: {}".format(backend))

	try:
		outpath.parent.mkdir(parents=True, exist_ok=True)

		frame = vf.grab_frame(pos)
		print(frame.shape)
		vf.frame_to_file(outpath, frame)
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
