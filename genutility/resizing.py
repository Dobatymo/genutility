from __future__ import absolute_import, division, print_function, unicode_literals

from itertools import islice
from math import cos, pi, sin

import cv2
import numpy as np
from sklearn.cluster import MeanShift

from .math import degree_to_rad, inf
from .rand import rgb_colors

## UNFINISHED
## BASED ON: Resizing by Symmetry-Summarization (2010)

def MSER_draw(img, boxes, centers, major_v, minor_v, labels):

	center_int = centers.astype(int)
	major_int = (centers + major_v).astype(int)
	minor_int = (centers + minor_v).astype(int)

	labels_unique = np.unique(labels)
	n_clusters = len(labels_unique)
	colors = list(islice(rgb_colors(), n_clusters))
	print("{} clusters found".format(n_clusters))

	for box, label in zip(boxes, labels):
		cv2.ellipse(img, box, colors[label], 2)

	for c, ma, mi in zip(center_int, major_int, minor_int):
		cv2.line(img, tuple(c), tuple(ma), (0, 255, 0), 2)
		cv2.line(img, tuple(c), tuple(mi), (0, 255, 0), 2)

def MSER_boxes(img):
	mser = cv2.MSER_create()

	msers, _ = mser.detectRegions(img)

	return [cv2.fitEllipse(mser) for mser in msers]

def MSER_ellipses(boxes):
	pihalf = pi/2.
	boxes = np.array([(x, y, ma, mi, a) for (x, y), (ma, mi), a in boxes])

	centers = boxes[:,0:2]
	angles = boxes[:,4]*2.*pi/360. # convert degrees to rad

	major_x = boxes[:,2]/2 * np.cos(angles)
	major_y = boxes[:,2]/2 * np.sin(angles)
	major_v = np.stack([major_x, major_y], axis=-1)

	angles += pihalf
	minor_x = boxes[:,3]/2 * np.cos(angles)
	minor_y = boxes[:,3]/2 * np.sin(angles)
	minor_v = np.stack([minor_x, minor_y], axis=-1)

	return (centers, major_v, minor_v)

def MSER(img, show=True):
	boxes = MSER_boxes(img)
	centers, major_v, minor_v = MSER_ellipses(boxes)

	return boxes, centers, major_v, minor_v

def norm(v):
	return np.sqrt(np.sum(v**2, axis=-1))

def shape_dissimmilarity(R_u, R_v, i, j):
	num1 = np.abs(R_u[i] - R_u[j])
	denom1 = max(norm(R_u[i]), norm(R_u[j]))
	
	num2 = np.abs(R_v[i] - R_v[j])
	denom2 = max(norm(R_v[i]), norm(R_v[j]))

	return num1/denom1 + num2/denom2

def appearance_dissimmilarity():
	pass

def symmetry_detection(image, K_c=5):

	#Identifying cells with MSER
	boxes, R_c, R_u, R_v = MSER(image) # {r_i} set of MSERs (2d ellipsis) r_i = (center, major axis, minor axis)

	# Clustering with adaptive mean-shift clustering
	u_norm = norm(R_u)
	v_norm = norm(R_v)
	shapessizes = np.stack([u_norm, v_norm], axis=-1)

	ms = MeanShift()
	labels = ms.fit_predict(shapessizes)

	MSER_draw(image, boxes, R_c, R_u, R_v, labels)
	cv2.imshow('img', image)
	cv2.waitKey()

def diff(v1, v2, tau_v):
	val = abs(v1-v2)/max(norm(v1), norm(v2))
	if val > tau_v:
		return inf
	else:
		return val

if __name__ == "__main__":
	imgpath = "D:\\colloseo.jpg"
	img = cv2.imread(imgpath)
	symmetry_detection(img)
