from __future__ import generator_stop

import os.path

""" This module is to avoid circular imports.
	It should avoid any dependencies apart from the standard library.
"""

def entrysuffix(entry):
	# type: (MyDirEntryT, ) -> str

	return os.path.splitext(entry.name)[1]

