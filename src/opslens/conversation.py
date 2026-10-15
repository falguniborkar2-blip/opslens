"""In-memory conversation history with size and TTL limits."""

from __future__ import annotations

import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field

from .providers.base import Message


@dataclass
class Conversation:
    id: str
    messages: list[Message] = field(default_factory=list)
    updated: float = field(default_factory=time.monotonic)


class ConversationStore:
    def __init__(
        self, max_turns: int = 10, max_conversations: int = 1000, ttl_s: float = 3600.0
    ) -> None:
        self.max_turns = max_turns
        self.max_conversations = max_conversations
        self.ttl_s = ttl_s
        self._data: OrderedDict[str, Conversation] = OrderedDict()
        self._lock = threading.Lock()

    def get_or_create(self, conv_id: str | None) -> Conversation:
        with self._lock:
            self._evict()
            if conv_id and conv_id in self._data:
                self._data.move_to_end(conv_id)
                return self._data[conv_id]
            conv = Conversation(conv_id or uuid.uuid4().hex)
            self._data[conv.id] = conv
            return conv

    def get(self, conv_id: str) -> Conversation | None:
        with self._lock:
            self._evict()
            return self._data.get(conv_id)

    def append(self, conv: Conversation, user: str, assistant: str) -> None:
        with self._lock:
            conv.messages += [Message("user", user), Message("assistant", assistant)]
            conv.messages = conv.messages[-2 * self.max_turns :]
            conv.updated = time.monotonic()

    def _evict(self) -> None:
        now = time.monotonic()
        for cid in [c for c, v in self._data.items() if now - v.updated > self.ttl_s]:
            del self._data[cid]
        while len(self._data) > self.max_conversations:
            self._data.popitem(last=False)
