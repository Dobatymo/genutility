from __future__ import absolute_import, division, print_function, unicode_literals

from io import open

from lxml import etree  # nosec


def xml_xslt_to_xhtml(path_xml, path_xslt, path_xhtml):

	""" Only use with trusted xml data """

	xml = etree.parse(path_xml)  # nosec
	xslt = etree.parse(path_xslt)  # nosec
	transform = etree.XSLT(xslt)
	newdom = transform(xml)
	with open(path_xhtml, "wb") as xhtml:
		newdom.write(xhtml, pretty_print=True, xml_declaration=True, encoding="utf-8")
