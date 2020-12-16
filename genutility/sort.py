from __future__ import generator_stop

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

def selection_sort_min(seq):
	#inplace, unstable

	n = len(seq)
	for i in range(n-1):
		m = argmin(seq, i, n)
		if m != i:
			seq[i], seq[m] = seq[m], seq[i]

def selection_sort_max(seq):
	#inplace, unstable

	for n in range(len(seq)-1, 0, -1):
		m = argmax(seq[:n+1])
		if m != n:
			seq[m], seq[n] = seq[n], seq[m]

def selection_sort_ll(seq):
	# inplace, stable, on linked lists
	raise NotImplementedError
