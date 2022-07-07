from __future__ import generator_stop

from lxml import etree  # nosec


def xml_xslt_to_xhtml(path_xml: str, path_xslt: str, path_xhtml: str) -> None:

    """Only use with trusted xml data"""

    xml = etree.parse(path_xml)  # nosec
    xslt = etree.parse(path_xslt)  # nosec
    transform = etree.XSLT(xslt)
    newdom = transform(xml)
    with open(path_xhtml, "wb") as xhtml:
        newdom.write(xhtml, pretty_print=True, xml_declaration=True, encoding="utf-8")
