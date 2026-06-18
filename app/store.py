"""In-memory bin + request store with a bounded ring buffer per bin (testable)."""
from __future__ import annotations
import secrets
from collections import OrderedDict, deque
from dataclasses import dataclass, asdict
from typing import Deque, Dict, List


@dataclass
class CapturedRequest:
    id: int
    method: str
    path: str
    query: Dict[str, str]
    headers: Dict[str, str]
    body: str
    ts: str
    ip: str = ""
    truncated: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


DEFAULT_RESPONSE = {"status": 200, "body": "", "content_type": "application/json"}


class BinStore:
    """Bins are LRU-evicted once `max_bins` is exceeded; each bin keeps the last
    `max_per_bin` requests; each captured body is capped at `max_body` bytes."""

    def __init__(self, max_per_bin: int = 50, max_bins: int = 1000, max_body: int = 65536) -> None:
        self._bins: "OrderedDict[str, Deque[CapturedRequest]]" = OrderedDict()
        self._seq: Dict[str, int] = {}
        self._responses: Dict[str, dict] = {}
        self.max_per_bin = max_per_bin
        self.max_bins = max_bins
        self.max_body = max_body

    def create_bin(self) -> str:
        bin_id = secrets.token_hex(4)
        self._bins[bin_id] = deque(maxlen=self.max_per_bin)
        self._seq[bin_id] = 0
        self._bins.move_to_end(bin_id)
        while len(self._bins) > self.max_bins:            # evict the least-recently-used bin
            old, _ = self._bins.popitem(last=False)
            self._seq.pop(old, None)
            self._responses.pop(old, None)
        return bin_id

    def exists(self, bin_id: str) -> bool:
        return bin_id in self._bins

    def capture(self, bin_id: str, *, method: str, path: str, query: Dict[str, str],
                headers: Dict[str, str], body: str, ts: str, ip: str = "") -> CapturedRequest:
        if bin_id not in self._bins:
            raise KeyError(bin_id)
        truncated = len(body) > self.max_body
        if truncated:
            body = body[: self.max_body]
        self._seq[bin_id] += 1
        req = CapturedRequest(self._seq[bin_id], method, path, query, headers, body, ts, ip, truncated)
        self._bins[bin_id].append(req)
        self._bins.move_to_end(bin_id)
        return req

    def requests(self, bin_id: str, since: int = 0) -> List[CapturedRequest]:
        if bin_id not in self._bins:
            raise KeyError(bin_id)
        self._bins.move_to_end(bin_id)
        return [r for r in self._bins[bin_id] if r.id > since]

    def clear(self, bin_id: str) -> None:
        if bin_id in self._bins:
            self._bins[bin_id].clear()

    # ----- per-bin configurable response -----
    def set_response(self, bin_id: str, *, status: int, body: str, content_type: str) -> None:
        if bin_id not in self._bins:
            raise KeyError(bin_id)
        self._responses[bin_id] = {"status": status, "body": body, "content_type": content_type}

    def reset_response(self, bin_id: str) -> None:
        self._responses.pop(bin_id, None)

    def response(self, bin_id: str) -> dict:
        return self._responses.get(bin_id, dict(DEFAULT_RESPONSE))

    def has_custom_response(self, bin_id: str) -> bool:
        return bin_id in self._responses
