from __future__ import generator_stop


def escape_latex(text):
    chars = "%$_&#}{"
    for char in chars:
        text = text.replace(char, "\\" + char)
    return text
