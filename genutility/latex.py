def escape_latex(text):
    chars = "%$_&#}{"
    for char in chars:
        text = text.replace(char, "\\" + char)
    return text
