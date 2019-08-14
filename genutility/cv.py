from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

import cv2

if TYPE_CHECKING:
	from typing import Union, Iterator
	import numpy as np

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
