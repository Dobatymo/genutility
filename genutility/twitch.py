from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import viewkeys

import json
from typing import TYPE_CHECKING

from .http import URLRequest
from .ops import logical_xor

if TYPE_CHECKING:
	from typing import Callable, List, Optional, Tuple

class StreamWatcher(object):

	def __init__(self, api):
		self.api = api
		self.followed_names = api.get_followed()
		self.followed_online = {userid: False for userid in viewkeys(self.followed_names)}

	def watch(self, notify_started, notify_stopped):
		# type: (Callable[[str, str, Optional[str]], None], Callable[[str, str], None]) -> None

		user_ids = viewkeys(self.followed_names)
		streams = self.api.get_streams(user_ids)
		online = viewkeys(streams)
		offline = user_ids - online

		for user_id in online:
			if not self.followed_online[user_id]:
				self.followed_online[user_id] = True
				notify_started(user_id, self.followed_names[user_id], streams[user_id].get("title", None))

		for user_id in offline:
			if self.followed_online[user_id]:
				self.followed_online[user_id] = False
				notify_stopped(user_id, self.followed_names[user_id])

class TwitchAPI(object):

	base = "https://api.twitch.tv/helix/"
	login = "users"
	follows = "users/follows"
	streams = "streams?user_id={}"

	def __init__(self, client_id, userid=None, username=None):
		# type: (str, Optional[str], Optional[str]) -> None

		if not logical_xor(userid, username):
			raise ValueError("Either the userid or the username must be given")

		self.client_id = client_id

		if userid:
			self.userid = userid
		else:
			self.userid = self.get_userid(username)

	def req(self, url, params):
		# type: (str, List[Tuple[str, str]]) -> dict

		qs = "&".join(k+"="+v for k, v in params)
		data = URLRequest(url + "?" + qs, headers={"Client-ID": self.client_id}).load()
		return json.loads(data)

	def get_userid(self, username):
		# type: (str, ) -> str

		d = self.req(self.base + self.login, [("login", username)])
		return d["data"][0]["id"]

	def get_followed(self):
		d = self.req(self.base + self.follows, [("from_id", self.userid)])
		return {follow["to_id"]: follow["to_name"] for follow in d["data"]}

	def get_streams(self, user_ids):
		d = self.req(self.base + self.streams, [("user_id", user_id) for user_id in user_ids])
		ret = {stream["user_id"]: stream for stream in d["data"]}
		assert len(d["data"]) == len(ret), "More than one stream per user"
		return ret

	def watcher(self):
		# type: () -> StreamWatcher

		return StreamWatcher(self)
