"""
MockBackend — returns deterministic SituationalReports for testing.

Accepts AnomalyEvent (as dict or model). Cycles through 3 valid report
templates and fires a structured refusal for event IDs ending in 3, 6, or 9.
No API calls made. Used for smoke-testing the pipeline and eval harness.

Channel/feature names and anomaly windows are grounded in real SMAP labeled
anomaly data (labeled_anomalies.csv). Anomaly classes and windows:
  D-2: point anomaly, window [4319, 8536]
  A-9: contextual anomaly, window [4569, 8433]
  A-8: contextual anomaly, window [4569, 8374]
  D-3: point anomaly, window [5225, 8500]
"""
from __future__ import annotations

from typing import Any

from backend.backends.base import LLMBackend
from backend.schema.models import ProvenanceEntry, SituationalReport


_VALID_REPORTS: list[dict[str, Any]] = [
    # Template 0 — concentrated point anomaly, sensor_fault on D-2
    # Real SMAP D-2: point anomaly [4319, 8536], 8595 total values
    {
        "anomaly_type": "sensor_fault",
        "severity": "high",
        "primary_features": ["mean"],
        "explanation": (
            "Channel D-2 exhibits a sustained point anomaly beginning at index 4319 "
            "with attribution concentrated on the mean feature (Gini ≈ 0.74). "
            "The mean feature accounts for the dominant share of the anomaly signal, "
            "consistent with a sensor drift or bias fault. "
            "Per NASA Lessons Learned #691 (SOAR), anomalies of this type are classified "
            "by subsystem and mission effect — this pattern corresponds to a "
            "Subsystem/Instrument Degraded classification with non-negligible mission effect. "
            "EU AI Act Article 14 §4(a) requires that operators be enabled to monitor "
            "AI system operation and detect anomalies and unexpected performance."
        ),
        "confidence": 0.91,
        "ensemble_agreement_ratio": 1.0,
        "attribution_concentration": 0.74,
        "historical_precedent": (
            "NASA Lessons Learned #691 — SOAR system: point anomaly classification, "
            "Subsystem/Instrument Degraded, failure category Part Problem."
        ),
        "provenance": [
            ProvenanceEntry(
                source_body="EU_AI_Act",
                document="EU AI Act",
                section="Article 14, Paragraph 4",
                relevance_score=0.82,
            ),
            ProvenanceEntry(
                source_body="NASA_Lessons_Learned",
                document="NASA Lessons Learned #691 — Spacecraft Orbital Anomaly Report System",
                section="Anomaly Classification — Subsystems and Mission Effect",
                relevance_score=0.79,
            ),
            ProvenanceEntry(
                source_body="NASA_NPR",
                document="NASA NPR 8705.4A",
                section="Chapter 3, Section 3.1.3",
                relevance_score=0.65,
            ),
        ],
        "operator_assessment": (
            "Channel D-2 attribution is concentrated on the mean feature (Gini=0.74). "
            "Ensemble agreement is full (3/3 models). Confidence is 0.91. "
            "Anomaly window onset at index 4319 — sustained across 4217 samples."
        ),
        "operator_decision": (
            "The D-2 channel telemetry pattern is consistent with a sustained sensor fault. "
            "The attribution signal is unambiguous. "
            "The situation is available for operator review prior to the next contact window."
        ),
    },
    # Template 1 — mid spread contextual anomaly, power_anomaly on A-9
    # Real SMAP A-9: contextual anomaly [4569, 8433], 8434 total values
    {
        "anomaly_type": "power_anomaly",
        "severity": "medium",
        "primary_features": ["mean", "slope"],
        "explanation": (
            "Channel A-9 shows a contextual anomaly with moderate attribution spread "
            "across mean and slope features (Gini ≈ 0.42), suggesting a gradual trend "
            "deviation rather than an abrupt fault. The anomaly window onset at index 4569 "
            "is consistent with a slow power subsystem drift. "
            "NASA NPR 8705.4A Chapter 3 Section 3.1.3 classifies this mission profile "
            "as requiring moderate risk tolerance (Class C), where anomalies of this "
            "magnitude warrant documented investigation before relief from requirements "
            "is considered. "
            "EU AI Act Article 14 §4(b) notes the risk of automation bias — operators "
            "are expected to avoid over-reliance on this assessment without independent "
            "telemetry review."
        ),
        "confidence": 0.72,
        "ensemble_agreement_ratio": 0.67,
        "attribution_concentration": 0.42,
        "historical_precedent": (
            "NASA Lessons Learned #4057 — Spacecraft Single Phase AC Electrical Power: "
            "gradual phase imbalance producing anomalous sensor readings not attributable "
            "to the monitored component."
        ),
        "provenance": [
            ProvenanceEntry(
                source_body="NASA_NPR",
                document="NASA NPR 8705.4A",
                section="Chapter 3, Section 3.1.3",
                relevance_score=0.74,
            ),
            ProvenanceEntry(
                source_body="EU_AI_Act",
                document="EU AI Act",
                section="Article 14, Paragraph 4",
                relevance_score=0.69,
            ),
            ProvenanceEntry(
                source_body="NASA_Lessons_Learned",
                document="NASA Lessons Learned #4057 — Spacecraft Single Phase AC Electrical Power",
                section="Lesson Learned and Recommendation",
                relevance_score=0.66,
            ),
        ],
        "operator_assessment": (
            "Channel A-9 attribution is mid-range — mean and slope both contributing "
            "(Gini=0.42). Ensemble agreement is moderate (2/3 models). "
            "Contextual anomaly onset at index 4569."
        ),
        "operator_decision": (
            "The A-9 channel pattern is consistent with a gradual power subsystem drift. "
            "Attribution is not concentrated enough to isolate a single cause. "
            "The situation is available for trend analysis at next ground contact."
        ),
    },
    # Template 2 — diffuse contextual anomaly, attitude_anomaly on A-8
    # Real SMAP A-8: contextual anomaly [4569, 8374], 8375 total values
    {
        "anomaly_type": "attitude_anomaly",
        "severity": "low",
        "primary_features": ["mean", "std"],
        "explanation": (
            "Channel A-8 shows a contextual anomaly with diffuse attribution across "
            "mean and std features (Gini ≈ 0.08), with no single statistical signature "
            "dominating. The anomaly window onset at index 4569 mirrors A-9, suggesting "
            "a correlated multi-channel event. "
            "NASA Lessons Learned #6216 (MSL Lift Mishap) documents that anomalous "
            "sensor readings over twice the expected value are critical signals — "
            "however, in this case the diffuse attribution and low ensemble agreement "
            "indicate the signal does not meet that threshold. "
            "EU AI Act Article 14 §4(d) preserves the operator's right to disregard "
            "or override AI system output, which is appropriate given the low confidence "
            "of this assessment."
        ),
        "confidence": 0.55,
        "ensemble_agreement_ratio": 0.33,
        "attribution_concentration": 0.08,
        "historical_precedent": (
            "NASA Lessons Learned #6216 — MSL Mobility Assembly Lift Mishap: "
            "diffuse load cell readings that did not meet the threshold for immediate action."
        ),
        "provenance": [
            ProvenanceEntry(
                source_body="EU_AI_Act",
                document="EU AI Act",
                section="Article 14, Paragraph 4",
                relevance_score=0.71,
            ),
            ProvenanceEntry(
                source_body="NASA_Lessons_Learned",
                document="NASA Lessons Learned #6216 — MSL Mobility Assembly Lift Mishap",
                section="Lessons Learned",
                relevance_score=0.68,
            ),
            ProvenanceEntry(
                source_body="NASA_NPR",
                document="NASA NPR 8715.3E",
                section="Section 1.3.1",
                relevance_score=0.59,
            ),
        ],
        "operator_assessment": (
            "Channel A-8 attribution is diffuse (Gini=0.08). "
            "Only 1/3 ensemble models flagged this event. Confidence is 0.55. "
            "Contextual anomaly onset at index 4569 — correlated with A-9 window."
        ),
        "operator_decision": (
            "The A-8 channel pattern does not present a concentrated attribution signal. "
            "The low ensemble agreement and diffuse feature contributions are noted. "
            "The situation is within monitoring threshold for the current mission phase."
        ),
    },
]

_REFUSAL_REPORT: dict[str, Any] = {
    "degraded_mode": "insufficient_context_retrieval",
    "refusal_reason": (
        "No regulatory or historical chunks were retrieved above the similarity threshold "
        "for this event. Cannot produce a grounded report without retrieved context."
    ),
}


class MockBackend(LLMBackend):
    """
    Deterministic backend for testing.

    Events with event_id ending in '3', '6', or '9' return a refusal.
    All others cycle through the 3 valid report templates, which are grounded
    in real SMAP labeled anomaly data and the RAG corpus.
    """

    def generate(
        self,
        event: dict[str, Any],
        retrieved_context: dict[str, list[dict[str, Any]]],
    ) -> SituationalReport:
        event_id = str(event.get("event_id", "0"))

        # Trigger refusal for specific event IDs (simulates low retrieval similarity)
        last_char = event_id[-1] if event_id else "0"
        last_digit = last_char if last_char.isdigit() else "0"
        if last_digit in ("3", "6", "9"):
            return SituationalReport(
                event_id=event_id,
                **_REFUSAL_REPORT,
            )

        # Cycle through valid reports
        idx = int(last_digit) % len(_VALID_REPORTS)
        template = _VALID_REPORTS[idx]

        return SituationalReport(
            event_id=event_id,
            degraded_mode="none",
            **template,
        )
