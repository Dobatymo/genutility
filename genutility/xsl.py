from __future__ import absolute_import, division, print_function, unicode_literals

from io import open

from lxml import etree

def xml_xslt_to_xhtml(path_xml, path_xslt, path_xhtml):

	xml = etree.parse(path_xml)
	xslt = etree.parse(path_xslt)
	transform = etree.XSLT(xslt)
	newdom = transform(xml)
	with open(path_xhtml, "wb") as xhtml:
		newdom.write(xhtml, pretty_print=True, xml_declaration=True, encoding="utf-8")
