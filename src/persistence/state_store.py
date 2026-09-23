"""Atomic execution-state storage backed by state.json (T012)."""
from __future__ import annotations

import json
import os
import tempfile

from src.models import RunRecord, RunState


class StateStore:
    """Loads/saves RunState atomically (temp file + rename)."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.state = RunState()

    def load(self) -> RunState:
        try:
            with open(self.path, encoding="utf-8") as fh:
                self.state = RunState.model_validate(json.load(fh))
        except FileNotFoundError:
            self.state = RunState()
        return self.state

    def save(self) -> None:
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self.state.model_dump(), fh,
                          ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def get_last_id(self, source_id: str) -> int:
        return self.state.last_processed_id.get(source_id, 0)

    def set_last_id(self, source_id: str, post_id: int) -> None:
        current = self.state.last_processed_id.get(source_id, 0)
        self.state.last_processed_id[source_id] = max(current, post_id)

    def is_published(self, exact_hash: str) -> bool:
        return exact_hash in self.state.published_hashes

    def mark_published(self, exact_hash: str) -> None:
        if exact_hash not in self.state.published_hashes:
            self.state.published_hashes.append(exact_hash)

    def advance_cursor(self, steps: int = 1) -> int:
        self.state.distribution_cursor += steps
        return self.state.distribution_cursor

    def append_run(self, record: RunRecord) -> None:
        self.state.runs.append(record)
