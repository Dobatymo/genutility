from __future__ import absolute_import, division, print_function, unicode_literals


def _filemanager_cmd_mac(path):
	# type: (str, ) -> str

	return 'open -R "{}"'.format(path)
