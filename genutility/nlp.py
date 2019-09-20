from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import viewkeys
from builtins import sum

from itertools import islice
from typing import TYPE_CHECKING

from .file import PathOrTextIO

if TYPE_CHECKING:
	from typing import Dict, TextIO, Union

def load_freqs(fname, normalize=False, limit=None):
	# type: (Union[str, TextIO], ) -> Dict[str, int]

	with PathOrTextIO(fname, "rt", encoding="utf-8") as fin:
		freqs = dict()

		for line in islice(fin, limit):
			word, count = line.split()
			freqs[word] = int(count)

	if normalize:
		total = sum(viewkeys(freqs))

		for word, count in viewitems(freqs):
			freqs[word] = count / total

	return freqs
