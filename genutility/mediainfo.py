from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

from pymediainfo import MediaInfo

from .compat.os import PathLike, fspath

if TYPE_CHECKING:
	from typing import Union

	from pymediainfo import Track

	from .compat.pathlib import Path

class MediaInfoHelper(object):

	def __init__(self, path):
		# type: (Union[str, Path], ) -> None

		if isinstance(path, PathLike):
			path = fspath(path)

		self.mi = MediaInfo.parse(path)

	def audio_duration(self):
		# type: () -> float

		""" Returns audio duration in seconds. """

		for track in self.mi.tracks:
			if track.track_type == "Audio":
				return track.duration / 1000.

		raise LookupError("Audio duration not available")

	@property
	def general(self):
		return self.first_track("General")

	@property
	def video(self):
		return self.first_track("Video")

	@property
	def audio(self):
		return self.first_track("Audio")

	@property
	def text(self):
		return self.first_track("Text")

	def first_track(self, track_type):
		# type: (str, ) -> Track

		for track in self.mi.tracks:
			if track.track_type == track_type:
				return track

		raise LookupError("Video track not available")

	def is_vfr(self):
		for track in self.mi.tracks:
			if track.track_type == "Video":
				return track.frame_rate_mode == "VFR"

		return False

	def meta_info(self):

		for track in self.mi.tracks:
			if track.track_type == "General":

				if track.duration is None:
					duration = None
				else:
					duration = track.duration / 1000.

				return {
					"title": track.title, # track_name
					"performer": track.performer,
					"album": track.album,
					"track-position": track.track_name_position,
					"duration": duration,
					"date": track.Recorded_Date,
				}

		raise LookupError("Meta data not available")
