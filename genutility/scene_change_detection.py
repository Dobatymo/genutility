from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import map

from typing import TYPE_CHECKING

import numpy as np

from .image import image_block_histogram, image_histogram
from .iter import pairwise
from .numpy import histogram_correlation

if TYPE_CHECKING:
	pass

def scene_change_detection_histogram_correlation(images):

	""" Based on: 'Histogram Correlation for Video Scene Change Detection'. Algorithm described
		in paper is incomplete. It only mentions 'almost constant', 'not constant' and 'change is sharp'
		behaviour of the correlation. A real implementation would need to define a sliding window
		based derivative and threshold values for said derivatives.
	"""

	it = iter(images)
	hist_rf = image_histogram(np.array(next(it)))

	for image in it:
		hist_i = image_histogram(np.array(image))
		yield histogram_correlation(hist_rf, hist_i)

def scene_change_detection_block_histogram(images):
	it = iter(images)

	def get_means_of_block_histograms(arr):
		hist = image_block_histogram(arr, 16, 16)
		#print(hist.shape)
		#print(hist.tolist())
		means = np.mean(hist, axis=-1)
		print(means)
		return means

	for means1, means2 in pairwise(map(get_means_of_block_histograms, it)):
		# difference of means
		diffs = np.abs(means1 - means2)
		yield diffs

def proc(hist, lambda_=200):
	delta = 0.5
	DS = np.sqrt(2.)/2.*np.sum(np.abs(hist - hist.T), axis=(-2,-1))
	B = DS > lambda_
	BC = np.mean(unpack(B, 2, 2), axis=-1) > delta # noqa: F821

	raise RuntimeError("Unfinished")

def test_scene_change_detection_histogram_correlation():
	from .cv import iter_video

	images = iter_video()
	for score in scene_change_detection_histogram_correlation(images):
		print(score)

def test_scene_change_detection_block_histogram():
	from .cv import iter_video

	images = iter_video()
	for diffs in scene_change_detection_block_histogram(images):
		print(diffs.tolist())

if __name__ == "__main__":
	from PIL import Image

	#test_image_histogram_gray()
	#test_scene_change_detection_histogram_correlation()
	test_scene_change_detection_block_histogram()
