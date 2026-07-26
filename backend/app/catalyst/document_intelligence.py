"""Truthful Catalyst File Store and Zia OCR adapter.

The REST calls mirror Catalyst's documented Python SDK operations: File Store
upload and ``zia.extract_optical_characters``.  This adapter intentionally
raises on unavailable configuration/provider failures; callers must never turn
those failures into synthetic OCR or a fabricated storage reference.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

from backend.app.db.catalyst import CatalystRestDatastore


class DocumentProviderError(RuntimeError):
    """A real Catalyst document operation did not complete."""


@dataclass(frozen=True)
class StoredFile:
    file_id: str
    file_name: str
    file_size: int


@dataclass(frozen=True)
class OcrResult:
    text: str
    confidence: float | None


class CatalystDocumentProvider:
    """Catalyst File Store + Zia OCR provider, backed by authenticated REST."""

    def __init__(self, datastore: CatalystRestDatastore, folder_id: str) -> None:
        if not folder_id:
            raise DocumentProviderError("CASECLOCK_DOCUMENT_FOLDER_ID is not configured.")
        self._datastore = datastore
        self._folder_id = folder_id

    @classmethod
    def from_env(cls) -> "CatalystDocumentProvider":
        return cls(CatalystRestDatastore.from_env(), os.environ.get("CASECLOCK_DOCUMENT_FOLDER_ID", ""))

    def store_file(self, filename: str, content_type: str, content: bytes) -> StoredFile:
        response = requests.post(
            f"{self._datastore.api_domain}/baas/v1/project/{self._datastore.project_id}/folder/{self._folder_id}/file",
            headers=self._datastore.headers(),
            files={"code": (filename, content, content_type)},
            data={"file_name": filename},
            timeout=self._datastore.timeout,
        )
        self._raise_for_provider_error(response, "Catalyst File Store upload")
        data = response.json().get("data") or {}
        file_id = data.get("id")
        if not file_id:
            raise DocumentProviderError("Catalyst File Store response did not include a file ID.")
        return StoredFile(str(file_id), str(data.get("file_name") or filename), int(data.get("file_size") or len(content)))

    def extract_optical_characters(self, filename: str, content_type: str, content: bytes) -> OcrResult:
        """Execute Catalyst Zia OCR (the SDK-equivalent extract_optical_characters operation)."""
        response = requests.post(
            f"{self._datastore.api_domain}/baas/v1/project/{self._datastore.project_id}/ml/ocr",
            headers=self._datastore.headers(),
            files={"image": (filename, content, content_type)},
            data={"language": "eng"},
            timeout=self._datastore.timeout,
        )
        self._raise_for_provider_error(response, "Catalyst Zia OCR")
        data = response.json().get("data") or {}
        text = data.get("text")
        if not isinstance(text, str):
            raise DocumentProviderError("Catalyst Zia OCR response did not include text.")
        raw_confidence = data.get("confidence")
        try:
            confidence = float(raw_confidence) if raw_confidence is not None else None
        except (TypeError, ValueError):
            confidence = None
        return OcrResult(text=text, confidence=confidence)

    @staticmethod
    def _raise_for_provider_error(response: requests.Response, operation: str) -> None:
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise DocumentProviderError(f"{operation} failed.") from exc
        payload: dict[str, Any] = response.json()
        if payload.get("status") != "success":
            raise DocumentProviderError(f"{operation} returned a non-success status.")
