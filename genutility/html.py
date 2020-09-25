from __future__ import absolute_import, division, print_function, unicode_literals

import bs4


def simple_microdata_parser(bstree): # schema.org Microdata, replace with `extruct` module?
	# type: (bs4.BeautifulSoup, ) -> dict

	def is_item_scope(elem):
		return elem.has_attr("itemscope") and elem.has_attr("itemtype") and not elem.has_attr("itemprop")

	def is_item_scopeprop(elem):
		return elem.has_attr("itemscope") and elem.has_attr("itemtype") and elem.has_attr("itemprop")

	def is_item_prop(elem):
		return elem.has_attr("itemprop") and not elem.has_attr("itemscope") and not elem.has_attr("itemtype")

	def rec(tree, dict=None):
		if dict is None:
			dict = {}

		for child in tree.children:
			if isinstance(child, bs4.element.Tag):
				if is_item_scope(child):
					key = child["itemtype"]
					value = rec(child)
					#print("tag {} is scope: {}".format(child.name, child["itemtype"]))

					try:
						dict[key].append(value)
					except KeyError:
						dict[key] = [value]

				elif is_item_scopeprop(child):
					#print("tag {} is scopeprop: {}, {}".format(child.name, child["itemtype"], child["itemprop"]))

					try:
						dict[(child["itemtype"], child["itemprop"])].append(rec(child))
					except KeyError:
						dict[(child["itemtype"], child["itemprop"])] = [rec(child)]

				elif is_item_prop(child):
					key = child["itemprop"]

					if child.name == "meta":
						value = child["content"]
					elif key == "url":
						value = child["href"]
						rec(child, dict)
					elif child.contents:
						value = child.text.strip() # was: child.contents[0].string
					else:
						continue

					try:
						dict[key].append(value)
					except KeyError:
						dict[key] = [value]

				else:
					rec(child, dict)

		return dict

	return rec(bstree) #.html
