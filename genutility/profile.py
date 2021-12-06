from __future__ import generator_stop

""" Scripts using line_profiler.profile can import this to be able to run unmodified
    without the profiler present.
"""
import logging

try:
    profile = profile  # bind so it can be imported
    logging.info("Running profiler")

except NameError:

    def profile(func):
        return func
