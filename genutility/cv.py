from __future__ import generator_stop

import logging
from typing import TYPE_CHECKING, Iterator, Union

import cv2
import numpy as np

if TYPE_CHECKING:
    import wx  # noqa: F401

logger = logging.getLogger(__name__)


def wx_to_cv_image(wximage: "wx.Image") -> np.ndarray:

    buf = wximage.GetDataBuffer()
    arr = np.asarray(buf, dtype=np.uint8)

    return np.reshape(arr, (wximage.Height, wximage.Width, 3))[:, :, ::-1]  # RGB => BGR


def grayscale(cvimg: np.ndarray) -> np.ndarray:

    return cv2.cvtColor(cvimg, cv2.COLOR_RGB2GRAY)


def iter_video(input: Union[str, int] = 0, show: bool = False) -> Iterator[np.ndarray]:

    cap = cv2.VideoCapture(input)
    logger.debug("Reading video using %s backend", cap.getBackendName())

    try:
        while True:
            retval, image = cap.read()
            if retval:
                yield image
            else:
                break

            if show:
                cv2.imshow("iter_video", image)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    return
    finally:
        cap.release()
        if show:
            cv2.destroyAllWindows()
