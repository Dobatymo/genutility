from __future__ import generator_stop

import asyncio
import re

import requests_mock
from aioresponses import aioresponses
from genutility.salesforce import LiveAgent, LiveAgentAsync
from genutility.test import MyTestCase

SessionId = {
	"clientPollTimeout": 40,
	"key": "00000000-0000-0000-0000-000000000000!00000000-0000-0000-0000-000000000000",
	"affinityToken": "00000000",
	"id": "00000000-0000-0000-0000-000000000000"
}

Availability = {
	"messages": [{
		"type": "Availability",
		"message": {
			"results": [{
				"id": "button-id",
				"isAvailable": True
			}]
		}
	}]
}

MessagesReceive = [
	{
		"type": "ChatRequestSuccess",
		"message": {
			"connectionTimeout": 150000,
			"estimatedWaitTime": -1,
			"sensitiveDataRules": [],
			"transcriptSaveEnabled": False,
			"url": "",
			"queuePosition": 1,
			"customDetails": [],
			"visitorId": "00000000-0000-0000-0000-000000000000",
			"geoLocation": {
				"organization": "ISP",
				"city": "Taipei",
				"countryName": "Taiwan",
				"latitude": 25.0000,
				"countryCode": "TW",
				"longitude": 121.000
			}
		}
	},
	{
		"type": "ChatMessage",
		"message": {
			"text": "Liveagent Message",
			"name": "Liveagent Name"
		}
	},
	{
		"type": "AgentNotTyping",
		"message": {}
	}
]

Messages = {
	"messages": MessagesReceive,
	"sequence": 4
}

class SalesforceTest(MyTestCase):

	def test_connect(self):
		la = LiveAgent("sfdc", "org-id", "deploy-id", "button-id")

		with requests_mock.Mocker() as m:
			m.get("https://sfdc/chat/rest/System/SessionId", json=SessionId)
			m.post("https://sfdc/chat/rest/Chasitor/ChasitorInit", text="OK")

			la.connect("name")

	def test_is_available(self):
		la = LiveAgent("sfdc", "org-id", "deploy-id", "button-id")

		with requests_mock.Mocker() as m:
			m.get("https://sfdc/chat/rest/Visitor/Availability", json=Availability)

			result = la.is_available()
			truth = True
			self.assertEqual(truth, result)

	def test_receive(self):
		la = LiveAgent("sfdc", "org-id", "deploy-id", "button-id")

		with requests_mock.Mocker() as m:
			m.get("https://sfdc/chat/rest/System/Messages", json=Messages)

			result = la.receive()
			truth = MessagesReceive
			self.assertEqual(truth, result)

class SalesforceAsyncTest(MyTestCase):

	@classmethod
	def setUpClass(cls):
		cls.loop = asyncio.get_event_loop()

	def test_connect(self):
		la = LiveAgentAsync("sfdc", "org-id", "deploy-id", "button-id")

		with aioresponses() as m:
			m.get("https://sfdc/chat/rest/System/SessionId", payload=SessionId)
			m.post("https://sfdc/chat/rest/Chasitor/ChasitorInit", body="OK")

			self.loop.run_until_complete(la.connect("name"))

	def test_is_available(self):
		la = LiveAgentAsync("sfdc", "org-id", "deploy-id", "button-id")

		with aioresponses() as m:
			m.get(re.compile(r"^https:\/\/sfdc\/chat\/rest\/Visitor\/Availability\?"), payload=Availability)

			result = self.loop.run_until_complete(la.is_available())
			truth = True
			self.assertEqual(truth, result)

	def test_receive(self):
		la = LiveAgentAsync("sfdc", "org-id", "deploy-id", "button-id")

		with aioresponses() as m:
			m.get("https://sfdc/chat/rest/System/Messages", payload=Messages)

			result = self.loop.run_until_complete(la.receive())
			truth = MessagesReceive
			self.assertEqual(truth, result)


if __name__ == "__main__":
	import unittest
	unittest.main()
