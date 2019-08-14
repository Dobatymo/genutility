from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import viewkeys
import json

from genutility.http import URLRequest

class StreamWatcher(object):

	def __init__(self, api):
		self.api = api
		self.followed = {name: False for name in api.get_followed()}

	def watch(self, notify_started, notify_stopped):
		for name in viewkeys(self.followed):
			stream = self.api.get_stream(name)

			if stream is not None and not self.followed[name]:
				self.followed[name] = True
				notify_started(name)
			elif stream is None and self.followed[name]:
				self.followed[name] = False
				notify_stopped(name)

class TwitchAPI(object):

	base = "https://api.twitch.tv/kraken/"
	follows = "users/{}/follows/channels?client_id={}"
	streams = "streams/{}?client_id={}"

	def __init__(self, username, client_id):
		self.username = username
		self.client_id = client_id

	def get_followed(self):
		url = TwitchAPI.base + TwitchAPI.follows.format(self.username, self.client_id)
		data = URLRequest(url).load()
		d = json.loads(data)
		return [follow["channel"]["_links"]["self"].rsplit("/", 1)[1] for follow in d["follows"]]

	def get_stream(self, channel):
		url = TwitchAPI.base + TwitchAPI.streams.format(channel, self.client_id)
		data = URLRequest(url).load()
		d = json.loads(data)
		return d["stream"]

	def watcher(self):
		return StreamWatcher(self)
