import re

import mistune

_markdown_newline_pat = re.compile(r"[^\n]\n[^\n]")


def _markdown_newline_func(x: re.Match) -> str:
    return x.group(0).replace("\n", "  \n")


def markdown_newline(s: str) -> str:
    """Convert newlines to markdown linebreaks."""

    return _markdown_newline_pat.sub(_markdown_newline_func, s)


_markdown_urls_pat = re.compile(
    r"(?<![\<])((?:http|https|ftp):\/\/[a-zA-Z0-9\-\.]+\.[a-zA-Z0-9]{2,}(?:\/[\:\/\?\#\[\]\@\!\$\&\'\(\)\*\+\;\=a-zA-Z0-9\-\._\~\%]*)?)(?![\>])"
)


def markdown_urls(s: str, ignore_trailing_dot: bool = True) -> str:
    """Converts text with URLs to text with markdown formatted URLs.
    markdown_urls("Visit https://google.com") -> "Visit <https://google.com>"
    This function is idempotent, which means that it will not convert URLs which are already in the correct format.
    markdown_urls("Visit <https://google.com>") -> "Visit <https://google.com>"
    """

    def markdown_dotfix(m):
        (url,) = m.groups()
        if ignore_trailing_dot and url.endswith("."):
            return f"<{url[:-1]}>."
        else:
            return f"<{url}>"

    # return _markdown_urls_pat.sub(r"<\1>", s)
    return _markdown_urls_pat.sub(markdown_dotfix, s)


class PlaintextRenderer(mistune.Renderer):
    """Mistune renderer to strip all markdown formatting and only return plaintext."""

    def block_code(self, code, lang=None):
        return code

    def block_quote(self, text):
        return text

    def block_html(self, html):
        return html

    def header(self, text, level, raw=None):
        return text + "\n\n"

    def hrule(self):
        return "\n"

    def list(self, body, ordered=True):
        return body + "\n"

    def list_item(self, text):
        return text + " "

    def paragraph(self, text):
        return text + "\n\n"

    def table(self, header, body):
        return body

    def table_row(self, content):
        return content

    def table_cell(self, content, **flags):
        return content

    # superscript is not supported!?

    def autolink(self, link, is_email=False):
        if is_email:
            return "<EMAIL>"
        else:
            return "<URL>"

    def codespan(self, text):
        return text

    def double_emphasis(self, text):
        return text

    def emphasis(self, text):
        return text

    def image(self, src, title, text):
        # text: alt attribute

        if title:
            return title
        return text

    def linebreak(self):
        return "\n"

    def newline(self):
        return "\n"

    def link(self, link, title, text):
        # link: href attribute
        if title:
            return title
        return text

    def strikethrough(self, text):
        return text

    def text(self, text):
        return text

    def inline_html(self, html):
        return html

    def escape(self, text):
        return text


def unescape(s: str) -> str:
    return s.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


md_text = mistune.Markdown(renderer=PlaintextRenderer())


def markdown2plaintext(s: str) -> str:
    """Converts markdown to plaintext."""

    return md_text.render(unescape(s)).strip()


md_html = mistune.Markdown(renderer=mistune.Renderer())


def markdown2html(s: str) -> str:
    """Converts markdown to HTML and strips surrounding <p> tags."""

    html = md_html.render(s).strip()
    if html.count("<p>") == 1 and html.count("</p>") == 1:
        return html[3:-4]  # assume p tags wrap everything
    else:
        return html
