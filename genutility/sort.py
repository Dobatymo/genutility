from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

from .math import argmax, argmin

if TYPE_CHECKING:
	from typing import MutableSequence

def bubble_sort(seq):
	# type: (MutableSequence, ) -> None

	""" Slightly optimized version of stable bubble sort. Sorts input `seq` in place. """

	n = len(seq)
	while True:
		newn = 1
		for i in range(1, n):
			if seq[i-1] > seq[i]:
				seq[i-1], seq[i] = seq[i], seq[i-1]
				newn = i
		if newn == 1:
			break
		n = newn

def selection_sort_min(l):
	#inplace, unstable

	n = len(l)
	for i in range(n-1):
		m = argmin(l, i, n)
		if m != i:
			l[i], l[m] = l[m], l[i]

def selection_sort_max(l):
	#inplace, unstable

	for n in range(len(l)-1, 0, -1):
		m = argmax(l[:n+1])
		if m != n:
			l[m], l[n] = l[n], l[m]

def selection_sort_ll(l):
	# inplace, stable, on linked lists
	raise NotImplementedError
