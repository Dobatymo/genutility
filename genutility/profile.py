"""Scripts using line_profiler.profile can import this to be able to run unmodified
without the profiler present.
"""

import logging

logger = logging.getLogger(__name__)

try:
    profile = profile  # bind so it can be imported  # noqa: PLW0127
    logger.info("Running profiler")

except NameError:

    def profile(func):
        return func
