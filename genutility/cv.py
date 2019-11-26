from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
	from typing import Union, Iterator
	import wx

def wx_to_cv_image(wximage):
	# type (wx.Image, ) -> np.ndarray

	buf = wximage.GetDataBuffer()
	arr = np.asarray(buf, dtype=np.uint8)

	return np.reshape(arr, (wximage.Height, wximage.Width, 3))[:,:,::-1] #RGB => BGR

def grayscale(cvimg):
	# type: (np.ndarray, ) -> np.ndarray

	return cv2.cvtColor(cvimg, cv2.COLOR_RGB2GRAY)

def iter_video(input=0, show=False):
	# type: (Union[str, int], bool) -> Iterator[np.ndarray]

	cap = cv2.VideoCapture(input)

	try:
		while True:
			retval, image = cap.read()
			if retval:
				yield image
			else:
				break
			
			if show:
				cv2.imshow('iter_video', image)
				if cv2.waitKey(1) & 0xFF == ord('q'):
					return
	finally:
		cap.release()
		if show:
			cv2.destroyAllWindows()
