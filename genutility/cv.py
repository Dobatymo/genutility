from typing import TYPE_CHECKING, Iterator, Union

import cv2
import numpy as np

from videofile import CvVideo

if TYPE_CHECKING:
    import wx  # noqa: F401


def wx_to_cv_image(wximage: "wx.Image") -> np.ndarray:
    buf = wximage.GetDataBuffer()
    arr = np.asarray(buf, dtype=np.uint8)

    return np.reshape(arr, (wximage.Height, wximage.Width, 3))[:, :, ::-1]  # RGB => BGR


def grayscale(cvimg: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(cvimg, cv2.COLOR_RGB2GRAY)


def iter_video(input: Union[str, int] = 0, show: bool = False) -> Iterator[np.ndarray]:
    with CvVideo(input) as video:
        if show:
            for _time, image in video.show():
                yield image
        else:
            for _time, image in video.iterall(native=True):
                yield image
