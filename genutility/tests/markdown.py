from genutility.markdown import markdown2html, markdown2plaintext, markdown_urls
from genutility.test import MyTestCase, parametrize


class MarkdownTest(MyTestCase):
    @parametrize(  # see: https://mathiasbynens.be/demo/url-regex
        ("http://foo.com/blah_blah", True),
        ("http://foo.com/blah_blah/", True),
        ("http://foo.com/blah_blah_(wikipedia)", True),
        ("http://foo.com/blah_blah_(wikipedia)_(again)", True),
        ("http://www.example.com/wpstyle/?p=364", True),
        ("https://www.example.com/foo/?bar=baz&inga=42&quux", True),
        # ('http://✪df.ws/123', True),
        # ('http://userid:password@example.com:8080', True),
        # ('http://userid:password@example.com:8080/', True),
        # ('http://userid@example.com', True),
        # ('http://userid@example.com/', True),
        # ('http://userid@example.com:8080', True),
        # ('http://userid@example.com:8080/', True),
        # ('http://userid:password@example.com', True),
        # ('http://userid:password@example.com/', True),
        # ('http://142.42.1.1/', True),
        # ('http://142.42.1.1:8080/', True),
        # ('http://➡.ws/䨹', True),
        # ('http://⌘.ws', True),
        # ('http://⌘.ws/', True),
        ("http://foo.com/blah_(wikipedia)#cite-1", True),
        ("http://foo.com/blah_(wikipedia)_blah#cite-1", True),
        # ('http://foo.com/unicode_(✪)_in_parens', True),
        ("http://foo.com/(something)?after=parens", True),
        # ('http://☺.damowmow.com/', True),
        ("http://code.google.com/events/#&product=browser", True),
        ("http://j.mp", True),
        ("ftp://foo.bar/baz", True),
        ("http://foo.bar/?q=Test%20URL-encoded%20stuff", True),
        # ('http://مثال.إختبار', True),
        # ('http://例子.测试', True),
        # ('http://उदाहरण.परीक्षा', True),
        # ("http://-.~_!$&'()*+,;=:%40:80%2f::::::@example.com", True),
        ("http://1337.net", True),
        ("http://a.b-c.de", True),
        ("http://223.255.255.254", True),
        # ('https://foo_bar.example.com/', True),
        ("http://.", False),
        ("http://..", False),
        ("http://../", False),
        ("http://?", False),
        ("http://??", False),
        ("http://??/", False),
        ("http://#", False),
        ("http://##", False),
        ("http://##/", False),
        ("http://foo.bar?q=Spaces should be encoded", False),
        ("//", False),
        ("//a", False),
        ("///a", False),
        ("///", False),
        ("http:///a", False),
        ("foo.com", False),
        ("rdar://1234", False),
        ("h://test", False),
        ("http:// shouldfail.com", False),
        (":// should fail", False),
        ("http://foo.bar/foo(bar)baz quux", False),
        ("ftps://foo.bar/", False),
        # ("http://-error-.invalid/", False),
        # ("http://a.b--c.de/", False), # shouldnt that be correct?
        # ("http://-a.b.co", False),
        # ("http://a.b-.co", False),
        ("http://0.0.0.0", False),
        # ("http://10.1.1.0", False),
        # ("http://10.1.1.255", False),
        # ("http://224.1.1.1", False),
        ("http://1.1.1.1.1", False),
        # ("http://123.123.123", False),
        ("http://3628126748", False),
        # ("http://.www.foo.bar/", False),
        ("http://www.foo.bar./", False),
        ("http://.www.foo.bar./", False),
        # ("http://10.1.1.1", False),
        # ("http://10.1.1.254", False)
    )
    def test_markdown_urls(self, url, valid):
        truth = f"asd <{url}> qwe"

        result = markdown_urls(f"asd {url} qwe")
        if valid:
            self.assertEqual(truth, result)
        else:
            self.assertNotEqual(truth, result)

        result = markdown_urls(f"asd <{url}> qwe")
        if valid:
            self.assertEqual(truth, result)

    @parametrize(
        ("http://foo.com", "<http://foo.com>"),
        ("asd http://foo.com", "asd <http://foo.com>"),
        ("http://foo.com qwe", "<http://foo.com> qwe"),
        ("asd http://foo.com qwe", "asd <http://foo.com> qwe"),
        ("http://foo.com.", "<http://foo.com>."),
        ("asd http://foo.com.", "asd <http://foo.com>."),
        ("http://foo.com. qwe", "<http://foo.com>. qwe"),
        ("asd http://foo.com. qwe", "asd <http://foo.com>. qwe"),
        ("asd https://sub2.sub1.domain.com/asd/qwe#zxc.", "asd <https://sub2.sub1.domain.com/asd/qwe#zxc>."),
        ("https://sub.domain/dir/1 https://sub.domain/dir/2", "<https://sub.domain/dir/1> <https://sub.domain/dir/2>"),
    )
    def test_markdown_urls_2(self, text, truth):
        result = markdown_urls(text)
        self.assertEqual(truth, result)

    def test_markdown2plaintext(self):
        value = """# heading h1

heading h2
------------

this is a *paragraph*.
this is &lt;still&gt; the ~~same~~ **paragraph**.

this is a _new_ __paragraph__.

* Red
* Green

http://en.wikipedia.org
[Wikipedia](http://en.wikipedia.org)
[Wikipedia](http://en.wikipedia.org "wiki text")

"""

        truth = """heading h1

heading h2

this is a paragraph.
this is <still> the same paragraph.

this is a new paragraph.

Red Green 
<URL>
Wikipedia
wiki text"""  # noqa: W291 # keep the space after Red Green

        result = markdown2plaintext(value)
        self.assertEqual(result, truth)

    def test_markdown2html(self):
        value = """1. Harry Potter and the Philosopher's Stone (2001)
2. Harry Potter and the Chamber of Secrets (2002)
3. Harry Potter and the Prisoner of Azkaban (2004)
4. Harry Potter and the Goblet of Fire (2005)
5. Harry Potter and the Order of the Phoenix (2007)
6. Harry Potter and the Half-Blood Prince (2009)
7. Harry Potter and the Deathly Hallows - Part 1 (2010)
8. Harry Potter and the Deathly Hallows - Part 2 (2011)"""

        truth = """<ol>
<li>Harry Potter and the Philosopher's Stone (2001)</li>
<li>Harry Potter and the Chamber of Secrets (2002)</li>
<li>Harry Potter and the Prisoner of Azkaban (2004)</li>
<li>Harry Potter and the Goblet of Fire (2005)</li>
<li>Harry Potter and the Order of the Phoenix (2007)</li>
<li>Harry Potter and the Half-Blood Prince (2009)</li>
<li>Harry Potter and the Deathly Hallows - Part 1 (2010)</li>
<li>Harry Potter and the Deathly Hallows - Part 2 (2011)</li>
</ol>"""

        result = markdown2html(value)
        self.assertEqual(result, truth)


if __name__ == "__main__":
    import unittest

    unittest.main()
