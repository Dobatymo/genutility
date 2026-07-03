import re

import mistune
from mistune.inline_parser import AUTO_EMAIL

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


def _parse_auto_link(inline, m, state):
    text = m.group(0)
    if state.in_link:
        inline.process_text(text, state)
    else:
        state.append_token({"type": "auto_link", "raw": text[1:-1] if text.startswith("<") else text})
    return m.end()


def _parse_auto_email(inline, m, state):
    text = m.group(0)
    if state.in_link:
        inline.process_text(text, state)
    else:
        state.append_token({"type": "auto_email", "raw": text[1:-1]})
    return m.end()


def _plaintext_links(md):
    md.inline.register("auto_link", None, _parse_auto_link)
    # Mistune's AUTO_EMAIL is the HTML Standard valid e-mail address regex:
    # https://html.spec.whatwg.org/multipage/input.html#valid-e-mail-address
    md.inline.register("auto_email", AUTO_EMAIL, _parse_auto_email)
    md.inline.register("url_link", None, _parse_auto_link)


_MARKDOWN_PLUGINS = ("strikethrough", "superscript", "table", "url")


class PlaintextRenderer(mistune.BaseRenderer):
    """Render Markdown tokens to plain text.

    This is lossy: it removes Markdown syntax, prefers link/image titles when
    present, replaces URL/email autolinks with "<URL>"/"<EMAIL>", skips table
    headers, and keeps the contents of superscript spans.
    """

    _raw_tokens = {"block_code", "block_html", "codespan", "inline_html", "text"}
    _children_tokens = {
        "block_quote",
        "block_text",
        "emphasis",
        "strikethrough",
        "strong",
        "superscript",
        "table",
        "table_body",
        "table_cell",
        "table_row",
    }
    _newline_tokens = {"linebreak", "softbreak", "thematic_break"}

    def render_token(self, token, state):
        token_type = token["type"]

        if token_type in self._raw_tokens:
            return token.get("raw", "")
        if token_type in self._children_tokens:
            return self.render_tokens(token["children"], state)
        if token_type in self._newline_tokens:
            return "\n"
        if token_type in {"heading", "paragraph"}:
            return self.render_tokens(token["children"], state) + "\n\n"
        if token_type == "list":  # nosec B105
            return self.render_tokens(token["children"], state) + "\n"
        if token_type == "list_item":  # nosec B105
            return self.render_tokens(token["children"], state) + " "
        if token_type == "table_head":  # nosec B105
            return ""
        if token_type == "auto_link":  # nosec B105
            return "<URL>"
        if token_type == "auto_email":  # nosec B105
            return "<EMAIL>"
        if token_type in {"image", "link"}:
            attrs = token.get("attrs") or {}
            return attrs.get("title") or self.render_tokens(token["children"], state)
        if token_type == "blank_line":  # nosec B105
            return ""

        raise AttributeError(f'No renderer "{token_type}"')


def unescape(s: str) -> str:
    return s.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


md_text = mistune.create_markdown(
    renderer=PlaintextRenderer(),
    plugins=(*_MARKDOWN_PLUGINS, _plaintext_links),
)


def markdown2plaintext(s: str) -> str:
    """Converts markdown to plaintext."""

    return md_text(unescape(s)).strip()


md_html = mistune.create_markdown(renderer="html", plugins=_MARKDOWN_PLUGINS)


def markdown2html(s: str) -> str:
    """Converts markdown to HTML and strips surrounding <p> tags."""

    html = md_html(s).strip()
    if html.count("<p>") == 1 and html.count("</p>") == 1:
        return html[3:-4]  # assume p tags wrap everything
    else:
        return html
