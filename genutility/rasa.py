import requests

from .exceptions import assert_choice

class RasaRest(object):

	def __init__(self, sender, scheme="http", netloc="localhost:5005", token=None, timeout=60):
		# type: (str, str, str, Optional[str], int) -> None

		self.sender = sender
		self.scheme = scheme
		self.netloc = netloc
		self.token = token
		self.timeout = timeout

	def get_endpoint(self, path):
		# type: (str, ) -> str

		return self.scheme + "://" + self.netloc + path

	def get_request(self, url, params=None):
		# type: (str, Optional[dict]) -> dict

		params = params or {}

		if self.token:
			params.setdefault("token", self.token)

		r = requests.get(url, timeout=self.timeout, params=params)
		r.raise_for_status()
		return r.json()

	def post_request(self, url, params=None, json=None):
		# type: (str, Optional[dict], Optional[dict]) -> dict

		params = params or {}

		if self.token:
			params.setdefault("token", self.token)

		r = requests.post(url, timeout=self.timeout, params=params, json=json)
		r.raise_for_status()
		return r.json()

INCLUDE_EVENTS_ENUM = {"AFTER_RESTART", "ALL", "APPLIED", "NONE"}

class RasaRestConversations(RasaRest):

	def get_tracker(self, include_events=None, until=None):
		# type: (Optional[str], Optional[int]) -> dict

		assert_choice("include_events", include_events, INCLUDE_EVENTS_ENUM, True)

		url = self.get_endpoint("/conversations/{}/tracker".format(self.sender))

		return self.get_request(url, params={
			"include_events": include_events,
			"until": until,
		})

	def post_events(self, event, timestamp, include_events=None):
		# type: (str, int, Optional[str]) -> dict

		assert_choice("include_events", include_events, INCLUDE_EVENTS_ENUM, True)

		url = self.get_endpoint("/conversations/{}/tracker/events".format(self.sender))

		return self.post_request(url, json={
			"event": event,
			"timestamp": timestamp,
		})

	def get_story(self, until=None):
		# type: (Optional[int], ) -> dict

		url = self.get_endpoint("/conversations/{}/story".format(self.sender))

		return self.get_request(url, params={
			"until": until,
		})

class RasaRestWebhook(RasaRest):

	def health(self):
		# type: () -> dict

		url = self.get_endpoint("/webhooks/rest/")

		return self.get_request(url)

	def send_message(self, message):
		# type: (str, ) -> List[dict]

		url = self.get_endpoint("/webhooks/rest/webhook")

		return self.post_request(url, json={
			"sender": self.sender,
			"message": message,
		})

class RasaCallbackWebhook(RasaRest):

	def send_message(self, message):
		# type: (str, ) -> List[dict]

		url = self.get_endpoint("/webhooks/callback/webhook")

		return self.post_request(url, json={
			"sender": self.sender,
			"message": message,
		})
