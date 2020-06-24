from __future__ import absolute_import, division, print_function, unicode_literals

from genutility.test import MyTestCase, parametrize
from genutility.markdown import markdown_urls

class MarkdownTest(MyTestCase):

	@parametrize( # see: https://mathiasbynens.be/demo/url-regex
		('http://foo.com/blah_blah', True),
		('http://foo.com/blah_blah/', True),
		('http://foo.com/blah_blah_(wikipedia)', True),
		('http://foo.com/blah_blah_(wikipedia)_(again)', True),
		('http://www.example.com/wpstyle/?p=364', True),
		('https://www.example.com/foo/?bar=baz&inga=42&quux', True),
		#('http://✪df.ws/123', True),
		#('http://userid:password@example.com:8080', True),
		#('http://userid:password@example.com:8080/', True),
		#('http://userid@example.com', True),
		#('http://userid@example.com/', True),
		#('http://userid@example.com:8080', True),
		#('http://userid@example.com:8080/', True),
		#('http://userid:password@example.com', True),
		#('http://userid:password@example.com/', True),
		#('http://142.42.1.1/', True),
		#('http://142.42.1.1:8080/', True),
		#('http://➡.ws/䨹', True),
		#('http://⌘.ws', True),
		#('http://⌘.ws/', True),
		('http://foo.com/blah_(wikipedia)#cite-1', True),
		('http://foo.com/blah_(wikipedia)_blah#cite-1', True),
		#('http://foo.com/unicode_(✪)_in_parens', True),
		('http://foo.com/(something)?after=parens', True),
		#('http://☺.damowmow.com/', True),
		('http://code.google.com/events/#&product=browser', True),
		('http://j.mp', True),
		('ftp://foo.bar/baz', True),
		('http://foo.bar/?q=Test%20URL-encoded%20stuff', True),
		#('http://مثال.إختبار', True),
		#('http://例子.测试', True),
		#('http://उदाहरण.परीक्षा', True),
		#("http://-.~_!$&'()*+,;=:%40:80%2f::::::@example.com", True),
		('http://1337.net', True),
		('http://a.b-c.de', True),
		('http://223.255.255.254', True),
		#('https://foo_bar.example.com/', True),
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
		#("http://-error-.invalid/", False),
		#("http://a.b--c.de/", False), # shouldnt that be correct?
		#("http://-a.b.co", False),
		#("http://a.b-.co", False),
		("http://0.0.0.0", False),
		#("http://10.1.1.0", False),
		#("http://10.1.1.255", False),
		#("http://224.1.1.1", False),
		("http://1.1.1.1.1", False),
		#("http://123.123.123", False),
		("http://3628126748", False),
		#("http://.www.foo.bar/", False),
		("http://www.foo.bar./", False),
		("http://.www.foo.bar./", False),
		#("http://10.1.1.1", False),
		#("http://10.1.1.254", False)
	)
	def test_markdown_urls(self, url, valid):
		truth = "asd <{}> qwe".format(url)

		result = markdown_urls("asd {} qwe".format(url))
		if valid:
			self.assertEqual(truth, result)
		else:
			self.assertNotEqual(truth, result)

		result = markdown_urls("asd <{}> qwe".format(url))
		if valid:
			self.assertEqual(truth, result)

	@parametrize(
		('http://foo.com', '<http://foo.com>'),
		('asd http://foo.com', 'asd <http://foo.com>'),
		('http://foo.com qwe', '<http://foo.com> qwe'),
		('asd http://foo.com qwe', 'asd <http://foo.com> qwe'),
		('http://foo.com.', '<http://foo.com>.'),
		('asd http://foo.com.', 'asd <http://foo.com>.'),
		('http://foo.com. qwe', '<http://foo.com>. qwe'),
		('asd http://foo.com. qwe', 'asd <http://foo.com>. qwe'),

		("asd https://sub2.sub1.domain.com/asd/qwe#zxc.", "asd <https://sub2.sub1.domain.com/asd/qwe#zxc>."),
		("https://sub.domain/dir/1 https://sub.domain/dir/2", "<https://sub.domain/dir/1> <https://sub.domain/dir/2>"),
	)
	def test_markdown_urls_2(self, text, truth):
		result = markdown_urls(text)
		self.assertEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
