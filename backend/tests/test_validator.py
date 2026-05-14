"""
Unit tests for OutputValidator.

Covers:
  - Valid report passes all checks
  - Each prescriptive verb triggers INVALID_RETRY
  - Severity-confidence mismatch triggers INVALID_RETRY
  - Empty channels triggers INVALID_RETRY
  - Degraded reports always pass
"""
from __future__ import annotations

import pytest

from backend.schema.models import ProvenanceEntry, SituationalReport
from backend.validator.output_validator import OutputValidator, ValidationResult


def _make_valid_report(**overrides) -> SituationalReport:
    """Build a minimal valid SituationalReport for testing."""
    defaults = dict(
        event_id="test_001",
        degraded_mode="none",
        anomaly_type="sensor_fault",
        severity="medium",
        primary_features=["mean", "std"],
        explanation="Channel D-2 shows a sharp deviation in the mean feature above nominal.",
        confidence=0.75,
        ensemble_agreement_ratio=0.80,
        attribution_concentration=0.65,
        historical_precedent=None,
        provenance=[
            ProvenanceEntry(
                source_body="EU_AI_Act",
                document="EU AI Act",
                section="Article 14",
                relevance_score=0.82,
            )
        ],
        operator_assessment="Channel D-2 attribution is concentrated on the mean feature.",
        operator_decision="Situation warrants operator review at next contact window.",
    )
    defaults.update(overrides)
    return SituationalReport(**defaults)


@pytest.fixture
def validator() -> OutputValidator:
    return OutputValidator()


class TestValidReport:
    def test_valid_report_passes(self, validator):
        report = _make_valid_report()
        result, msg = validator.validate(report)
        assert result == ValidationResult.VALID
        assert msg is None


class TestPrescriptiveVerbs:
    @pytest.mark.parametrize(
        "verb,field",
        [
            ("verify the heater status", "explanation"),
            ("check the battery temperature", "operator_assessment"),
            ("recommend immediate action", "operator_decision"),
            ("ensure the system is stable", "operator_decision"),
            ("adjust the heater setpoint", "explanation"),
            ("suggest a power cycle", "operator_assessment"),
            ("command the thruster to fire", "operator_decision"),
        ],
    )
    def test_prescriptive_verb_triggers_retry(self, validator, verb, field):
        report = _make_valid_report(**{field: f"Operator should {verb}."})
        result, msg = validator.validate(report)
        assert result == ValidationResult.INVALID_RETRY
        assert msg is not None
        assert field in msg

    def test_observational_language_passes(self, validator):
        report = _make_valid_report(
            explanation="Temperature sensors show a 12°C rise above nominal.",
            operator_assessment="Attribution is concentrated on heater channels.",
            operator_decision="Situation is within monitoring threshold.",
        )
        result, msg = validator.validate(report)
        assert result == ValidationResult.VALID


class TestSeverityConfidence:
    def test_high_severity_low_confidence_triggers_retry(self, validator):
        report = _make_valid_report(severity="high", confidence=0.45)
        result, msg = validator.validate(report)
        assert result == ValidationResult.INVALID_RETRY
        assert "confidence" in msg.lower()

    def test_critical_severity_low_confidence_triggers_retry(self, validator):
        report = _make_valid_report(severity="critical", confidence=0.30)
        result, msg = validator.validate(report)
        assert result == ValidationResult.INVALID_RETRY

    def test_high_severity_sufficient_confidence_passes(self, validator):
        report = _make_valid_report(severity="high", confidence=0.50)
        result, msg = validator.validate(report)
        assert result == ValidationResult.VALID

    def test_medium_severity_any_confidence_passes(self, validator):
        report = _make_valid_report(severity="medium", confidence=0.20)
        result, msg = validator.validate(report)
        assert result == ValidationResult.VALID


class TestChannelsPresent:
    def test_empty_channels_triggers_retry(self, validator):
        report = _make_valid_report(primary_features=[])
        result, msg = validator.validate(report)
        assert result == ValidationResult.INVALID_RETRY
        assert "feature" in msg.lower()

    def test_none_channels_triggers_retry(self, validator):
        report = _make_valid_report(primary_features=None)
        result, msg = validator.validate(report)
        assert result == ValidationResult.INVALID_RETRY


class TestDegradedReports:
    @pytest.mark.parametrize(
        "degraded_mode",
        [
            "insufficient_context_retrieval",
            "validation_failed",
            "model_low_confidence",
            "shap_unavailable",
            "llm_unavailable",
        ],
    )
    def test_degraded_report_always_passes(self, validator, degraded_mode):
        report = SituationalReport(
            event_id="test_refusal",
            degraded_mode=degraded_mode,
            refusal_reason="Test refusal.",
        )
        result, msg = validator.validate(report)
        assert result == ValidationResult.VALID
        assert msg is None


class TestMockBackend:
    def test_mock_backend_produces_valid_and_refusal(self):
        from backend.backends.mock_backend import MockBackend

        backend = MockBackend()

        # Non-refusal event
        report = backend.generate({"event_id": "evt_001"}, {})
        assert report.degraded_mode == "none"
        assert report.primary_features is not None

        # Refusal event (ends in 3)
        report = backend.generate({"event_id": "evt_003"}, {})
        assert report.degraded_mode != "none"
        assert report.refusal_reason is not None

    def test_mock_backend_cycles_reports(self):
        from backend.backends.mock_backend import MockBackend

        backend = MockBackend()
        ids = ["evt_001", "evt_002", "evt_004", "evt_005"]
        reports = [backend.generate({"event_id": eid}, {}) for eid in ids]
        assert all(r.degraded_mode == "none" for r in reports)
        # Should not all be identical (cycles through templates)
        anomaly_types = [r.anomaly_type for r in reports]
        assert len(set(anomaly_types)) > 1
