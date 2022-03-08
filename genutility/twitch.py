from __future__ import generator_stop

import json
import ssl
from typing import Callable, List, Optional, Tuple

from .http import URLRequest
from .ops import logical_xor


class StreamWatcher:
    def __init__(self, api):
        self.api = api
        self.followed_names = api.get_followed()
        self.followed_online = {userid: False for userid in self.followed_names.keys()}

    def watch(self, notify_started, notify_stopped):
        # type: (Callable[[str, str, Optional[str]], None], Callable[[str, str], None]) -> None

        user_ids = self.followed_names.keys()
        streams = self.api.get_streams(user_ids)
        online = streams.keys()
        offline = user_ids - online

        for user_id in online:
            if not self.followed_online[user_id]:
                self.followed_online[user_id] = True
                notify_started(user_id, self.followed_names[user_id], streams[user_id].get("title", None))

        for user_id in offline:
            if self.followed_online[user_id]:
                self.followed_online[user_id] = False
                notify_stopped(user_id, self.followed_names[user_id])


class TwitchAPI:

    base = "https://api.twitch.tv/helix/"
    login = "users"
    follows = "users/follows"
    streams = "streams?user_id={}"

    def __init__(
        self,
        client_id: str,
        userid: Optional[str] = None,
        username: Optional[str] = None,
        ssl_context: Optional[ssl.SSLContext] = None,
    ) -> None:

        if not logical_xor(userid, username):
            raise ValueError("Either the userid or the username must be given")

        self.client_id = client_id
        self.ssl_context = ssl_context

        if userid:
            self.userid = userid
        else:
            assert username
            self.userid = self.get_userid(username)

    def req(self, url, params):
        # type: (str, List[Tuple[str, str]]) -> dict

        qs = "&".join(k + "=" + v for k, v in params)
        data = URLRequest(url + "?" + qs, headers={"Client-ID": self.client_id}, context=self.ssl_context).load()
        return json.loads(data)

    def get_userid(self, username):
        # type: (str, ) -> str

        d = self.req(self.base + self.login, [("login", username)])
        return d["data"][0]["id"]

    def get_followed(self):
        d = self.req(self.base + self.follows, [("from_id", self.userid)])
        return {follow["to_id"]: follow["to_name"] for follow in d["data"]}

    def get_streams(self, user_ids):
        d = self.req(self.base + self.streams, [("user_id", user_id) for user_id in user_ids])
        ret = {stream["user_id"]: stream for stream in d["data"]}
        assert len(d["data"]) == len(ret), "More than one stream per user"
        return ret

    def watcher(self):
        # type: () -> StreamWatcher

        return StreamWatcher(self)
