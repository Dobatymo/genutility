from __future__ import generator_stop


def _filemanager_cmd_mac(path):
	# type: (str, ) -> str

	return 'open -R "{}"'.format(path)
