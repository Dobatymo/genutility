from os import PathLike, fspath
from pathlib import Path
from typing import Any, Dict, Union

from pymediainfo import MediaInfo, Track


class MediaInfoHelper:
    def __init__(self, path: Union[str, Path]) -> None:
        if isinstance(path, PathLike):
            path = fspath(path)

        self.mi = MediaInfo.parse(path)

    def audio_duration(self) -> float:
        """Returns audio duration in seconds."""

        for track in self.mi.tracks:
            if track.track_type == "Audio":
                return track.duration / 1000.0

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

    def first_track(self, track_type: str) -> Track:
        for track in self.mi.tracks:
            if track.track_type == track_type:
                return track

        raise LookupError("Video track not available")

    def is_vfr(self) -> bool:
        for track in self.mi.tracks:
            if track.track_type == "Video":
                return track.frame_rate_mode == "VFR"

        return False

    def meta_info(self) -> Dict[str, Any]:
        for track in self.mi.tracks:
            if track.track_type == "General":
                if track.duration is None:
                    duration = None
                else:
                    duration = track.duration / 1000.0

                return {
                    "title": track.title,  # track_name
                    "performer": track.performer,
                    "album": track.album,
                    "track-position": track.track_name_position,
                    "duration": duration,
                    "date": track.Recorded_Date,
                }

        raise LookupError("Meta data not available")
