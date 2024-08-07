import asyncio
import csv
import logging
import re
import time
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Coroutine, Dict, Generic, Iterable, Iterator, List
from typing import Mapping as MappingT
from typing import Optional
from typing import Sequence as SequenceT
from typing import Tuple, TypeVar, Union

import aiohttp
import requests
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceExpiredSession

from .atomic import sopen
from .callbacks import Progress
from .json import read_json, write_json

if TYPE_CHECKING:
    import pandas as pd  # noqa: F401

JsonDict = Dict[str, Any]
ReturnTGet = TypeVar("ReturnTGet")
ReturnTPost = TypeVar("ReturnTPost")
T = TypeVar("T")

logger = logging.getLogger(__name__)

_sosl_pat = re.compile("[" + re.escape("?&|!{}[]()^~*:\\\"'+-") + "]")


def _sosl_repl(m) -> str:
    return "\\" + m.group(0)


def sosl_escape(s: str) -> str:
    return _sosl_pat.sub(_sosl_repl, s)


def one(result: SequenceT[T]) -> T:
    if len(result) == 1:
        return result[0]
    else:
        raise ValueError("More than one result")


class SalesforceError(Exception):
    pass


def _flatten_row(row):
    ret = {}
    del row["attributes"]

    for k, v in row.items():
        if isinstance(v, dict):
            for kk, vv in _flatten_row(v).items():
                ret[f"{k}.{kk}"] = vv
        else:
            ret[k] = v

    return ret


class MySalesforce:
    def __init__(
        self,
        username: str,
        password: str,
        security_token: str,
        consumer_key: str,
        consumer_secret: str,
        test: bool = False,
        cache_file: Optional[str] = None,
        timeout: int = 60,
    ) -> None:
        self.username = username
        self.password = password
        self.security_token = security_token
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.test = test
        self.cache_file = cache_file
        self.timeout = timeout

        self._session: Optional[Salesforce] = None

    def _login(self) -> Tuple[str, str]:
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

    def session(self, fresh: bool = False) -> Salesforce:
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
                write_json(
                    {
                        "instance_url": instance_url,
                        "session_id": session_id,
                    },
                    self.cache_file,
                )

            logger.debug("Creating new Salesforce session")
            self._session = Salesforce(instance_url=instance_url, session_id=session_id)

        return self._session

    # internal query/search

    def _query(self, s: str, attributes: bool = False) -> List[JsonDict]:
        try:
            results = self.session().query(s).get("records", [])
        except SalesforceExpiredSession:
            logger.debug("Salesforce session expired")
            results = self.session(True).query(s).get("records", [])

        if not attributes:
            for row in results:
                del row["attributes"]

        return results

    def _query_all(self, s: str, flatten: bool = True) -> Iterator[JsonDict]:
        reconnect = True

        try:
            for row in self.session().query_all_iter(s):
                if flatten:
                    yield _flatten_row(row)
                else:
                    yield row
                reconnect = False
        except SalesforceExpiredSession:
            logger.debug("Salesforce session expired")
            if reconnect:
                for row in self.session(True).query_all_iter(s):
                    if flatten:
                        yield _flatten_row(row)
                    else:
                        yield row
            else:
                raise RuntimeError("Cannot reconnect Salesforce session after partial query")

    def _search(self, s):
        try:
            return self.session().search(s)
        except SalesforceExpiredSession:
            logger.debug("Salesforce session expired")
            return self.session(True).search(s)

    def rest_post(self, endpoint: str, params: dict) -> dict:
        sess = self.session()
        headers = {"Authorization": "Bearer " + sess.session_id}

        r = requests.post("https://" + sess.sf_instance + endpoint, json=params, headers=headers, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def rest_get(self, endpoint: str) -> dict:
        sess = self.session()
        headers = {"Authorization": "Bearer " + sess.session_id}

        r = requests.get("https://" + sess.sf_instance + endpoint, headers=headers, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # actual methods

    def query(self, query_str: str) -> List[JsonDict]:
        return self._query(query_str)

    def _get_one_field(self, results, name):
        return [row[name] for row in results]

    def get_all_objects(self) -> List[JsonDict]:
        query_str = "SELECT QualifiedApiName, Label FROM EntityDefinition ORDER BY QualifiedApiName"

        return self._query(query_str)

    def get_all_fields(self, object_name: str) -> List[JsonDict]:
        """Retrieves all fields of `object_name`.
        Warning: `object_name` is not escaped!
        """

        query_str = f"SELECT QualifiedApiName, DataType, Label FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName = '{object_name}'"  # nosec

        return self._query(query_str)

    def search_fields(self, s: str, object_name: str, object_fields: Iterable[str]) -> dict:
        """Searches for `s` in object_name with object_fields.
        Warning: `object_name` and `object_fields` are not escaped!
        """

        s = sosl_escape(s)
        return self._search("FIND {{{}}} RETURNING {}({})".format(s, object_name, ", ".join(object_fields)))

    @staticmethod
    def dictkeymapper(it: Iterable[MappingT[str, str]], columns: MappingT[str, T]) -> Iterator[Dict[T, str]]:
        for row in it:
            yield {v: row.get(k, "") for k, v in columns.items()}

    def soql_to_pandas(
        self,
        query_str: str,
        columns: Optional[Union[SequenceT[str], MappingT[str, str]]] = None,
        progress: Optional[Progress] = None,
    ) -> "pd.DataFrame":
        import pandas as pd  # noqa: F811

        progress = progress or Progress()
        it = progress.track(self._query_all(query_str, flatten=True))

        if not columns:
            fieldnames: Optional[Iterable[str]] = None
        elif isinstance(columns, Sequence):
            fieldnames = columns
        elif isinstance(columns, Mapping):
            fieldnames = columns.keys()
        else:
            raise ValueError()

        df = pd.DataFrame.from_records(it, columns=fieldnames)
        if isinstance(columns, Mapping):
            df.columns = columns.values()
        return df

    def dump_csv(
        self,
        query_str: str,
        path: str,
        safe: bool = False,
        columns: Optional[Union[SequenceT[str], MappingT[str, str]]] = None,
        progress: Optional[Progress] = None,
    ) -> int:
        """Run SOQL `query_str` and dump results to csv file `path`.
        Returns the number of exported rows.
        """

        i = 0

        with sopen(path, "wt", encoding="utf-8", newline="", safe=safe) as csvfile:
            progress = progress or Progress()
            it = progress.track(self._query_all(query_str, flatten=True))

            if isinstance(columns, Mapping):
                it = self.dictkeymapper(it, columns)

            row = next(it)
            if not columns:
                fieldnames = row.keys()
            elif isinstance(columns, Sequence):
                fieldnames = columns
            elif isinstance(columns, Mapping):
                fieldnames = columns.values()
            else:
                raise ValueError()

            csvwriter = csv.DictWriter(csvfile, fieldnames, extrasaction="ignore")

            csvwriter.writeheader()
            csvwriter.writerow(row)
            i += 1

            for row in it:
                csvwriter.writerow(row)
                i += 1

        return i


class LiveAgentBase(Generic[ReturnTGet, ReturnTPost]):
    # https://help.salesforce.com/articleView?id=000331168&type=1&mode=1
    # https://help.salesforce.com/articleView?id=000340657&type=1&mode=1

    api_version = "42"

    def __init__(
        self,
        hostname: str,
        organization_id: str,
        deployment_id: str,
        button_id: str,
        scheme: str = "https",
        timeout: int = 30,
    ) -> None:
        self.hostname = hostname
        self.organization_id = organization_id
        self.deployment_id = deployment_id
        self.button_id = button_id
        self.scheme = scheme
        self.timeout = timeout

        if not (hostname and organization_id and deployment_id and button_id and scheme):
            raise ValueError("All arguments must have a value")

        self.key: Optional[str] = None
        self.affinity_token: Optional[str] = None
        self._sequence = 0
        self.last_offset = 0
        self.client_poll_timeout: Optional[int] = None

    # abstract

    def get_request(
        self, endpoint: str, headers: JsonDict, params: Optional[JsonDict] = None, timeout: Optional[float] = None
    ) -> ReturnTGet:
        raise NotImplementedError

    def post_request(
        self, endpoint: str, headers: JsonDict, json: Optional[JsonDict] = None, timeout: Optional[float] = None
    ) -> ReturnTPost:
        raise NotImplementedError

    # helper

    def urljoin(self, endpoint: str) -> str:
        return self.scheme + "://" + self.hostname + endpoint

    @property
    def sequence(self) -> str:
        self._sequence += 1
        return str(self._sequence)

    @staticmethod
    def _make_prechat_details(slots: Union[Dict[str, str], List[JsonDict]]) -> List[JsonDict]:
        if isinstance(slots, dict):
            prechat_details = []

            for label, value in slots.items():
                custom_detail = {
                    "label": label,
                    "value": value,
                    "displayToAgent": True,
                    "transcriptFields": [],
                    "entityMaps": [],
                }
                prechat_details.append(custom_detail)

        elif isinstance(slots, list):
            try:
                for custom_detail in slots:
                    custom_detail["label"]
                    custom_detail["value"]
                    custom_detail.setdefault("displayToAgent", True)
                    custom_detail.setdefault("transcriptFields", [])
                    custom_detail.setdefault("entityMaps", [])
            except KeyError as e:
                raise ValueError(f"slots is missing fields: {e}")

            prechat_details = slots

        else:
            raise TypeError("either prechat_details must be given or slots must be dict or list")

        return prechat_details

    def _availibility(self, res: JsonDict) -> bool:
        # this is not a staticmethod as to include potentially useful stack-info in logs

        for msg in res["messages"]:
            if msg["type"] == "Availability":
                return msg["message"]["results"][0].get("isAvailable", False)
            else:
                logger.error("Got unexpected message: %s", msg)

        raise SalesforceError("No Availability message in live agent response")

    def _reset(self, d: JsonDict) -> None:
        msg = d["messages"][0]
        assert msg["type"] == "ReconnectSession"

        self.affinity_token = msg["affinityToken"]
        reset = msg.get("resetSequence", True)
        if reset:
            self._sequence = 0

    def _set_session_info(self, response: JsonDict) -> None:
        self.key = response["key"]
        self.affinity_token = response["affinityToken"]
        self.client_poll_timeout = response["clientPollTimeout"]

    # high level

    def send(self, text: str) -> ReturnTPost:
        """Send text message to agent."""

        assert self.key
        assert self.affinity_token
        return self.rest_chat_message(self.key, self.affinity_token, text)

    def close(self) -> ReturnTPost:
        """Close live chat.
        Can raise a 403 HTTP error in case the agent already ended the chat.
        """

        assert self.key
        assert self.affinity_token
        return self.rest_chat_end(self.key, self.affinity_token)

    # low level

    def rest_session_id(self) -> ReturnTGet:
        endpoint = "/chat/rest/System/SessionId"

        headers = {
            "X-LIVEAGENT-AFFINITY": "null",
        }

        return self.get_request(endpoint, headers)

    def rest_chasitor_init(
        self,
        key: str,
        affinity_token: str,
        session_id: str,
        visitor_name: str,
        user_agent: str = "",
        language: str = "en-US",
        screen_resolution: str = "1920x1080",
        prechat_details: Optional[List[JsonDict]] = None,
        prechat_entities: Optional[List[JsonDict]] = None,
        receive_queue_updates: bool = True,
        is_post: bool = True,
    ) -> ReturnTPost:
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

    def rest_reconnect_session(self, key: str, affinity_token: str, offset: int) -> ReturnTGet:
        endpoint = "/chat/rest/System/ReconnectSession"

        headers = {
            "X-LIVEAGENT-AFFINITY": affinity_token,
            "X-LIVEAGENT-SESSION-KEY": key,
        }

        params = {"ReconnectSession.offset": offset}

        return self.get_request(endpoint, headers, params=params)

    def rest_chasitor_resync_state(self, key: str, affinity_token: str) -> ReturnTPost:
        endpoint = "/chat/rest/Chasitor/ChasitorResyncState"

        headers = {
            "X-LIVEAGENT-AFFINITY": affinity_token,
            "X-LIVEAGENT-SESSION-KEY": key,
        }

        params = {"organizationId": self.organization_id}

        return self.post_request(endpoint, headers, json=params)

    def rest_messages(self, key: str, affinity_token: str) -> ReturnTGet:
        endpoint = "/chat/rest/System/Messages"

        headers = {
            "X-LIVEAGENT-AFFINITY": affinity_token,
            "X-LIVEAGENT-SESSION-KEY": key,
        }

        return self.get_request(endpoint, headers, timeout=self.client_poll_timeout)

    def rest_chat_message(self, key: str, affinity_token: str, text: str) -> ReturnTPost:
        endpoint = "/chat/rest/Chasitor/ChatMessage"

        headers = {
            "X-LIVEAGENT-AFFINITY": affinity_token,
            "X-LIVEAGENT-SESSION-KEY": key,
        }

        params = {
            "text": text,
        }

        return self.post_request(endpoint, headers, json=params)

    def rest_chasitor_sneak_peek(self, key: str, affinity_token: str, position: int, text: str) -> ReturnTPost:
        endpoint = "/chat/rest/Chasitor/ChasitorSneakPeek"

        headers = {
            "X-LIVEAGENT-AFFINITY": affinity_token,
            "X-LIVEAGENT-SESSION-KEY": key,
        }

        params = {"position": position, "text": text}

        return self.post_request(endpoint, headers, json=params)

    def rest_chat_end(self, key: str, affinity_token: str) -> ReturnTPost:
        endpoint = "/chat/rest/Chasitor/ChatEnd"

        headers = {
            "X-LIVEAGENT-AFFINITY": affinity_token,
            "X-LIVEAGENT-SESSION-KEY": key,
        }

        params = {"type": "ChatEndReason", "reason": "client"}

        return self.post_request(endpoint, headers, json=params)

    def rest_availability(self, estimated_wait_time: bool = False) -> ReturnTGet:
        endpoint = "/chat/rest/Visitor/Availability"

        headers: JsonDict = {}

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


class LiveAgent(LiveAgentBase[JsonDict, bytes]):
    def get_request(
        self, endpoint: str, headers: JsonDict, params: Optional[JsonDict] = None, timeout: Optional[float] = None
    ) -> JsonDict:
        headers.setdefault("X-LIVEAGENT-API-VERSION", self.api_version)
        timeout = timeout or self.timeout

        r = requests.get(self.urljoin(endpoint), params=params, headers=headers, timeout=self.timeout)
        r.raise_for_status()
        if r.status_code == 204:
            return {}
        else:
            return r.json()

    def post_request(
        self, endpoint: str, headers: JsonDict, json: Optional[JsonDict] = None, timeout: Optional[float] = None
    ) -> bytes:
        headers.setdefault("X-LIVEAGENT-API-VERSION", self.api_version)
        headers.setdefault("X-LIVEAGENT-SEQUENCE", self.sequence)
        timeout = timeout or self.timeout

        r = requests.post(self.urljoin(endpoint), json=json, headers=headers, timeout=self.timeout)
        r.raise_for_status()
        return r.content

    # high level

    def connect(
        self,
        visitor_name: str,
        slots: Optional[Union[Dict[str, str], List[JsonDict]]] = None,
        prechat_details: Optional[List[JsonDict]] = None,
        prechat_entities: Optional[List[JsonDict]] = None,
    ) -> None:
        """Connect using `visitor_name` as name."""

        self._sequence = 0
        response = self.rest_session_id()

        self._set_session_info(response)
        session_id = response["id"]
        if not prechat_details and slots:
            prechat_details = self._make_prechat_details(slots)

        assert self.key
        assert self.affinity_token
        self.rest_chasitor_init(
            self.key,
            self.affinity_token,
            session_id,
            visitor_name,
            prechat_details=prechat_details,
            prechat_entities=prechat_entities,
        )

    def reconnect(self) -> None:
        """Use `reconnect()` whenever a 503 error is encounted."""

        assert self.key
        assert self.last_offset
        d = self.rest_reconnect_session(self.key, "null", self.last_offset)
        self._reset(d)
        assert self.affinity_token
        self.rest_chasitor_resync_state(self.key, self.affinity_token)

    def is_available(self) -> bool:
        """Check for agent availability."""

        res = self.rest_availability()
        return self._availibility(res)

    def wait_available(self, wait: float = 10) -> None:
        """Waits until an agent is available.
        Polls every `wait` seconds.
        """

        while True:
            if self.is_available():
                return

            time.sleep(wait)

    def receive(self, wait_forever: bool = False) -> List[JsonDict]:
        """Long poll messages."""

        assert self.key
        assert self.affinity_token
        while True:
            d = self.rest_messages(self.key, self.affinity_token)
            if not d:
                if wait_forever:
                    continue
                else:
                    return []

            self.last_offset = d.get("offset", 0)
            return d["messages"]


class LiveAgentAsync(LiveAgentBase[Coroutine[Any, Any, JsonDict], Coroutine[Any, Any, bytes]]):
    trust_env = True

    async def get_request(
        self, endpoint: str, headers: JsonDict, params: Optional[JsonDict] = None, timeout: Optional[float] = None
    ) -> JsonDict:
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

    async def post_request(
        self, endpoint: str, headers: JsonDict, json: Optional[JsonDict] = None, timeout: Optional[float] = None
    ) -> bytes:
        headers = headers or {}
        headers.setdefault("X-LIVEAGENT-API-VERSION", self.api_version)
        headers.setdefault("X-LIVEAGENT-SEQUENCE", self.sequence)
        timeout = timeout or self.timeout

        async with aiohttp.ClientSession(trust_env=self.trust_env) as session:
            async with session.post(self.urljoin(endpoint), headers=headers, json=json, timeout=timeout) as r:
                r.raise_for_status()
                return await r.read()

    # high level

    async def connect(
        self,
        visitor_name: str,
        slots: Optional[Union[Dict[str, str], List[JsonDict]]] = None,
        prechat_details: Optional[List[JsonDict]] = None,
        prechat_entities: Optional[List[JsonDict]] = None,
    ) -> None:
        """Connect using `visitor_name` as name."""

        self._sequence = 0
        response = await self.rest_session_id()

        self._set_session_info(response)
        session_id = response["id"]
        if not prechat_details and slots:
            prechat_details = self._make_prechat_details(slots)

        assert self.key
        assert self.affinity_token
        await self.rest_chasitor_init(
            self.key,
            self.affinity_token,
            session_id,
            visitor_name,
            prechat_details=prechat_details,
            prechat_entities=prechat_entities,
        )

    async def reconnect(self) -> None:
        """Use `reconnect()` whenever a 503 error is encounted."""

        assert self.key
        assert self.last_offset
        d = await self.rest_reconnect_session(self.key, "null", self.last_offset)
        self._reset(d)
        assert self.affinity_token
        await self.rest_chasitor_resync_state(self.key, self.affinity_token)

    async def is_available(self) -> bool:
        """Check for agent availability."""

        res = await self.rest_availability()
        return self._availibility(res)

    async def wait_available(self, wait: float = 10) -> None:
        """Waits until an agent is available.
        Polls every `wait` seconds.
        """

        while True:
            if await self.is_available():
                return

            await asyncio.sleep(wait)

    async def receive(self, wait_forever: bool = False) -> List[JsonDict]:
        """Long poll messages."""
        assert self.key
        assert self.affinity_token

        while True:
            d = await self.rest_messages(self.key, self.affinity_token)
            if not d:
                if wait_forever:
                    continue
                else:
                    return []

            self.last_offset = d.get("offset", 0)
            return d["messages"]
