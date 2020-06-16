from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import viewitems

import logging

import wx
from wx.lib.mixins.listctrl import ColumnSorterMixin

logger = logging.getLogger(__name__)

class AdvancedListCtrl(wx.ListCtrl, ColumnSorterMixin):

	#wx.LC_SORT_* breaks idtopos
	def __init__(self, *args, **kwargs):
		wx.ListCtrl.__init__(self, *args, **kwargs)
		self.columns = 0
		self._init()
		ColumnSorterMixin.__init__(self, 0)

		#self.Bind(wx.EVT_LIST_DELETE_ITEM, self.OnDeleteItem)
		#self.Bind(wx.EVT_LIST_INSERT_ITEM, self.OnInsertItem)

	def _init(self):
		self.rows = 0
		self.itemDataMap = {}
		self.insertcount = 0
		self.idtopos = {}

	def GetListCtrl(self):
		return self

	def ClearAll(self, clear_columns = True):
		if clear_columns:
			wx.ListCtrl.ClearAll(self)
			self.columns = 0
		else:
			wx.ListCtrl.DeleteAllItems(self)
		self._init()

	def Setup(self, columns):
		self.columns = len(columns)
		self.SetColumnCount(self.columns)
		for i, col in enumerate(columns):
			self.InsertColumn(i, col)

	def Append(self, items):
		if len(items) != self.columns:
			raise ValueError("Length of items doesn't match available columns")

		pos = self.InsertItem(self.rows, items[0])
		assert pos == self.rows
		#logger.debug("Appending Item on rows->pos: {}->{}".format(self.rows, pos))

		self.rows += 1
		self.SetItemData(pos, self.insertcount)
		self.itemDataMap[self.insertcount] = items

		"""for id, pos in viewitems(self.idtopos):
			if pos >= event.Index:
				self.idtopos[id] = pos + 1"""

		self.idtopos[self.insertcount] = pos
		self.insertcount += 1

		for col in range(1, self.columns):
			self.SetItem(pos, col, items[col])

		return self.insertcount - 1

	def Edit(self, pos, items):
		"""items is dict with col as key and string als value"""
		for col, val in viewitems(items):
			self.SetItem(pos, col, val)

	def GetSelections(self):
		indexes = []
		pos = self.GetFirstSelected()
		while pos != -1:
			indexes.append(pos)
			pos = self.GetNextSelected(pos)
		return indexes

	def DeleteSelectedItems(self):
		#might be faster with autoarrange (listbox only??) off, no reversed -> autoarrange on
		indexes = self.GetSelections()

		for index in reversed(indexes):
			self.DeleteItem(index)
			self.rows -= 1
			id = self.GetItemData(index)
			del self.itemDataMap[id]
			del self.idtopos[id]

		return indexes

	def Get(self, pos = 0):
		if pos < 0:
			return self.GetItem(self.GetItemCount() + 1 + pos).GetText()
		else:
			return self.GetItem(pos).GetText()

	def IDtoPos(self, id):
		return self.idtopos[id]

	def Delete(self, pos = 0):
		if pos < 0:
			index = self.GetItemCount() + 1 + pos
		else:
			index = pos
		if self.GetItemCount() > pos:
			item = self.GetItem(index)
			ret = item.GetText()
			id = self.GetItemData(index)
			del self.itemDataMap[id]
			del self.idtopos[id]

			self.rows -= 1
			self.DeleteItem(index)
			return ret
		else:
			return None

class AdvancedItemContainerMixin(object):

	def DeleteSelectedItems(self):
		#might be faster with autoarrange of, no reversed -> autoarrange on
		indexes = self.GetSelections()

		for index in reversed(indexes):
			self.Delete(index)

		return indexes

class AdvancedListBox(wx.ListBox, AdvancedItemContainerMixin):

	def __init__(self, *args, **kwargs):
		wx.ListBox.__init__(self, *args, **kwargs)
