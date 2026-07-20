"""Catalyst Data Store backed repository for CaseClock.

This adapter keeps the API surface aligned with the in-memory repository while
loading rows from the real Catalyst tables created for the prototype.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import requests

from backend.app.core.clock.engine import ClockEngine
from backend.app.core.dependency.engine import DependencyEngine
from backend.app.core.escalation.engine import EscalationEngine
from backend.app.db.in_memory import InMemoryBackendRepository
from shared.contracts.api import DependencyResponse, DependencyStatus, EscalationResponse


SYSTEM_COLUMNS = {
    "ROWID",
    "CREATORID",
    "CREATEDTIME",
    "MODIFIEDTIME",
}


class CatalystBackendRepository(InMemoryBackendRepository):
    """Repository that reads/writes CaseClock data from Catalyst Data Store."""

    def __init__(
        self,
        catalyst_app: Any | None = None,
        reference_time: datetime | None = None,
    ) -> None:
        self.reference_time = reference_time or datetime.now(timezone.utc)
        if self.reference_time.tzinfo is None:
            self.reference_time = self.reference_time.replace(tzinfo=timezone.utc)

        self.clock_engine = ClockEngine(self.reference_time)
        self.dependency_engine = DependencyEngine(self.reference_time)
        self.escalation_engine = EscalationEngine(self.reference_time)

        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        self.manual_escalations: dict[str, EscalationResponse] = {}
        self.audit_events: list[dict[str, Any]] = []
        self.state_path = None
        self._rowids_by_table: dict[str, dict[str, str]] = {}

        self._app = catalyst_app or self._initialize_app()
        self._datastore = self._app.datastore()
        self._load_catalyst_tables()
        self._rebuild_indexes()

    def _initialize_app(self) -> Any:
        return CatalystRestApp.from_env()

    def _load_catalyst_tables(self) -> None:
        for row in self._iter_table("graph_nodes"):
            node = self._graph_node_from_row(row)
            if node:
                self.nodes.setdefault(str(node["id"]), node)

        self.edges = [edge for row in self._iter_table("graph_edges") if (edge := self._graph_edge_from_row(row))]

        for row in self._iter_table("cases"):
            node = self._entity_node_from_row(row, "Case")
            if node:
                self.nodes[str(node["id"])] = node

        for row in self._iter_table("clock_instances"):
            node = self._entity_node_from_row(row, "ClockInstance")
            if node:
                self.nodes[str(node["id"])] = node
                self._append_unique_edge("CASE_HAS_CLOCK", str(node.get("case_id", "")), str(node["id"]))

        for row in self._iter_table("dependencies"):
            node = self._entity_node_from_row(row, "Dependency")
            if node:
                self.nodes[str(node["id"])] = node
                self._append_unique_edge("CASE_HAS_DEPENDENCY", str(node.get("case_id", "")), str(node["id"]))

    def _iter_table(self, table_name: str) -> list[dict[str, Any]]:
        table = self._datastore.table(table_name)
        return [dict(row) for row in table.get_iterable_rows()]

    def _entity_node_from_row(self, row: dict[str, Any], entity_type: str) -> dict[str, Any] | None:
        cleaned = self._clean_row(row)
        node_id = cleaned.get("id")
        if not node_id:
            return None
        self._remember_rowid(entity_type, str(node_id), row)
        cleaned["entity_type"] = entity_type
        return cleaned

    def _graph_node_from_row(self, row: dict[str, Any]) -> dict[str, Any] | None:
        cleaned = self._clean_row(row)
        node_id = cleaned.get("id")
        entity_type = cleaned.get("entity_type")
        if not node_id or not entity_type:
            return None

        properties = self._json_dict(cleaned.get("properties_json"))
        properties.update({"id": str(node_id), "entity_type": str(entity_type)})
        return properties

    def _graph_edge_from_row(self, row: dict[str, Any]) -> dict[str, Any] | None:
        cleaned = self._clean_row(row)
        edge_type = cleaned.get("edge_type")
        source_id = cleaned.get("source_id")
        target_id = cleaned.get("target_id")
        if not edge_type or not source_id or not target_id:
            return None

        properties = self._json_dict(cleaned.get("properties_json"))
        return {
            **properties,
            "edge_type": str(edge_type),
            "source_id": str(source_id),
            "target_id": str(target_id),
            "storage_mode": str(cleaned.get("storage_mode") or "Stored"),
        }

    def _clean_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in row.items()
            if key not in SYSTEM_COLUMNS and value is not None
        }

    def _json_dict(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if not isinstance(value, str) or not value:
            return {}
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _remember_rowid(self, entity_type: str, entity_id: str, row: dict[str, Any]) -> None:
        rowid = row.get("ROWID")
        if not rowid:
            return
        table_name = {
            "Case": "cases",
            "ClockInstance": "clock_instances",
            "Dependency": "dependencies",
        }.get(entity_type)
        if table_name:
            self._rowids_by_table.setdefault(table_name, {})[entity_id] = str(rowid)

    def _append_unique_edge(self, edge_type: str, source_id: str, target_id: str) -> None:
        if not source_id or not target_id:
            return
        edge = {"edge_type": edge_type, "source_id": source_id, "target_id": target_id, "storage_mode": "Stored"}
        if edge not in self.edges:
            self.edges.append(edge)

    def update_dependency(self, dependency_id: str, status: DependencyStatus) -> DependencyResponse | None:
        dependency = super().update_dependency(dependency_id, status)
        if dependency is None:
            return None

        rowid = self._rowids_by_table.get("dependencies", {}).get(dependency_id)
        if rowid:
            update_payload: dict[str, Any] = {
                "ROWID": rowid,
                "status": dependency.status.value,
                "days_stale": dependency.days_stale,
            }
            resolved_at = self.nodes[dependency_id].get("resolved_at")
            if resolved_at:
                update_payload["resolved_at"] = self._catalyst_datetime(resolved_at)
            self._datastore.table("dependencies").update_row(update_payload)
        return dependency

    def _record_manual_escalation(self, dependency_node: dict[str, Any]) -> None:
        super()._record_manual_escalation(dependency_node)
        escalation_id = f"manual-esc-{dependency_node['id']}"
        escalation = self.manual_escalations.get(escalation_id)
        if escalation:
            self._datastore.table("escalations").insert_row(
                {
                    "id": escalation.id,
                    "case_id": escalation.case_id,
                    "triggered_at": escalation.triggered_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "reason": escalation.reason,
                    "routed_to_rank": escalation.routed_to_rank,
                    "routed_to_officer_id": escalation.routed_to_officer_id,
                    "resolved": escalation.resolved,
                }
            )

    def _audit(self, event_type: str, **details: Any) -> None:
        event = {
            "id": f"audit-{len(self.audit_events) + 1}",
            "event_type": event_type,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "details": details,
        }
        self.audit_events.append(event)
        try:
            self._datastore.table("audit_events").insert_row(
                {
                    "id": event["id"],
                    "event_type": event_type,
                    "occurred_at": self._catalyst_datetime(event["occurred_at"]),
                    "case_id": str(details.get("case_id") or ""),
                    "actor_role": str(details.get("role") or details.get("actor_role") or ""),
                    "details_json": json.dumps(details, separators=(",", ":")),
                }
            )
        except Exception:
            # API responses should keep working even if audit persistence is temporarily unavailable.
            return

    def _save_state(self) -> None:
        return

    def _catalyst_datetime(self, value: Any) -> str:
        if isinstance(value, datetime):
            parsed = value
        else:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d %H:%M:%S")


class CatalystRestApp:
    """Small adapter over Catalyst's REST API with the SDK-like methods we use."""

    def __init__(self, auth: dict[str, str], options: dict[str, str]) -> None:
        self._datastore = CatalystRestDatastore(auth, options)

    @classmethod
    def from_env(cls) -> "CatalystRestApp":
        auth = _json_env("CATALYST_AUTH")
        options = _json_env("CATALYST_OPTIONS")
        return cls(auth, options)

    def datastore(self) -> "CatalystRestDatastore":
        return self._datastore


class CatalystRestDatastore:
    def __init__(self, auth: dict[str, str], options: dict[str, str]) -> None:
        self.auth = auth
        self.options = options
        self.api_domain = str(options.get("api_domain") or "https://api.catalyst.zoho.in").rstrip("/")
        self.accounts_domain = str(options.get("accounts_domain") or "https://accounts.zoho.in").rstrip("/")
        self.project_id = str(options["project_id"])
        self.project_key = str(options["project_key"])
        self.environment = str(options.get("environment") or "Development")
        self.timeout = int(options.get("timeout_seconds") or os.getenv("CATALYST_HTTP_TIMEOUT_SECONDS") or 120)
        self._access_token: str | None = None

    def table(self, table_name: str) -> "CatalystRestTable":
        return CatalystRestTable(self, table_name)

    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Zoho-oauthtoken {self.access_token()}",
            "PROJECT_ID": self.project_key,
            "X-Catalyst-Environment": self.environment,
            "Environment": self.environment,
            "X-CATALYST-USER": "admin",
        }

    def access_token(self) -> str:
        if self._access_token:
            return self._access_token
        response = requests.post(
            f"{self.accounts_domain}/oauth/v2/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.auth["refresh_token"],
                "client_id": self.auth["client_id"],
                "client_secret": self.auth["client_secret"],
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise RuntimeError(f"Catalyst token refresh failed: {payload}")
        self._access_token = str(token)
        return self._access_token


class CatalystRestTable:
    def __init__(self, datastore: CatalystRestDatastore, table_name: str) -> None:
        self.datastore = datastore
        self.table_name = table_name

    def get_iterable_rows(self):
        next_token: str | None = None
        while True:
            params: dict[str, str | int] = {"max_rows": 200}
            if next_token:
                params["next_token"] = next_token
            payload = self._request("GET", params=params)
            yield from payload.get("data") or []
            next_token = payload.get("next_token")
            if not next_token:
                break

    def insert_row(self, row: dict[str, Any]) -> dict[str, Any]:
        payload = self._request("POST", json=[row])
        rows = payload.get("data") or []
        return dict(rows[0]) if rows else row

    def update_row(self, row: dict[str, Any]) -> dict[str, Any]:
        payload = self._request("PATCH", json=[row])
        rows = payload.get("data") or []
        return dict(rows[0]) if rows else row

    def _request(self, method: str, **kwargs: Any) -> dict[str, Any]:
        response = requests.request(
            method,
            f"{self.datastore.api_domain}/baas/v1/project/{self.datastore.project_id}/table/{self.table_name}/row",
            headers=self.datastore.headers(),
            timeout=self.datastore.timeout,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()


def _json_env(name: str) -> dict[str, str]:
    raw = os.getenv(name)
    if not raw:
        raise RuntimeError(f"{name} must be set for CASECLOCK_REPOSITORY=catalyst")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise RuntimeError(f"{name} must be a JSON object")
    return {str(key): str(value) for key, value in parsed.items()}
