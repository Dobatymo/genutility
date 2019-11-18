from __future__ import absolute_import, division, print_function, unicode_literals

import os

import cv2

def grab_pic(inpath, outpath, pos=0.5, overwrite=False):
	# type: (str, str, float) -> None

	if not overwrite and os.path.exists(outpath):
		raise RuntimeError("File already exists")

	cap = cv2.VideoCapture(inpath)

	try:
		total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

		cap.set(cv2.CAP_PROP_POS_FRAMES, int(pos * total_frames))

		# reading from frame
		ret, frame = cap.read()

		if ret:
			cv2.imwrite(outpath, frame)
		else:
			raise RuntimeError("Cannot read video")

	finally:
		cap.release()
