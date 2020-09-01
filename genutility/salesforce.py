import logging, re, csv
from time import sleep
from collections.abc import Sequence
from typing import TYPE_CHECKING

import requests
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceExpiredSession, SalesforceAuthenticationFailed
from simplejson.errors import JSONDecodeError

from .iter import progress
from .json import read_json, write_json

if TYPE_CHECKING:
	from typing import List, Iterable, Optional, Tuple, Iterator

logger = logging.getLogger(__name__)

_sosl_pat = re.compile("[" + re.escape("?&|!{}[]()^~*:\\\"'+-") + "]")
_sosl_repl = lambda m: "\\" + m.group(0)

def sosl_escape(s):
	# type: (str, ) -> str

	return _sosl_pat.sub(_sosl_repl, s)

class MySalesforce(object):

	timeout = 60

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
		# type: () -> Salesforce

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

	def _query(self, s):
		# type: (str, ) -> dict

		try:
			return self.session().query(s)
		except SalesforceExpiredSession:
			logger.debug("Salesforce session expired")
			return self.session(True).query(s)

	def _query_all(self, s):
		# type: (str, ) -> Iterator[dict]

		reconnect = True

		try:
			for row in self.session().query_all_iter(s):
				yield row
				reconnect = False
		except SalesforceExpiredSession:
			logger.debug("Salesforce session expired")
			if reconnect:
				for row in self.session(True).query_all_iter(s):
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
		# type: (str, ) -> dict

		return self._query(query_str)

	def get_all_fields(self, object_name):
		# type: (str, ) -> dict

		""" Retrieves all fields of `object_name`.
			Warning: `object_name` is not escaped!
		"""

		query_str = "SELECT QualifiedApiName FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName = '{}'".format(object_name)  # nosec

		return self._query(query_str)

	def get_all_objects(self):

		query_str = "SELECT QualifiedApiName FROM EntityDefinition ORDER BY QualifiedApiName"

		return self._query(query_str)

	def search_fields(self, s, object_name, object_fields):
		# type: (str, str, Iterable[str]) -> dict

		""" Searches for `s` in object_name with object_fields.
			Warning: `object_name` and `object_fields` are not escaped!
		"""

		s = sosl_escape(s)
		return self._search("FIND {{{}}} RETURNING {}({})".format(s, object_name, ", ".join(object_fields)))

	def dump_csv(self, query_str, path, verbose=False):
		# type: (str, str, False) -> int

		""" Run SOQL `query_str` and dump results to csv file `path`.
			Returns the number of exported rows.
		"""

		i = 0

		with open(path, "w", encoding="utf-8", newline="") as csvfile:
			csvwriter = csv.writer(csvfile)

			if verbose:
				it = progress(self._query_all(query_str))
			else:
				it = self._query_all(query_str)

			row = next(it)
			del row["attributes"]
			csvwriter.writerow(row.keys())
			csvwriter.writerow(row.values())
			i += 1

			for row in it:
				del row["attributes"]
				csvwriter.writerow(row.values())
				i += 1

		return i

class LiveAgent(object):

	# https://help.salesforce.com/articleView?id=000331168&type=1&mode=1
	# https://help.salesforce.com/articleView?id=000340657&type=1&mode=1

	api_version = "42"

	def __init__(self, hostname, organization_id, deployment_id, button_id, timeout=60):
		# type: (str, str, str, str, int) -> None

		self.hostname = hostname
		self.organization_id = organization_id
		self.deployment_id = deployment_id
		self.button_id = button_id
		self.timeout = timeout

		self.key = None
		self.affinity_token = None
		self._sequence = 0
		self.last_offset = 0

	# helper

	def urljoin(self, endpoint):
		return "https://" + self.hostname + endpoint

	@property
	def sequence(self):
		self._sequence += 1
		return str(self._sequence)

	# high level

	def connect(self, visitor_name, slots=None, prechat_details=None, prechat_entities=None):
		# type: (str, Optional[Union[Dict[str, str], Sequence[Dict[str, Any]]]]) -> None

		""" Connect using `visitor_name` as name.
		"""

		self._sequence = 0
		response = self.rest_session_id()
		slots = slots or {}

		self.key = response["key"]
		self.affinity_token = response["affinityToken"]
		session_id = response["id"]
		client_poll_timeout = response["clientPollTimeout"]

		if not prechat_details:

			if isinstance(slots, dict):
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
				raise ValueError("slots must be dict or Sequence")

		self.rest_chasitor_init(self.key, self.affinity_token, session_id, visitor_name,
			prechat_details=prechat_details, prechat_entities=prechat_entities)

	def reconnect(self):
		# type: () -> None

		""" Use `reconnect()` whenever a 503 error is encounted. """

		d = self.rest_reconnect_session(self.key, "null", self.last_offset)

		msg = d["messages"][0]
		assert msg["type"] == "ReconnectSession"

		self.affinity_token = msg["affinityToken"]
		reset = msg.get("resetSequence", True)
		if reset:
			self._sequence = 0

		self.rest_chasitor_resync_state(self.key, self.affinity_token)

	def is_available(self):
		# type: () -> bool

		""" Check for agent availability.
		"""

		res = self.rest_availability()
		for msg in res["messages"]:
			if msg["type"] == "Availability":
				return msg["message"]["results"][0].get("isAvailable", False)
			else:
				logger.error("Got unexpected message: %s", msg)

	def wait_available(self, wait=10):
		# type: (float, ) -> None

		while True:
			if self.is_available():
				return

			sleep(wait)

	def receive(self, wait_forever=False):
		# type: () -> List[dict]

		""" Long poll messages.
		"""

		while True:
			res = self.rest_messages(self.key, self.affinity_token)
			if res.status_code == 204:
				if wait_forever:
					continue
				else:
					return []

			d = res.json()
			self.last_offset = d.get("offset", 0)
			return d["messages"]

	def send(self, text):
		# type: (str, ) -> bytes

		""" Send text message to agent.
		"""

		return self.rest_chat_message(self.key, self.affinity_token, text)

	def close(self):
		# type: () -> bytes

		""" Close live chat.
		"""

		return self.rest_chat_end(self.key, self.affinity_token)

	# low level

	def rest_session_id(self):
		# type: () -> dict

		endpoint = "/chat/rest/System/SessionId"

		headers = {
			"X-LIVEAGENT-API-VERSION": self.api_version,
			"X-LIVEAGENT-AFFINITY": "null",
		}

		r = requests.get(self.urljoin(endpoint), headers=headers, timeout=self.timeout)
		r.raise_for_status()
		return r.json()

	def rest_chasitor_init(self, key, affinity_token, session_id, visitor_name, user_agent="", language="en-US",
		screen_resolution="1920x1080", prechat_details=None, prechat_entities=None,
		receive_queue_updates=True, is_post=True):
		# type: (str, str, str, str, str, str, str, Sequence[Dict[str, Any]]) -> bytes

		endpoint = "/chat/rest/Chasitor/ChasitorInit"

		headers = {
			"X-LIVEAGENT-API-VERSION": self.api_version,
			"X-LIVEAGENT-AFFINITY": affinity_token,
			"X-LIVEAGENT-SESSION-KEY": key,
			"X-LIVEAGENT-SEQUENCE": self.sequence,
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

		r = requests.post(self.urljoin(endpoint), headers=headers, json=params, timeout=self.timeout)
		r.raise_for_status()
		return r.content

	def rest_reconnect_session(self, key, affinity_token, offset):
		# type: (str, str, int) -> dict

		endpoint = "/chat/rest/System/ReconnectSession"

		headers = {
			"X-LIVEAGENT-API-VERSION": self.api_version,
			"X-LIVEAGENT-AFFINITY": affinity_token,
			"X-LIVEAGENT-SESSION-KEY": key,
		}

		params = {
			"ReconnectSession.offset": offset
		}

		r = requests.get(self.urljoin(endpoint), headers=headers, params=params, timeout=self.timeout)
		r.raise_for_status()
		return r.json()

	def rest_chasitor_resync_state(self, key, affinity_token):
		# type: (str, str) -> bytes

		endpoint = "/chat/rest/Chasitor/ChasitorResyncState"

		headers = {
			"X-LIVEAGENT-API-VERSION": self.api_version,
			"X-LIVEAGENT-AFFINITY": affinity_token,
			"X-LIVEAGENT-SESSION-KEY": key,
		}

		params = {
			"organizationId": self.organization_id
		}

		r = requests.get(self.urljoin(endpoint), headers=headers, json=params, timeout=self.timeout)
		r.raise_for_status()
		return r.content

	def rest_messages(self, key, affinity_token):
		# type: (str, str) -> requests.Response

		endpoint = "/chat/rest/System/Messages"

		headers = {
			"X-LIVEAGENT-API-VERSION": self.api_version,
			"X-LIVEAGENT-AFFINITY": affinity_token,
			"X-LIVEAGENT-SESSION-KEY": key,
		}

		r = requests.get(self.urljoin(endpoint), headers=headers, timeout=self.timeout)
		r.raise_for_status()
		return r

	def rest_chat_message(self, key, affinity_token, text):
		# type: (str, str, str) -> bytes

		endpoint = "/chat/rest/Chasitor/ChatMessage"

		headers = {
			"X-LIVEAGENT-API-VERSION": self.api_version,
			"X-LIVEAGENT-AFFINITY": affinity_token,
			"X-LIVEAGENT-SESSION-KEY": key,
			"X-LIVEAGENT-SEQUENCE": self.sequence,
		}

		params = {
			"text" : text,
		}

		r = requests.post(self.urljoin(endpoint), headers=headers, json=params, timeout=self.timeout)
		r.raise_for_status()
		return r.content

	def rest_chasitor_sneak_peek(self, key, affinity_token, position, text):
		# type: (str, str, int, str) -> bytes

		endpoint = "/chat/rest/Chasitor/ChasitorSneakPeek"

		headers = {
			"X-LIVEAGENT-API-VERSION": self.api_version,
			"X-LIVEAGENT-AFFINITY": affinity_token,
			"X-LIVEAGENT-SESSION-KEY": key,
			"X-LIVEAGENT-SEQUENCE": self.sequence,
		}

		params = {
			"position": position,
			"text": text
		}

		r = requests.get(self.urljoin(endpoint), headers=headers, json=params, timeout=self.timeout)
		r.raise_for_status()
		return r.content

	def rest_chat_end(self, key, affinity_token):
		# type: (str, str) -> bytes

		endpoint = "/chat/rest/Chasitor/ChatEnd"

		headers = {
			"X-LIVEAGENT-API-VERSION": self.api_version,
			"X-LIVEAGENT-AFFINITY": affinity_token,
			"X-LIVEAGENT-SESSION-KEY": key,
			"X-LIVEAGENT-SEQUENCE": self.sequence,
		}

		params = {
			"type": "ChatEndReason",
			"reason": "client"
		}

		r = requests.post(self.urljoin(endpoint), headers=headers, json=params, timeout=self.timeout)
		r.raise_for_status()
		return r.content

	def rest_availability(self, estimated_wait_time=False):
		# type: (bool, ) -> dict

		endpoint = "/chat/rest/Visitor/Availability"

		headers = {
			"X-LIVEAGENT-API-VERSION": self.api_version,
		}

		params = {
			"org_id": self.organization_id,
			"deployment_id": self.deployment_id,
			"Availability.ids": [self.button_id],
			"Availability.needEstimatedWaitTime": str(int(estimated_wait_time)),
		}

		r = requests.get(self.urljoin(endpoint), headers=headers, params=params, timeout=self.timeout)
		r.raise_for_status()
		return r.json()
