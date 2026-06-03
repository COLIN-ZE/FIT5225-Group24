"""Firestore file_hashes (GCP) with /tmp JSON fallback for local Lambda tests."""

from __future__ import annotations

import json
import os
import threading
from typing import Any

from config import FIRESTORE_PROJECT_ID, GOOGLE_APPLICATION_CREDENTIALS, USE_LOCAL_DB

_LOCAL_PATH = os.environ.get(
    "LOCAL_DB_PATH", "/tmp/aussie_upload_db.json"
)
_lock = threading.Lock()


class Database:
    def get_hash_record(self, sha256: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def put_hash_record(self, sha256: str, record: dict[str, Any]) -> None:
        raise NotImplementedError


class LocalDatabase(Database):
    def _read(self) -> dict[str, Any]:
        if not os.path.exists(_LOCAL_PATH):
            return {"hashes": {}}
        with open(_LOCAL_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return {"hashes": data.get("hashes", {})}

    def _write(self, data: dict[str, Any]) -> None:
        with open(_LOCAL_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_hash_record(self, sha256: str) -> dict[str, Any] | None:
        with _lock:
            return self._read().get("hashes", {}).get(sha256)

    def put_hash_record(self, sha256: str, record: dict[str, Any]) -> None:
        with _lock:
            data = self._read()
            data.setdefault("hashes", {})[sha256] = record
            self._write(data)


class FirestoreDatabase(Database):
    def __init__(self) -> None:
        from google.cloud import firestore

        self._client = firestore.Client(project=FIRESTORE_PROJECT_ID)

    def get_hash_record(self, sha256: str) -> dict[str, Any] | None:
        doc = self._client.collection("file_hashes").document(sha256).get()
        return doc.to_dict() if doc.exists else None

    def put_hash_record(self, sha256: str, record: dict[str, Any]) -> None:
        self._client.collection("file_hashes").document(sha256).set(record)


_db: Database | None = None


def get_database() -> Database:
    global _db
    if _db is not None:
        return _db
    if USE_LOCAL_DB or not FIRESTORE_PROJECT_ID:
        _db = LocalDatabase()
    else:
        if GOOGLE_APPLICATION_CREDENTIALS:
            os.environ.setdefault(
                "GOOGLE_APPLICATION_CREDENTIALS", GOOGLE_APPLICATION_CREDENTIALS
            )
        _db = FirestoreDatabase()
    return _db
