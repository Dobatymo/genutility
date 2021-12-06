from __future__ import generator_stop

import os.path
from abc import ABCMeta, abstractmethod
from typing import Any, Coroutine, Dict, Generic, List, Optional, TypeVar, Union

import aiohttp
import requests

from .exceptions import assert_choice
from .yaml import read_yaml

""" Properly type checking this file would require higher-kinded type-vars,
    ie. https://github.com/python/typing/issues/548 to be fixed.
"""

JsonDict = Dict[str, Any]
JsonValue = Union[JsonDict, List[JsonDict]]
ReturnT = TypeVar("ReturnT")  # fixme: should be higher kinded type var
ResponseT = Union[bytes, JsonValue]

SyncReturnT = ResponseT
AsyncReturnT = Coroutine[Any, Any, ResponseT]


class RasaABC(Generic[ReturnT], metaclass=ABCMeta):

    sender: str

    @abstractmethod
    def get_endpoint(self, path):
        # type: (str, ) -> str
        raise NotImplementedError

    @abstractmethod
    def get_request(self, url, params=None, raw=False):
        # type: (str, Optional[JsonDict], bool) -> ReturnT
        raise NotImplementedError

    @abstractmethod
    def post_request(self, url, params=None, json=None, raw=False):
        # type: (str, Optional[JsonDict], Optional[JsonDict], bool) -> ReturnT
        raise NotImplementedError

    @abstractmethod
    def put_request(self, url, params=None, json=None, raw=False):
        # type: (str, Optional[JsonDict], Optional[JsonDict], bool) -> ReturnT
        raise NotImplementedError

    @abstractmethod
    def delete_request(self, url, params=None, json=None, raw=False):
        # type: (str, Optional[JsonDict], Optional[JsonDict], bool) -> ReturnT
        raise NotImplementedError


class Rasa:

    sender: str

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
    def get_request(self, url, params=None, raw=False):
        # type: (str, Optional[JsonDict], bool) -> ResponseT

        params = params or {}

        if self.token:
            params.setdefault("token", self.token)

        r = requests.get(url, timeout=self.timeout, params=params)
        r.raise_for_status()
        if raw:
            return r.content
        else:
            return r.json()

    def post_request(self, url, params=None, json=None, raw=False):
        # type: (str, Optional[JsonDict], Optional[JsonDict], bool) -> ResponseT

        params = params or {}

        if self.token:
            params.setdefault("token", self.token)

        r = requests.post(url, timeout=self.timeout, params=params, json=json)
        r.raise_for_status()
        if raw:
            return r.content
        else:
            return r.json()

    def put_request(self, url, params=None, json=None, raw=False):
        # type: (str, Optional[JsonDict], Optional[JsonDict], bool) -> ResponseT

        params = params or {}

        if self.token:
            params.setdefault("token", self.token)

        r = requests.put(url, timeout=self.timeout, params=params, json=json)
        r.raise_for_status()

        if raw:
            return r.content
        else:
            if r.status_code == 204:
                return b""
            else:
                return r.json()

    def delete_request(self, url, params=None, json=None, raw=False):
        # type: (str, Optional[JsonDict], Optional[JsonDict], bool) -> ResponseT

        params = params or {}

        if self.token:
            params.setdefault("token", self.token)

        r = requests.delete(url, timeout=self.timeout, params=params, json=json)
        r.raise_for_status()

        if raw:
            return r.content
        else:
            if r.status_code == 204:
                return b""
            else:
                return r.json()


class RasaRestAsync(Rasa):
    async def get_request(self, url, params=None, raw=False):
        # type: (str, Optional[JsonDict], bool) -> ResponseT

        params = params or {}

        if self.token:
            params.setdefault("token", self.token)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=self.timeout, params=params) as r:
                r.raise_for_status()
                if raw:
                    return await r.read()
                else:
                    return await r.json()

    async def post_request(self, url, params=None, json=None, raw=False):
        # type: (str, Optional[JsonDict], Optional[JsonDict], bool) -> ResponseT

        params = params or {}

        if self.token:
            params.setdefault("token", self.token)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, timeout=self.timeout, params=params, json=json) as r:
                r.raise_for_status()
                if raw:
                    return await r.read()
                else:
                    return await r.json()

    async def put_request(self, url, params=None, json=None, raw=False):
        # type: (str, Optional[JsonDict], Optional[JsonDict], bool) -> ResponseT

        params = params or {}

        if self.token:
            params.setdefault("token", self.token)

        async with aiohttp.ClientSession() as session:
            async with session.put(url, timeout=self.timeout, params=params, json=json) as r:
                r.raise_for_status()
                if raw:
                    return await r.read()
                else:
                    if r.status == 204:
                        return {}
                    else:
                        return await r.json()

    async def delete_request(self, url, params=None, json=None, raw=False):
        # type: (str, Optional[JsonDict], Optional[JsonDict], bool) -> ResponseT

        params = params or {}

        if self.token:
            params.setdefault("token", self.token)

        async with aiohttp.ClientSession() as session:
            async with session.delete(url, timeout=self.timeout, params=params, json=json) as r:
                r.raise_for_status()
                if raw:
                    return await r.read()
                else:
                    if r.status == 204:
                        return {}
                    else:
                        return await r.json()


INCLUDE_EVENTS_ENUM = {"AFTER_RESTART", "ALL", "APPLIED", "NONE"}
OUTPUT_CHANNEL_ENUM = {
    "latest",
    "slack",
    "callback",
    "facebook",
    "rocketchat",
    "telegram",
    "twilio",
    "webexteams",
    "socketio",
}


class _RasaRestConversations(RasaABC[ReturnT]):
    def get_tracker(self, include_events=None, until=None):
        # type: (Optional[str], Optional[int]) -> ReturnT

        """Retrieve a conversations tracker.

        The tracker represents the state of the conversation. The state of the tracker is created by applying a sequence of events, which modify the state. These events can optionally be included in the response.
        """

        assert_choice("include_events", include_events, INCLUDE_EVENTS_ENUM, True)

        url = self.get_endpoint(f"/conversations/{self.sender}/tracker")

        return self.get_request(
            url,
            params={
                "include_events": include_events,
                "until": until,
            },
        )

    def post_events(self, event, timestamp, include_events=None, output_channel=None, execute_side_effects=False):
        # type: (str, int, Optional[str], Optional[str], bool) -> ReturnT

        """Append events to a tracker.

        Appends one or multiple new events to the tracker state of the conversation. Any existing events will be kept and the new events will be appended, updating the existing state. If events are appended to a new conversation ID, the tracker will be initialised with a new session.
        """

        assert_choice("include_events", include_events, INCLUDE_EVENTS_ENUM, True)
        assert_choice("output_channel", output_channel, OUTPUT_CHANNEL_ENUM, True)

        url = self.get_endpoint(f"/conversations/{self.sender}/tracker/events")

        return self.post_request(
            url,
            params={
                "include_events": include_events,
                "output_channel": output_channel,
                "execute_side_effects": execute_side_effects,
            },
            json={
                "event": event,
                "timestamp": timestamp,
            },
        )

    def get_story(self, until=None, all_sessions=False):
        # type: (Optional[int], bool) -> ReturnT

        """Retrieve an end-to-end story corresponding to a conversation.

        The story represents the whole conversation in end-to-end format. This can be posted to the '/test/stories' endpoint and used as a test.
        """

        url = self.get_endpoint(f"/conversations/{self.sender}/story")

        return self.get_request(
            url,
            params={
                "until": until,
                "all_sessions": all_sessions,
            },
            raw=True,
        )

    def execute_action(self, name, policy=None, confidence=None, include_events=None, output_channel=None):
        # type: (str, Optional[str], Optional[float], Optional[str], Optional[str]) -> ReturnT

        """Run an action in a conversation.

        DEPRECATED. Runs the action, calling the action server if necessary. Any responses sent by the executed action will be forwarded to the channel specified in the `output_channel` parameter. If no output channel is specified, any messages that should be sent to the user will be included in the response of this endpoint.
        """

        assert_choice("include_events", include_events, INCLUDE_EVENTS_ENUM, True)
        assert_choice("output_channel", output_channel, OUTPUT_CHANNEL_ENUM, True)

        url = self.get_endpoint(f"/conversations/{self.sender}/execute")

        return self.post_request(
            url,
            params={
                "include_events": include_events,
                "output_channel": output_channel,
            },
            json={
                "name": name,
                "policy": policy,
                "confidence": confidence,
            },
        )

    def trigger_intent(self, name, entities=None, include_events=None, output_channel=None):
        # type: (str, Optional[JsonDict], Optional[str], Optional[str]) -> ReturnT

        """Inject an intent into a conversation.

        Sends a specified intent and list of entities in place of a user message. The bot then predicts and executes a response action. Any responses sent by the executed action will be forwarded to the channel specified in the output_channel parameter. If no output channel is specified, any messages that should be sent to the user will be included in the response of this endpoint.
        """

        assert_choice("include_events", include_events, INCLUDE_EVENTS_ENUM, True)
        assert_choice("output_channel", output_channel, OUTPUT_CHANNEL_ENUM, True)

        url = self.get_endpoint(f"/conversations/{self.sender}/trigger_intent")

        return self.post_request(
            url,
            params={
                "include_events": include_events,
                "output_channel": output_channel,
            },
            json={
                "name": name,
                "entities": entities,
            },
        )


REMOTE_STORAGE_ENUM = {"aws", "gcs", "azure"}


class _RasaRestModel(RasaABC[ReturnT]):
    def train(
        self,
        directory,
        config=None,
        domain=None,
        nlu=None,
        responses=None,
        stories=None,
        save_to_default_model_directory=True,
        force_training=False,
    ):
        # type: (str, Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], bool, bool) -> ReturnT

        """Train a Rasa model.

        Trains a new Rasa model. Depending on the data given only a dialogue model, only a NLU model, or a model combining a trained dialogue model with an NLU model will be trained. The new model is not loaded by default.
        """

        # use default values
        json = {
            "config": config or "config.yml",
            "domain": domain or "domain.yml",
            "nlu": nlu or "data/nlu.yml",
            "responses": responses or "data/responses.yml",
            "stories": stories or "data/stories.yml",
        }

        # check if files exist and read contents
        json = {k: read_yaml(v) if os.path.exists(v) else None for k, v in json.items()}

        url = self.get_endpoint("/model/train")

        return self.post_request(
            url,
            params={
                "save_to_default_model_directory": save_to_default_model_directory,
                "force_training": force_training,
            },
            json=json,
        )

    def replace_model(self, model_file=None, model_server=None, remote_storage=None):
        # type: (Optional[str], Optional[JsonDict], Optional[str]) -> ReturnT

        """Replace the currently loaded model.

        Updates the currently loaded model. First, tries to load the model from the local storage system. Secondly, tries to load the model from the provided model server configuration. Last, tries to load the model from the provided remote storage.
        """

        assert_choice("remote_storage", remote_storage, REMOTE_STORAGE_ENUM, True)

        if model_file is None and model_server is None and remote_storage is None:
            model_file = "models/"

        url = self.get_endpoint("/model")

        return self.put_request(
            url,
            json={
                "model_file": model_file,
                "model_server": model_server,
                "remote_storage": remote_storage,
            },
        )

    def unload_model(self):
        # type: () -> ReturnT

        url = self.get_endpoint("/model")

        return self.delete_request(url)


class _RasaRestWebhook(RasaABC[ReturnT]):
    def health(self):
        # type: () -> ReturnT

        url = self.get_endpoint("/webhooks/rest/")

        return self.get_request(url)

    def send_message(self, message):
        # type: (str, ) -> ReturnT

        url = self.get_endpoint("/webhooks/rest/webhook")

        return self.post_request(
            url,
            json={
                "sender": self.sender,
                "message": message,
            },
        )


class _RasaCallbackWebhook(RasaABC[ReturnT]):
    def send_message(self, message):
        # type: (str, ) -> ReturnT

        url = self.get_endpoint("/webhooks/callback/webhook")

        return self.post_request(
            url,
            json={
                "sender": self.sender,
                "message": message,
            },
        )


class RasaRestConversations(RasaRest, _RasaRestConversations[SyncReturnT]):
    pass


class RasaRestModel(RasaRest, _RasaRestModel[SyncReturnT]):
    pass


class RasaRestWebhook(RasaRest, _RasaRestWebhook[SyncReturnT]):
    pass


class RasaCallbackWebhook(RasaRest, _RasaCallbackWebhook[SyncReturnT]):
    pass


class RasaRestConversationsAsync(RasaRestAsync, _RasaRestConversations[AsyncReturnT]):
    pass


class RasaRestModelAsync(RasaRestAsync, _RasaRestModel[AsyncReturnT]):
    pass


class RasaRestWebhookAsync(RasaRestAsync, _RasaRestWebhook[AsyncReturnT]):
    pass


class RasaCallbackWebhookAsync(RasaRestAsync, _RasaCallbackWebhook[AsyncReturnT]):
    pass
