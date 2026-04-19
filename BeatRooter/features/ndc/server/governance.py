from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import shutil
import sqlite3
from typing import Any

from features.ndc.core.schema import (
    SUPPORTED_NDC_SCHEMA_VERSIONS,
    migration_expectations_for,
    validate_ndc_event,
)
from features.ndc.server.normalized_store import NDCNormalizedStore


@dataclass(frozen=True)
class NDCRetentionPolicy:
    raw_retention_days: int = 30
    network_retention_days: int = 30
    normalized_retention_days: int = 180
    derived_retention_days: int = 90
    governance_report_retention_days: int = 30

    def to_dict(self) -> dict[str, int]:
        return {
            "raw_retention_days": self.raw_retention_days,
            "network_retention_days": self.network_retention_days,
            "normalized_retention_days": self.normalized_retention_days,
            "derived_retention_days": self.derived_retention_days,
            "governance_report_retention_days": self.governance_report_retention_days,
        }


class NDCSensitiveDataMinimizer:
    _PRIVATE_KEY_RE = re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        re.IGNORECASE | re.DOTALL,
    )
    _EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
    _BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._\-+/=]{8,}\b", re.IGNORECASE)
    _SECRET_ASSIGNMENT_RE = re.compile(
        r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret)\b\s*[:=]\s*([^\s,;]+)"
    )

    def sanitize_text(self, text: str) -> str:
        sanitized = str(text or "")
        sanitized = self._PRIVATE_KEY_RE.sub("[redacted_private_key]", sanitized)
        sanitized = self._EMAIL_RE.sub("[redacted_email]", sanitized)
        sanitized = self._BEARER_RE.sub("Bearer [redacted_token]", sanitized)
        sanitized = self._SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=[redacted]", sanitized)
        return sanitized

    def sanitize_json_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                str(key): self.sanitize_json_value(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self.sanitize_json_value(item) for item in value]
        if isinstance(value, tuple):
            return [self.sanitize_json_value(item) for item in value]
        if isinstance(value, str):
            return self.sanitize_text(value)
        return value


class NDCGovernanceController:
    def __init__(
        self,
        base_dir: str | Path,
        *,
        normalized_store: NDCNormalizedStore,
        derived_pipeline: Any,
        retention_policy: NDCRetentionPolicy | None = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.normalized_store = normalized_store
        self.derived_pipeline = derived_pipeline
        self.retention_policy = retention_policy or NDCRetentionPolicy()
        self.governance_dir = self.base_dir / "governance"
        self.dashboard_path = self.governance_dir / "dashboard.json"
        self.alerts_path = self.governance_dir / "alerts.json"
        self.retention_policy_path = self.governance_dir / "retention_policy.json"
        self.schema_report_path = self.governance_dir / "schema_migration_report.json"
        self.governance_dir.mkdir(parents=True, exist_ok=True)

    def refresh_reports(self) -> dict[str, Any]:
        dashboard = self.build_dashboard()
        self._write_json(self.retention_policy_path, self.retention_policy.to_dict())
        self._write_json(self.schema_report_path, dashboard["schema_migration"])
        self._write_json(self.alerts_path, dashboard["alerts"])
        self._write_json(self.dashboard_path, dashboard)
        return dashboard

    def build_dashboard(self) -> dict[str, Any]:
        raw_metrics = self._build_raw_metrics()
        normalized_metrics = self._build_normalized_metrics()
        derived_metrics = self._build_derived_metrics()
        schema_migration = self.validate_schema_migrations()
        alerts = self._build_alerts(
            raw_metrics=raw_metrics,
            normalized_metrics=normalized_metrics,
            derived_metrics=derived_metrics,
            schema_migration=schema_migration,
        )
        return {
            "generated_at": _utc_now(),
            "retention_policy": self.retention_policy.to_dict(),
            "raw_ingest": raw_metrics,
            "normalized": normalized_metrics,
            "derived": derived_metrics,
            "schema_migration": schema_migration,
            "alerts": alerts,
        }

    def validate_schema_migrations(self) -> dict[str, Any]:
        with sqlite3.connect(self.normalized_store.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT event_id, family, action, source_id, project_id, created_at, schema_version,
                       payload_json, content_hash, sequence_number
                FROM events
                ORDER BY sequence_number ASC, created_at ASC, event_id ASC
                """
            ).fetchall()

        schema_versions_seen: dict[str, int] = {}
        failed_event_ids: list[str] = []
        failure_details: list[dict[str, str]] = []

        for row in rows:
            schema_version = str(row["schema_version"])
            schema_versions_seen[schema_version] = schema_versions_seen.get(schema_version, 0) + 1
            payload = json.loads(row["payload_json"])
            event = {
                "event_id": row["event_id"],
                "family": row["family"],
                "action": row["action"],
                "source_id": row["source_id"],
                "project_id": row["project_id"],
                "created_at": row["created_at"],
                "schema_version": schema_version,
                "payload": payload,
                "content_hash": row["content_hash"],
                "sequence_number": row["sequence_number"],
            }
            try:
                validate_ndc_event(event)
            except Exception as exc:
                failed_event_ids.append(str(row["event_id"]))
                failure_details.append(
                    {
                        "event_id": str(row["event_id"]),
                        "detail": str(exc),
                    }
                )

        unsupported_versions = sorted(
            version for version in schema_versions_seen if version not in SUPPORTED_NDC_SCHEMA_VERSIONS
        )
        expectations = {
            version: migration_expectations_for(version)
            for version in schema_versions_seen
            if version in SUPPORTED_NDC_SCHEMA_VERSIONS
        }
        return {
            "checked_event_count": len(rows),
            "schema_versions_seen": schema_versions_seen,
            "unsupported_schema_versions": unsupported_versions,
            "failed_event_count": len(failed_event_ids),
            "failed_event_ids": failed_event_ids,
            "failure_details": failure_details,
            "migration_expectations": expectations,
        }

    def apply_retention_policy(
        self,
        *,
        now: str | None = None,
        prune: bool = False,
    ) -> dict[str, Any]:
        reference_time = _parse_timestamp(now) if now is not None else datetime.now(timezone.utc)
        raw_cutoff = reference_time - timedelta(days=self.retention_policy.raw_retention_days)
        network_cutoff = reference_time - timedelta(days=self.retention_policy.network_retention_days)
        normalized_cutoff = reference_time - timedelta(days=self.retention_policy.normalized_retention_days)
        derived_cutoff = reference_time - timedelta(days=self.retention_policy.derived_retention_days)
        governance_cutoff = reference_time - timedelta(days=self.retention_policy.governance_report_retention_days)

        raw_result = self._prune_jsonl(
            self.base_dir / "raw_ingest_batches.jsonl",
            timestamp_field="received_at",
            cutoff=raw_cutoff,
            prune=prune,
        )
        raw_result["expired_indexed_events"] = self._prune_raw_index(cutoff=raw_cutoff, prune=prune)
        network_result = self._prune_jsonl(
            self.base_dir / "network_observations.jsonl",
            timestamp_field="observed_at",
            cutoff=network_cutoff,
            prune=prune,
        )
        normalized_result = self._prune_normalized_store(cutoff=normalized_cutoff, prune=prune)
        derived_result = self._prune_derived_documents(cutoff=derived_cutoff, prune=prune)
        governance_result = self._prune_governance_reports(cutoff=governance_cutoff, prune=prune)

        result = {
            "applied_at": _utc_now(),
            "prune": prune,
            "raw": raw_result,
            "network": network_result,
            "normalized": normalized_result,
            "derived": derived_result,
            "governance": governance_result,
        }
        if prune:
            self.refresh_reports()
        return result

    def _build_raw_metrics(self) -> dict[str, Any]:
        batches = self._read_jsonl(self.base_dir / "raw_ingest_batches.jsonl")
        network = self._read_jsonl(self.base_dir / "network_observations.jsonl")
        accepted_count = sum(int(batch.get("accepted_count", 0) or 0) for batch in batches)
        duplicate_count = sum(int(batch.get("duplicate_count", 0) or 0) for batch in batches)
        total = accepted_count + duplicate_count
        return {
            "receipt_count": len(batches),
            "accepted_event_count": accepted_count,
            "duplicate_event_count": duplicate_count,
            "duplicate_rate": round((duplicate_count / total), 3) if total else 0.0,
            "network_observation_count": len(network),
            "latest_receipt_at": max((batch.get("received_at") for batch in batches), default=None),
        }

    def _build_normalized_metrics(self) -> dict[str, Any]:
        with sqlite3.connect(self.normalized_store.db_path) as connection:
            source_count = int(connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0] or 0)
            project_count = int(connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0] or 0)
            event_count = int(connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] or 0)
            family_rows = connection.execute(
                "SELECT family, COUNT(*) FROM events GROUP BY family ORDER BY family"
            ).fetchall()
            schema_rows = connection.execute(
                "SELECT schema_version, COUNT(*) FROM events GROUP BY schema_version ORDER BY schema_version"
            ).fetchall()
        return {
            "source_count": source_count,
            "project_count": project_count,
            "event_count": event_count,
            "event_family_distribution": {str(row[0]): int(row[1]) for row in family_rows},
            "schema_version_distribution": {str(row[0]): int(row[1]) for row in schema_rows},
        }

    def _build_derived_metrics(self) -> dict[str, Any]:
        manifests = list(self.base_dir.glob("derived_documents/*/*/manifest.json"))
        document_count = 0
        rejected_count = 0
        quality_scores: list[float] = []
        documents_by_type: dict[str, int] = {}
        rejected_flag_counts: dict[str, int] = {}

        for manifest_path in manifests:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for item in manifest.get("documents", []):
                document_count += 1
                document_type = str(item.get("document_type") or "unknown")
                documents_by_type[document_type] = documents_by_type.get(document_type, 0) + 1
                quality_scores.append(float(item.get("quality_score", 0.0) or 0.0))
            for item in manifest.get("rejected_documents", []):
                rejected_count += 1
                for flag in item.get("quality_flags", []):
                    key = str(flag)
                    rejected_flag_counts[key] = rejected_flag_counts.get(key, 0) + 1

        failure_count = len(self._read_jsonl(self.base_dir / "derived_document_failures.jsonl"))
        total_candidates = document_count + rejected_count
        return {
            "manifest_count": len(manifests),
            "document_count": document_count,
            "rejected_count": rejected_count,
            "rejected_rate": round((rejected_count / total_candidates), 3) if total_candidates else 0.0,
            "average_quality_score": round(sum(quality_scores) / len(quality_scores), 3) if quality_scores else 0.0,
            "documents_by_type": documents_by_type,
            "rejected_flag_counts": rejected_flag_counts,
            "failure_count": failure_count,
        }

    def _build_alerts(
        self,
        *,
        raw_metrics: dict[str, Any],
        normalized_metrics: dict[str, Any],
        derived_metrics: dict[str, Any],
        schema_migration: dict[str, Any],
    ) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []

        if float(raw_metrics["duplicate_rate"]) >= 0.25:
            alerts.append(
                self._alert(
                    "warning",
                    "duplicate_rate_high",
                    f"Duplicate ingest rate is {raw_metrics['duplicate_rate']}.",
                )
            )
        if derived_metrics["rejected_rate"] >= 0.3:
            alerts.append(
                self._alert(
                    "warning",
                    "derived_rejection_rate_high",
                    f"Derived rejection rate is {derived_metrics['rejected_rate']}.",
                )
            )
        if int(derived_metrics["failure_count"]) > 0:
            alerts.append(
                self._alert(
                    "error",
                    "derived_build_failures",
                    f"{derived_metrics['failure_count']} derived document rebuild failures were recorded.",
                )
            )
        if int(schema_migration["failed_event_count"]) > 0:
            alerts.append(
                self._alert(
                    "error",
                    "schema_replay_failed",
                    f"{schema_migration['failed_event_count']} stored events failed migration replay validation.",
                )
            )
        if schema_migration["unsupported_schema_versions"]:
            alerts.append(
                self._alert(
                    "error",
                    "unsupported_schema_versions",
                    "Unsupported schema versions were detected in normalized events.",
                    details={"versions": schema_migration["unsupported_schema_versions"]},
                )
            )
        if len(normalized_metrics["schema_version_distribution"]) > 1:
            alerts.append(
                self._alert(
                    "warning",
                    "multiple_schema_versions",
                    "Multiple schema versions are present in the normalized store.",
                    details={"distribution": normalized_metrics["schema_version_distribution"]},
                )
            )
        if normalized_metrics["project_count"] > 0 and derived_metrics["documents_by_type"].get("project_summary", 0) == 0:
            alerts.append(
                self._alert(
                    "warning",
                    "missing_project_summaries",
                    "Projects exist in the normalized store but no project summaries were derived.",
                )
            )
        return alerts

    def _prune_jsonl(
        self,
        path: Path,
        *,
        timestamp_field: str,
        cutoff: datetime,
        prune: bool,
    ) -> dict[str, Any]:
        records = self._read_jsonl(path)
        kept: list[dict[str, Any]] = []
        removed = 0
        for record in records:
            timestamp = record.get(timestamp_field)
            if timestamp and _parse_timestamp(str(timestamp)) < cutoff:
                removed += 1
                continue
            kept.append(record)

        if prune and path.exists():
            if kept:
                with path.open("w", encoding="utf-8") as handle:
                    for record in kept:
                        handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True))
                        handle.write("\n")
            else:
                path.unlink(missing_ok=True)

        return {"removed_count": removed, "kept_count": len(kept)}

    def _prune_normalized_store(self, *, cutoff: datetime, prune: bool) -> dict[str, Any]:
        cutoff_text = _format_timestamp(cutoff)
        with sqlite3.connect(self.normalized_store.db_path) as connection:
            event_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM events WHERE created_at < ?",
                    (cutoff_text,),
                ).fetchone()[0]
                or 0
            )
            project_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM projects WHERE last_seen_at < ?",
                    (cutoff_text,),
                ).fetchone()[0]
                or 0
            )
            source_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM sources WHERE last_seen_at < ?",
                    (cutoff_text,),
                ).fetchone()[0]
                or 0
            )
            if prune:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("DELETE FROM notes WHERE created_at < ?", (cutoff_text,))
                connection.execute("DELETE FROM tool_activity WHERE created_at < ?", (cutoff_text,))
                connection.execute("DELETE FROM snapshots WHERE created_at < ?", (cutoff_text,))
                connection.execute("DELETE FROM events WHERE created_at < ?", (cutoff_text,))
                connection.execute(
                    "DELETE FROM normalized_provenance WHERE event_id NOT IN (SELECT event_id FROM events)"
                )
                connection.execute("DELETE FROM projects WHERE last_seen_at < ?", (cutoff_text,))
                connection.execute("DELETE FROM sources WHERE last_seen_at < ?", (cutoff_text,))
                connection.commit()
        return {
            "expired_event_count": event_count,
            "expired_project_count": project_count,
            "expired_source_count": source_count,
        }

    def _prune_raw_index(self, *, cutoff: datetime, prune: bool) -> int:
        index_path = self.base_dir / "raw_ingest_index.sqlite3"
        if not index_path.exists():
            return 0
        cutoff_text = _format_timestamp(cutoff)
        with sqlite3.connect(index_path) as connection:
            expired_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM ingested_events WHERE received_at < ?",
                    (cutoff_text,),
                ).fetchone()[0]
                or 0
            )
            if prune:
                connection.execute(
                    "DELETE FROM ingested_events WHERE received_at < ?",
                    (cutoff_text,),
                )
                connection.commit()
        return expired_count

    def _prune_derived_documents(self, *, cutoff: datetime, prune: bool) -> dict[str, Any]:
        manifests = list(self.base_dir.glob("derived_documents/*/*/manifest.json"))
        removed_projects = 0
        for manifest_path in manifests:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            built_at = manifest.get("built_at")
            reference_time = _parse_timestamp(str(built_at)) if built_at else datetime.fromtimestamp(
                manifest_path.stat().st_mtime,
                tz=timezone.utc,
            )
            if reference_time < cutoff:
                removed_projects += 1
                if prune:
                    shutil.rmtree(manifest_path.parent, ignore_errors=True)
        return {"expired_project_document_sets": removed_projects}

    def _prune_governance_reports(self, *, cutoff: datetime, prune: bool) -> dict[str, Any]:
        removed = 0
        for path in self.governance_dir.glob("*.json"):
            modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            if modified_at < cutoff:
                removed += 1
                if prune:
                    path.unlink(missing_ok=True)
        return {"expired_report_count": removed}

    def _alert(
        self,
        severity: str,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "severity": severity,
            "code": code,
            "message": message,
        }
        if details:
            payload["details"] = details
        return payload

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def _write_json(self, path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")


def _parse_timestamp(value: str) -> datetime:
    normalized = str(value).strip().replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_now() -> str:
    return _format_timestamp(datetime.now(timezone.utc))
