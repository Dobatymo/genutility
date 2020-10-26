import asyncio
import csv
import logging
import re
import time
from collections.abc import Sequence
from typing import TYPE_CHECKING

import aiohttp
import requests
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceAuthenticationFailed, SalesforceExpiredSession
from simplejson.errors import JSONDecodeError

from .atomic import sopen
from .iter import progress
from .json import read_json, write_json

if TYPE_CHECKING:
	from typing import Any, Awaitable, Dict, Iterable, Iterator, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

_sosl_pat = re.compile("[" + re.escape("?&|!{}[]()^~*:\\\"'+-") + "]")
_sosl_repl = lambda m: "\\" + m.group(0)

def sosl_escape(s):
	# type: (str, ) -> str

	return _sosl_pat.sub(_sosl_repl, s)

class SalesforceError(Exception):
	pass

class MySalesforce(object):

	def __init__(self, username, password, security_token, consumer_key, consumer_secret, test=False, cache_file=None, timeout=60):
		# type: (str, str, str, str, str, bool, Optional[str], int) -> None

		self.username = username
		self.password = password
		self.security_token = security_token
		self.consumer_key = consumer_key
		self.consumer_secret = consumer_secret
		self.test = test
		self.cache_file = cache_file
		self.timeout = timeout

		self._session = None # type: Optional[Salesforce]

	def _login(self):
		# type: () -> Tuple[str, str]

		logger.debug("Obtaining new Salesforce credentials")

		if self.test:
			url = "https://test.salesforce.com/services/oauth2/token"
		else:
			url = "https://login.salesforce.com/services/oauth2/token"

		params = {
			"grant_type": "password",
			"client_id": self.consumer_key,
			"client_secret": self.consumer_secret,
			"username": self.username,
			"password": self.password + self.security_token,
		}

		r = requests.post(url, params=params, timeout=self.timeout)
		r.raise_for_status()
		response = r.json()

		return response["instance_url"], response["access_token"]

	def session(self, fresh=False):
		# type: (bool, ) -> Salesforce

		if self._session is not None and not fresh:
			return self._session

		try:
			if fresh or not self.cache_file:
				raise FileNotFoundError

			obj = read_json(self.cache_file)
			logger.debug("Creating new Salesforce session")
			self._session = Salesforce(instance_url=obj["instance_url"], session_id=obj["session_id"])

		except FileNotFoundError:
			instance_url, session_id = self._login()

			if self.cache_file:
				write_json({
					"instance_url": instance_url,
					"session_id": session_id,
				}, self.cache_file)

			logger.debug("Creating new Salesforce session")
			self._session = Salesforce(instance_url=instance_url, session_id=session_id)

		return self._session

	# internal query/search

	def _query(self, s, attributes=False):
		# type: (str, bool) -> List[dict]

		try:
			results = self.session().query(s).get("records", [])
		except SalesforceExpiredSession:
			logger.debug("Salesforce session expired")
			results = self.session(True).query(s).get("records", [])

		if not attributes:
			for row in results:
				del row["attributes"]

		return results

	def _query_all(self, s, attributes=False):
		# type: (str, bool) -> Iterator[dict]

		reconnect = True

		try:
			for row in self.session().query_all_iter(s):
				if not attributes:
					del row["attributes"]
				yield row
				reconnect = False
		except SalesforceExpiredSession:
			logger.debug("Salesforce session expired")
			if reconnect:
				for row in self.session(True).query_all_iter(s):
					if not attributes:
						del row["attributes"]
					yield row
			else:
				raise RuntimeError("Cannot reconnect Salesforce session after partial query")

	def _search(self, s):

		try:
			return self.session().search(s)
		except SalesforceExpiredSession:
			logger.debug("Salesforce session expired")
			return self.session(True).search(s)

	def rest_post(self, endpoint, params):
		# type: (str, dict) -> dict

		sess = self.session()
		headers = {"Authorization": "Bearer " + sess.session_id}

		r = requests.post("https://" + sess.sf_instance + endpoint, headers=headers, json=params)
		r.raise_for_status()
		return r.json()

	def rest_get(self, endpoint):
		# type: (str, ) -> dict

		sess = self.session()
		headers = {"Authorization": "Bearer " + sess.session_id}

		r = requests.get("https://" + sess.sf_instance + endpoint, headers=headers)
		r.raise_for_status()
		return r.json()

	# actual methods

	def query(self, query_str):
		# type: (str, ) -> List[dict]

		return self._query(query_str)

	def _get_one_field(self, results, name):
		return [row[name] for row in results]

	def get_all_objects(self):
		# type: () -> List[dict]

		query_str = "SELECT QualifiedApiName, Label FROM EntityDefinition ORDER BY QualifiedApiName"

		return self._query(query_str)

	def get_all_fields(self, object_name):
		# type: (str, ) -> List[dict]

		""" Retrieves all fields of `object_name`.
			Warning: `object_name` is not escaped!
		"""

		query_str = "SELECT QualifiedApiName, DataType, Label FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName = '{}'".format(object_name)  # nosec

		return self._query(query_str)

	def search_fields(self, s, object_name, object_fields):
		# type: (str, str, Iterable[str]) -> dict

		""" Searches for `s` in object_name with object_fields.
			Warning: `object_name` and `object_fields` are not escaped!
		"""

		s = sosl_escape(s)
		return self._search("FIND {{{}}} RETURNING {}({})".format(s, object_name, ", ".join(object_fields)))

	def dump_csv(self, query_str, path, verbose=False, safe=False):
		# type: (str, str, False, bool) -> int

		""" Run SOQL `query_str` and dump results to csv file `path`.
			Returns the number of exported rows.
		"""

		i = 0

		with sopen(path, "wt", encoding="utf-8", newline="", safe=safe) as csvfile:
			csvwriter = csv.writer(csvfile)

			if verbose:
				it = progress(self._query_all(query_str))
			else:
				it = self._query_all(query_str)

			row = next(it)
			csvwriter.writerow(row.keys())
			csvwriter.writerow(row.values())
			i += 1

			for row in it:
				csvwriter.writerow(row.values())
				i += 1

		return i

class LiveAgentBase(object):
	# https://help.salesforce.com/articleView?id=000331168&type=1&mode=1
	# https://help.salesforce.com/articleView?id=000340657&type=1&mode=1

	api_version = "42"

	def __init__(self, hostname, organization_id, deployment_id, button_id, scheme="https", timeout=30):
		# type: (str, str, str, str, str, int) -> None

		self.hostname = hostname
		self.organization_id = organization_id
		self.deployment_id = deployment_id
		self.button_id = button_id
		self.scheme = scheme
		self.timeout = timeout

		self.key = None
		self.affinity_token = None
		self._sequence = 0
		self.last_offset = 0
		self.client_poll_timeout = None

	# helper

	def urljoin(self, endpoint):
		return self.scheme + "://" + self.hostname + endpoint

	@property
	def sequence(self):
		self._sequence += 1
		return str(self._sequence)

	@staticmethod
	def _make_prechat_details(prechat_details, slots):

		if prechat_details:
			pass

		elif not slots:
			prechat_details = []

		elif isinstance(slots, dict):
			prechat_details = []  # type: List[Dict[str, Any]]

			for label, value in slots.items():
				custom_detail = {
					"label": label,
					"value": value,
					"displayToAgent": True,
					"transcriptFields": [],
					"entityMaps": [],
				}
				prechat_details.append(custom_detail)

		elif isinstance(slots, Sequence):
			try:
				for custom_detail in slots:
					custom_detail["label"]
					custom_detail["value"]
					custom_detail.setdefault("displayToAgent", True)
					custom_detail.setdefault("transcriptFields", [])
					custom_detail.setdefault("entityMaps", [])
			except KeyError as e:
				raise ValueError("slots is missing fields: {}".format(e))

			prechat_details = slots

		else:
			raise ValueError("either prechat_details must be given or slots must be dict or Sequence")

		return prechat_details

	@staticmethod
	def _availibility(res):
		for msg in res["messages"]:
			if msg["type"] == "Availability":
				return msg["message"]["results"][0].get("isAvailable", False)
			else:
				logger.error("Got unexpected message: %s", msg)

		raise SalesforceError("No Availability message in live agent response")

	def _reset(self, d):
		msg = d["messages"][0]
		assert msg["type"] == "ReconnectSession"

		self.affinity_token = msg["affinityToken"]
		reset = msg.get("resetSequence", True)
		if reset:
			self._sequence = 0

	def _set_session_info(self, response):
		self.key = response["key"]
		self.affinity_token = response["affinityToken"]
		self.client_poll_timeout = response["clientPollTimeout"]

	# high level

	def send(self, text):
		# type: (str, ) -> Union[bytes, Awaitable[bytes]]

		""" Send text message to agent.
		"""

		return self.rest_chat_message(self.key, self.affinity_token, text)

	def close(self):
		# type: () -> Union[bytes, Awaitable[bytes]]

		""" Close live chat.
			Can raise a 403 HTTP error in case the agent already ended the chat.
		"""

		return self.rest_chat_end(self.key, self.affinity_token)

	# low level

	def rest_session_id(self):
		# type: () -> Union[dict, Awaitable[dict]]

		endpoint = "/chat/rest/System/SessionId"

		headers = {
			"X-LIVEAGENT-AFFINITY": "null",
		}

		return self.get_request(endpoint, headers)

	def rest_chasitor_init(self, key, affinity_token, session_id, visitor_name, user_agent="", language="en-US",
		screen_resolution="1920x1080", prechat_details=None, prechat_entities=None,
		receive_queue_updates=True, is_post=True):
		# type: (str, str, str, str, str, str, str, Sequence[Dict[str, Any]], Sequence[Dict[str, Any]], bool, bool) -> Union[bytes, Awaitable[bytes]]

		endpoint = "/chat/rest/Chasitor/ChasitorInit"

		headers = {
			"X-LIVEAGENT-AFFINITY": affinity_token,
			"X-LIVEAGENT-SESSION-KEY": key,
		}

		params = {
			"organizationId": self.organization_id,
			"deploymentId": self.deployment_id,
			"buttonId": self.button_id,
			"sessionId": session_id,
			"userAgent": user_agent,
			"language": language,
			"screenResolution": screen_resolution,
			"visitorName": visitor_name,
			"prechatDetails": prechat_details or [],
			"prechatEntities": prechat_entities or [],
			"receiveQueueUpdates": receive_queue_updates,
			"isPost": is_post,
		}

		return self.post_request(endpoint, headers, json=params)

	def rest_reconnect_session(self, key, affinity_token, offset):
		# type: (str, str, int) -> Union[dict, Awaitable[dict]]

		endpoint = "/chat/rest/System/ReconnectSession"

		headers = {
			"X-LIVEAGENT-AFFINITY": affinity_token,
			"X-LIVEAGENT-SESSION-KEY": key,
		}

		params = {
			"ReconnectSession.offset": offset
		}

		return self.get_request(endpoint, headers, params=params)

	def rest_chasitor_resync_state(self, key, affinity_token):
		# type: (str, str) -> Union[dict, Awaitable[dict]]

		endpoint = "/chat/rest/Chasitor/ChasitorResyncState"

		headers = {
			"X-LIVEAGENT-AFFINITY": affinity_token,
			"X-LIVEAGENT-SESSION-KEY": key,
		}

		params = {
			"organizationId": self.organization_id
		}

		return self.get_request(endpoint, headers, json=params)

	def rest_messages(self, key, affinity_token):
		# type: (str, str) -> Union[dict, Awaitable[dict]]

		endpoint = "/chat/rest/System/Messages"

		headers = {
			"X-LIVEAGENT-AFFINITY": affinity_token,
			"X-LIVEAGENT-SESSION-KEY": key,
		}

		return self.get_request(endpoint, headers, timeout=self.client_poll_timeout)

	def rest_chat_message(self, key, affinity_token, text):
		# type: (str, str, str) -> Union[bytes, Awaitable[bytes]]

		endpoint = "/chat/rest/Chasitor/ChatMessage"

		headers = {
			"X-LIVEAGENT-AFFINITY": affinity_token,
			"X-LIVEAGENT-SESSION-KEY": key,
		}

		params = {
			"text" : text,
		}

		return self.post_request(endpoint, headers, json=params)

	def rest_chasitor_sneak_peek(self, key, affinity_token, position, text):
		# type: (str, str, int, str) -> Union[bytes, Awaitable[bytes]]

		endpoint = "/chat/rest/Chasitor/ChasitorSneakPeek"

		headers = {
			"X-LIVEAGENT-AFFINITY": affinity_token,
			"X-LIVEAGENT-SESSION-KEY": key,
		}

		params = {
			"position": position,
			"text": text
		}

		return self.post_request(endpoint, headers, json=params)

	def rest_chat_end(self, key, affinity_token):
		# type: (str, str) -> Union[bytes, Awaitable[bytes]]

		endpoint = "/chat/rest/Chasitor/ChatEnd"

		headers = {
			"X-LIVEAGENT-AFFINITY": affinity_token,
			"X-LIVEAGENT-SESSION-KEY": key,
		}

		params = {
			"type": "ChatEndReason",
			"reason": "client"
		}

		return self.post_request(endpoint, headers, json=params)

	def rest_availability(self, estimated_wait_time=False):
		# type: (bool, ) -> Union[dict, Awaitable[dict]]

		endpoint = "/chat/rest/Visitor/Availability"

		headers = {}

		params = {
			"org_id": self.organization_id,
			"deployment_id": self.deployment_id,

			# this should be an array according to docs. however arrays in url query params are not clearly defined.
			# `requests` repeats the key with different values, but it's not clear that this is the correct way.
			# edit: according to https://www.srinivas4sfdc.com/2019/12/live-agent-chat-rest-api-to-check.html
			# this should be a comma separated list.
			"Availability.ids": self.button_id,
			"Availability.needEstimatedWaitTime": str(int(estimated_wait_time)),
		}

		return self.get_request(endpoint, headers, params=params)

class LiveAgent(LiveAgentBase):

	def get_request(self, endpoint, headers, params=None, timeout=None):
		# type: (str, dict, Optional[dict], Optional[float]) -> dict

		headers.setdefault("X-LIVEAGENT-API-VERSION", self.api_version)
		timeout = timeout or self.timeout

		r = requests.get(self.urljoin(endpoint), headers=headers, params=params, timeout=self.timeout)
		r.raise_for_status()
		if r.status_code == 204:
			return {}
		else:
			return r.json()

	def post_request(self, endpoint, headers, json=None, timeout=None):
		# type: (str, dict, Optional[dict], Optional[float]) -> bytes

		headers.setdefault("X-LIVEAGENT-API-VERSION", self.api_version)
		headers.setdefault("X-LIVEAGENT-SEQUENCE", self.sequence)
		timeout = timeout or self.timeout

		r = requests.post(self.urljoin(endpoint), headers=headers, json=json, timeout=self.timeout)
		r.raise_for_status()
		return r.content

	# high level

	def connect(self, visitor_name, slots=None, prechat_details=None, prechat_entities=None):
		# type: (str, Optional[Union[Dict[str, str], Sequence[Dict[str, Any]]]], Sequence[Dict[str, Any]], Sequence[Dict[str, Any]]) -> None

		""" Connect using `visitor_name` as name.
		"""

		self._sequence = 0
		response = self.rest_session_id()

		self._set_session_info(response)
		session_id = response["id"]
		prechat_details = self._make_prechat_details(prechat_details, slots)

		self.rest_chasitor_init(self.key, self.affinity_token, session_id, visitor_name,
			prechat_details=prechat_details, prechat_entities=prechat_entities)

	def reconnect(self):
		# type: () -> None

		""" Use `reconnect()` whenever a 503 error is encounted. """

		d = self.rest_reconnect_session(self.key, "null", self.last_offset)
		self._reset(d)
		self.rest_chasitor_resync_state(self.key, self.affinity_token)

	def is_available(self):
		# type: () -> bool

		""" Check for agent availability.
		"""

		res = self.rest_availability()
		return self._availibility(res)

	def wait_available(self, wait=10):
		# type: (float, ) -> None

		""" Waits until an agent is available.
			Polls every `wait` seconds.
		"""

		while True:
			if self.is_available():
				return

			time.sleep(wait)

	def receive(self, wait_forever=False):
		# type: (bool, ) -> List[dict]

		""" Long poll messages.
		"""

		while True:
			d = self.rest_messages(self.key, self.affinity_token)
			if not d:
				if wait_forever:
					continue
				else:
					return []

			self.last_offset = d.get("offset", 0)
			return d["messages"]

class LiveAgentAsync(LiveAgentBase):

	trust_env = True

	async def get_request(self, endpoint, headers, params=None, timeout=None):
		# type: (str, dict, Optional[dict], Optional[float]) -> dict

		headers = headers or {}
		headers.setdefault("X-LIVEAGENT-API-VERSION", self.api_version)
		timeout = timeout or self.timeout

		async with aiohttp.ClientSession(trust_env=self.trust_env) as session:
			async with session.get(self.urljoin(endpoint), headers=headers, params=params, timeout=timeout) as r:
				r.raise_for_status()
				if r.status == 204:
					return {}
				else:
					return await r.json()

	async def post_request(self, endpoint, headers, json=None, timeout=None):
		# type: (str, dict, Optional[dict], Optional[float]) -> bytes

		headers = headers or {}
		headers.setdefault("X-LIVEAGENT-API-VERSION", self.api_version)
		headers.setdefault("X-LIVEAGENT-SEQUENCE", self.sequence)
		timeout = timeout or self.timeout

		async with aiohttp.ClientSession(trust_env=self.trust_env) as session:
			async with session.post(self.urljoin(endpoint), headers=headers, json=json, timeout=timeout) as r:
				r.raise_for_status()
				return await r.read()

	# high level

	async def connect(self, visitor_name, slots=None, prechat_details=None, prechat_entities=None):
		# type: (str, Optional[Union[Dict[str, str], Sequence[Dict[str, Any]]]], Sequence[Dict[str, Any]], Sequence[Dict[str, Any]]) -> None

		""" Connect using `visitor_name` as name.
		"""

		self._sequence = 0
		response = await self.rest_session_id()

		self._set_session_info(response)
		session_id = response["id"]
		prechat_details = self._make_prechat_details(prechat_details, slots)

		await self.rest_chasitor_init(self.key, self.affinity_token, session_id, visitor_name,
			prechat_details=prechat_details, prechat_entities=prechat_entities)

	async def reconnect(self):
		# type: () -> None

		""" Use `reconnect()` whenever a 503 error is encounted. """

		d = await self.rest_reconnect_session(self.key, "null", self.last_offset)
		self._reset(d)
		await self.rest_chasitor_resync_state(self.key, self.affinity_token)

	async def is_available(self):
		# type: () -> bool

		""" Check for agent availability.
		"""

		res = await self.rest_availability()
		return self._availibility(res)

	async def wait_available(self, wait=10):
		# type: (float, ) -> None

		""" Waits until an agent is available.
			Polls every `wait` seconds.
		"""

		while True:
			if await self.is_available():
				return

			await asyncio.sleep(wait)

	async def receive(self, wait_forever=False):
		# type: (bool, ) -> List[dict]

		""" Long poll messages.
		"""

		while True:
			d = await self.rest_messages(self.key, self.affinity_token)
			if not d:
				if wait_forever:
					continue
				else:
					return []

			self.last_offset = d.get("offset", 0)
			return d["messages"]
