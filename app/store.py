"""In-memory bin + request store with a bounded ring buffer per bin (testable)."""
from __future__ import annotations
import secrets
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Deque, Dict, List, Optional


@dataclass
class CapturedRequest:
    id: int
    method: str
    path: str
    query: Dict[str, str]
    headers: Dict[str, str]
    body: str
    ts: str

    def to_dict(self) -> dict:
        return asdict(self)


class BinStore:
    def __init__(self, max_per_bin: int = 50) -> None:
        self._bins: Dict[str, Deque[CapturedRequest]] = {}
        self._seq: Dict[str, int] = {}
        self.max_per_bin = max_per_bin

    def create_bin(self) -> str:
        bin_id = secrets.token_hex(4)
        self._bins[bin_id] = deque(maxlen=self.max_per_bin)
        self._seq[bin_id] = 0
        return bin_id

    def exists(self, bin_id: str) -> bool:
        return bin_id in self._bins

    def capture(self, bin_id: str, *, method: str, path: str,
                query: Dict[str, str], headers: Dict[str, str], body: str, ts: str) -> CapturedRequest:
        if bin_id not in self._bins:
            raise KeyError(bin_id)
        self._seq[bin_id] += 1
        req = CapturedRequest(self._seq[bin_id], method, path, query, headers, body, ts)
        self._bins[bin_id].append(req)
        return req

    def requests(self, bin_id: str, since: int = 0) -> List[CapturedRequest]:
        if bin_id not in self._bins:
            raise KeyError(bin_id)
        return [r for r in self._bins[bin_id] if r.id > since]

    def clear(self, bin_id: str) -> None:
        if bin_id in self._bins:
            self._bins[bin_id].clear()
