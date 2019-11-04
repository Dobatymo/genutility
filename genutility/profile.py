from __future__ import absolute_import, division, print_function, unicode_literals

""" Scripts using line_profiler.profile can import this to be able to run unmodified
	without the profiler present.
"""

try:
	profile
except NameError:
	def profile(func):
		return func
