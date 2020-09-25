from __future__ import absolute_import, division, print_function, unicode_literals


def escape_latex(text):
	chars = "%$_&#}{"
	for char in chars:
		text = text.replace(char, "\\"+char)
	return text
