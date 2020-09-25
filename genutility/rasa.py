import requests

from .exceptions import assert_choice

class RasaRest(object):

	def __init__(self, sender, scheme="http", netloc="localhost:5005", timeout=60):
		# type: (str, str, str, int) -> None

		self.sender = sender
		self.scheme = scheme
		self.netloc = netloc
		self.timeout = timeout

	def get_endpoint(self, path):
		# type: (str, ) -> str

		return self.scheme + "://" + self.netloc + path

INCLUDE_EVENTS_ENUM = {"AFTER_RESTART", "ALL", "APPLIED", "NONE"}

class RasaRestConversations(RasaRest):

	def get_tracker(self, include_events=None, until=None):
		# type: (Optional[str], Optional[int]) -> dict

		assert_choice("include_events", include_events, INCLUDE_EVENTS_ENUM, True)

		url = self.get_endpoint("/conversations/{}/tracker".format(self.sender))

		r = requests.get(url, timeout=self.timeout, params={
			"include_events": include_events,
			"until": until,
		})
		r.raise_for_status()
		return r.json()

	def post_events(self, event, timestamp, include_events=None):
		# type: (str, int, Optional[str]) -> dict

		assert_choice("include_events", include_events, INCLUDE_EVENTS_ENUM, True)

		url = self.get_endpoint("/conversations/{}/tracker/events".format(self.sender))

		r = requests.post(url, json={
			"event": event,
			"timestamp": timestamp,
		}, timeout=self.timeout)
		r.raise_for_status()
		return r.json()

	def get_story(self, until=None):
		# type: (Optional[int], ) -> dict

		url = self.get_endpoint("/conversations/{}/story".format(self.sender))

		r = requests.get(url, timeout=self.timeout, params={
			"until": until,
		})
		r.raise_for_status()
		return r.json()

class RasaRestWebhook(RasaRest):

	def health(self):
		# type: () -> dict

		url = self.get_endpoint("/webhooks/rest/")

		r = requests.get(url, timeout=self.timeout)
		r.raise_for_status()
		return r.json()

	def send_message(self, message):
		# type: (str, ) -> List[dict]

		url = self.get_endpoint("/webhooks/rest/webhook")

		r = requests.post(url, json={
			"sender": self.sender,
			"message": message,
		}, timeout=self.timeout)
		r.raise_for_status()
		return r.json()
