from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from features.ndc.server.governance import NDCGovernanceController


class NDCRolloutReadinessController:
    def __init__(self, base_dir: str | Path, *, governance: NDCGovernanceController) -> None:
        self.base_dir = Path(base_dir)
        self.governance = governance
        self.rollout_dir = self.base_dir / "governance"
        self.pilot_review_path = self.rollout_dir / "pilot_review.json"
        self.rollout_dir.mkdir(parents=True, exist_ok=True)

    def refresh_review(self, dashboard: dict[str, Any] | None = None) -> dict[str, Any]:
        current_dashboard = dashboard or self.governance.build_dashboard()
        review = self.build_pilot_review(current_dashboard)
        self.pilot_review_path.write_text(
            json.dumps(review, indent=2, ensure_ascii=True, sort_keys=True),
            encoding="utf-8",
        )
        return review

    def build_pilot_review(self, dashboard: dict[str, Any]) -> dict[str, Any]:
        raw = dashboard["raw_ingest"]
        normalized = dashboard["normalized"]
        derived = dashboard["derived"]
        alerts = dashboard["alerts"]

        readiness_status = "rollout_ready"
        blocking_reasons: list[str] = []
        if any(alert["severity"] == "error" for alert in alerts):
            readiness_status = "not_ready"
            blocking_reasons.extend(alert["code"] for alert in alerts if alert["severity"] == "error")
        elif any(alert["severity"] == "warning" for alert in alerts):
            readiness_status = "pilot_ready"
            blocking_reasons.extend(alert["code"] for alert in alerts if alert["severity"] == "warning")

        semantic_usefulness = self._semantic_usefulness_assessment(derived)
        taxonomy_adjustments = self._taxonomy_adjustments(
            raw=raw,
            normalized=normalized,
            derived=derived,
        )
        rollout_checks = {
            "payload_volume": {
                "accepted_event_count": raw["accepted_event_count"],
                "normalized_event_count": normalized["event_count"],
                "derived_document_count": derived["document_count"],
            },
            "duplication": {
                "duplicate_rate": raw["duplicate_rate"],
                "rejected_duplicate_chunks": derived["rejected_flag_counts"].get("duplicate_content", 0),
            },
            "semantic_usefulness": semantic_usefulness,
        }
        return {
            "generated_at": dashboard["generated_at"],
            "readiness_status": readiness_status,
            "blocking_reasons": blocking_reasons,
            "pilot_scope": "limited_internal",
            "rollout_checks": rollout_checks,
            "taxonomy_adjustments": taxonomy_adjustments,
            "next_steps": self._next_steps(readiness_status, taxonomy_adjustments, alerts),
        }

    def _semantic_usefulness_assessment(self, derived: dict[str, Any]) -> dict[str, Any]:
        average_quality = float(derived.get("average_quality_score", 0.0) or 0.0)
        documents_by_type = dict(derived.get("documents_by_type", {}))
        judgment = "strong"
        if average_quality < 0.7:
            judgment = "weak"
        elif average_quality < 0.82:
            judgment = "mixed"
        return {
            "average_quality_score": average_quality,
            "judgment": judgment,
            "documents_by_type": documents_by_type,
            "rejected_rate": derived.get("rejected_rate", 0.0),
        }

    def _taxonomy_adjustments(
        self,
        *,
        raw: dict[str, Any],
        normalized: dict[str, Any],
        derived: dict[str, Any],
    ) -> list[dict[str, Any]]:
        recommendations: list[dict[str, Any]] = []
        rejected_flags = derived.get("rejected_flag_counts", {})
        event_distribution = normalized.get("event_family_distribution", {})

        if float(raw.get("duplicate_rate", 0.0) or 0.0) >= 0.2:
            recommendations.append(
                {
                    "priority": "high",
                    "area": "dedupe",
                    "recommendation": "Collapse repetitive client events before enqueue when event_id/content_hash semantics already imply duplication.",
                }
            )
        if int(rejected_flags.get("low_signal_tool_chunk", 0) or 0) > 0:
            recommendations.append(
                {
                    "priority": "high",
                    "area": "tool_taxonomy",
                    "recommendation": "Tighten tool event taxonomy so helper/open actions without meaningful results do not emit downstream semantic chunks.",
                }
            )
        if int(rejected_flags.get("duplicate_content", 0) or 0) > 0:
            recommendations.append(
                {
                    "priority": "medium",
                    "area": "note_taxonomy",
                    "recommendation": "Coalesce note events that only restate unchanged semantic content to reduce duplicate derived note chunks.",
                }
            )
        if int(event_distribution.get("snapshot", 0) or 0) == 0:
            recommendations.append(
                {
                    "priority": "medium",
                    "area": "snapshot_coverage",
                    "recommendation": "Ensure snapshot checkpoints are present during pilot so reconstruction fidelity can be assessed before wider rollout.",
                }
            )
        return recommendations

    def _next_steps(
        self,
        readiness_status: str,
        taxonomy_adjustments: list[dict[str, Any]],
        alerts: list[dict[str, Any]],
    ) -> list[str]:
        if readiness_status == "not_ready":
            return [
                "Resolve error-severity governance alerts before expanding beyond the internal pilot.",
                "Replay stored events after fixes and regenerate the pilot review.",
            ]
        if taxonomy_adjustments:
            return [
                "Review the proposed taxonomy adjustments against pilot traffic.",
                "Keep the feature flag enabled only for the internal pilot cohort until the adjustments are accepted.",
            ]
        if alerts:
            return [
                "Continue the internal pilot and monitor warnings until payload volume and semantic quality stabilize.",
            ]
        return [
            "Operational signals are stable enough for broader rollout planning.",
            "Keep dashboards and pilot review in place during the first wider rollout wave.",
        ]
