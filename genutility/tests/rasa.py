from __future__ import generator_stop

import asyncio

import requests_mock
from aioresponses import aioresponses

from genutility.rasa import RasaRestConversations, RasaRestConversationsAsync, RasaRestWebhook, RasaRestWebhookAsync
from genutility.test import MyTestCase

Webhook = [
	{"text": "Hey Rasa!"},
	{"image": "http://example.com/image.jpg"}
]

GetTracker = {
	"conversation_id": "default",
	"slots": [{
		"slot_name": "slot_value"
	}],
	"latest_message": {
		"entities": [{
			"start": 0,
			"end": 0,
			"value": "string",
			"entity": "string",
			"confidence": 0
		}],
		"intent": {
			"confidence": 0.6323,
			"name": "greet"
		},
		"intent_ranking": [{
			"confidence": 0.6323,
			"name": "greet"
		}],
		"text": "Hello!"
	},
	"latest_event_time": 1537645578.314389,
	"followup_action": "string",
	"paused": False,
	"events": [{
		"event": "slot",
		"timestamp": 1559744410
	}],
	"latest_input_channel": "rest",
	"latest_action_name": "action_listen",
	"latest_action": {
		"action_name": "string",
		"action_text": "string"
	},
	"active_loop": {
		"name": "restaurant_form"
	}
}

class RasaTest(MyTestCase):

	def test_webhook(self):
		c = RasaRestWebhook("sender-id", netloc="rasa")

		with requests_mock.Mocker() as m:
			m.post("http://rasa/webhooks/rest/webhook", json=Webhook)

			result = c.send_message("the message")
			truth = Webhook

		self.assertEqual(truth, result)

	def test_conversations_tracker(self):
		c = RasaRestConversations("sender-id", netloc="rasa")

		with requests_mock.Mocker() as m:
			m.get("http://rasa/conversations/sender-id/tracker", json=GetTracker)

			result = c.get_tracker()
			truth = GetTracker

		self.assertEqual(truth, result)

class RasaAsyncTest(MyTestCase):

	@classmethod
	def setUpClass(cls):
		cls.loop = asyncio.get_event_loop()

	def test_webhook(self):
		c = RasaRestWebhookAsync("sender-id", netloc="rasa")

		with aioresponses() as m:
			m.post("http://rasa/webhooks/rest/webhook", payload=Webhook)

			truth = Webhook
			result = self.loop.run_until_complete(c.send_message("the message"))

			self.assertEqual(truth, result)

	def test_conversations_tracker(self):
		c = RasaRestConversationsAsync("sender-id", netloc="rasa")

		with aioresponses() as m:
			m.get("http://rasa/conversations/sender-id/tracker?include_events=AFTER_RESTART", payload=GetTracker)

			truth = GetTracker
			result = self.loop.run_until_complete(c.get_tracker("AFTER_RESTART", ""))

			self.assertEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
