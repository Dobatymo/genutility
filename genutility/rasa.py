from typing import TYPE_CHECKING

import aiohttp
import requests

from .exceptions import assert_choice

if TYPE_CHECKING:
	from typing import List, Optional

class Rasa(object):

	def __init__(self, sender, scheme="http", netloc="localhost:5005", token=None, timeout=60):
		# type: (str, str, str, Optional[str], int) -> None

		self.sender = sender
		self.scheme = scheme
		self.netloc = netloc
		self.token = token
		self.timeout = timeout

	def get_endpoint(self, path):
		# type: (str, ) -> str

		return f"{self.scheme}://{self.netloc}{path}"

class RasaRest(Rasa):

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

class RasaRestAsync(Rasa):

	async def get_request(self, url, params=None):
		# type: (str, Optional[dict]) -> dict

		params = params or {}

		if self.token:
			params.setdefault("token", self.token)

		async with aiohttp.ClientSession() as session:
			async with session.get(url, timeout=self.timeout, params=params) as response:
				response.raise_for_status()
				return await response.json()

	async def post_request(self, url, params=None, json=None):
		# type: (str, Optional[dict], Optional[dict]) -> dict

		params = params or {}

		if self.token:
			params.setdefault("token", self.token)

		async with aiohttp.ClientSession() as session:
			async with session.post(url, timeout=self.timeout, params=params, json=json) as response:
				response.raise_for_status()
				return await response.json()


INCLUDE_EVENTS_ENUM = {"AFTER_RESTART", "ALL", "APPLIED", "NONE"}
OUTPUT_CHANNEL_ENUM = {"latest", "slack", "callback", "facebook", "rocketchat", "telegram", "twilio", "webexteams", "socketio"}

class _RasaRestConversations(object):

	def get_tracker(self, include_events=None, until=None):
		# type: (Optional[str], Optional[int]) -> dict

		""" Retrieve a conversations tracker
			The tracker represents the state of the conversation. The state of the tracker is created by applying a sequence of events, which modify the state. These events can optionally be included in the response.
		"""

		assert_choice("include_events", include_events, INCLUDE_EVENTS_ENUM, True)

		url = self.get_endpoint(f"/conversations/{self.sender}/tracker")

		return self.get_request(url, params={
			"include_events": include_events,
			"until": until,
		})

	def post_events(self, event, timestamp, include_events=None, output_channel=None, execute_side_effects=False):
		# type: (str, int, Optional[str], bool) -> dict

		""" Append events to a tracker
			Appends one or multiple new events to the tracker state of the conversation. Any existing events will be kept and the new events will be appended, updating the existing state. If events are appended to a new conversation ID, the tracker will be initialised with a new session.
		"""

		assert_choice("include_events", include_events, INCLUDE_EVENTS_ENUM, True)
		assert_choice("output_channel", output_channel, OUTPUT_CHANNEL_ENUM, True)

		url = self.get_endpoint(f"/conversations/{self.sender}/tracker/events")

		return self.post_request(url, params={
			"include_events": include_events,
			"output_channel": output_channel,
			"execute_side_effects": execute_side_effects,
		}, json={
			"event": event,
			"timestamp": timestamp,
		})

	def get_story(self, until=None, all_sessions=False):
		# type: (Optional[int], bool) -> dict

		""" Retrieve an end-to-end story corresponding to a conversation
			The story represents the whole conversation in end-to-end format. This can be posted to the '/test/stories' endpoint and used as a test.
		"""

		url = self.get_endpoint(f"/conversations/{self.sender}/story")

		return self.get_request(url, params={
			"until": until,
			"all_sessions": all_sessions,
		})

	def execute_action(self, name, policy=None, confidence=None, include_events=None, output_channel=None):
		# type: (str, Optional[str], Optional[float], Optional[str], Optional[str]) -> dict

		""" Run an action in a conversation.
			DEPRECATED. Runs the action, calling the action server if necessary. Any responses sent by the executed action will be forwarded to the channel specified in the `output_channel` parameter. If no output channel is specified, any messages that should be sent to the user will be included in the response of this endpoint.
		"""

		assert_choice("include_events", include_events, INCLUDE_EVENTS_ENUM, True)
		assert_choice("output_channel", output_channel, OUTPUT_CHANNEL_ENUM, True)

		url = self.get_endpoint(f"/conversations/{self.sender}/execute")

		return self.post_request(url, params={
			"include_events": include_events,
			"output_channel": output_channel,
		}, json={
			"name": name,
			"policy": policy,
			"confidence": confidence,
		})

	def trigger_intent(self, name, entities=None, include_events=None, output_channel=None):
		# type: (str, Optional[dict], Optional[str], Optional[str]) -> dict

		""" Inject an intent into a conversation
			Sends a specified intent and list of entities in place of a user message. The bot then predicts and executes a response action. Any responses sent by the executed action will be forwarded to the channel specified in the output_channel parameter. If no output channel is specified, any messages that should be sent to the user will be included in the response of this endpoint.
		"""

		assert_choice("include_events", include_events, INCLUDE_EVENTS_ENUM, True)
		assert_choice("output_channel", output_channel, OUTPUT_CHANNEL_ENUM, True)

		url = self.get_endpoint(f"/conversations/{self.sender}/trigger_intent")

		return self.post_request(url, params={
			"include_events": include_events,
			"output_channel": output_channel,
		}, json={
			"name": name,
			"entities": entities,
		})

class _RasaRestWebhook(object):

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

class _RasaCallbackWebhook(object):

	def send_message(self, message):
		# type: (str, ) -> List[dict]

		url = self.get_endpoint("/webhooks/callback/webhook")

		return self.post_request(url, json={
			"sender": self.sender,
			"message": message,
		})

class RasaRestConversations(_RasaRestConversations, RasaRest):
	pass

class RasaRestWebhook(_RasaRestWebhook, RasaRest):
	pass

class RasaCallbackWebhook(_RasaCallbackWebhook, RasaRest):
	pass

class RasaRestConversationsAsync(_RasaRestConversations, RasaRestAsync):
	pass

class RasaRestWebhookAsync(_RasaRestWebhook, RasaRestAsync):
	pass

class RasaCallbackWebhookAsync(_RasaCallbackWebhook, RasaRestAsync):
	pass
