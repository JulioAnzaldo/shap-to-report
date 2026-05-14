"""
OutputValidator — validates SituationalReport content beyond schema correctness.

Three-state result:
  VALID         — report passes all checks, safe to return
  INVALID_RETRY — fixable violation, trigger one retry with corrective message
  INVALID_REFUSE — unfixable or repeated violation, return degraded report

Checks performed (in order):
  1. Schema validity (Pydantic already enforces this upstream, belt-and-suspenders)
  2. Prescriptive action-verb check on explanation + operator_decision
  3. Citation grounding stub (always passes until corpus is wired in Day 4)
  4. Severity-magnitude consistency (high/critical requires confidence ≥ 0.5)
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Any

from backend.schema.models import SituationalReport


# Prescriptive verbs the model must not use in operator-facing text
_PRESCRIPTIVE_PATTERN = re.compile(
    r"\b(verify|check|adjust|command|recommend|suggest|ensure|must|should|need to|have to)\b",
    re.IGNORECASE,
)


class ValidationResult(Enum):
    VALID = "valid"
    INVALID_RETRY = "invalid_retry"
    INVALID_REFUSE = "invalid_refuse"


class OutputValidator:
    """
    Validates a SituationalReport for content correctness.

    Usage:
        validator = OutputValidator()
        result, violation = validator.validate(report)
    """

    def validate(self, report: SituationalReport) -> tuple[ValidationResult, str | None]:
        """
        Run all validation checks on a report.

        Args:
            report: A SituationalReport (may be degraded — degraded reports pass validation).

        Returns:
            (ValidationResult, violation_description_or_None)
        """
        # Degraded reports don't need content validation
        if report.degraded_mode != "none":
            return ValidationResult.VALID, None

        # Check 1: prescriptive verbs
        result, msg = self._check_prescriptive_verbs(report)
        if result != ValidationResult.VALID:
            return result, msg

        # Check 2: severity-magnitude consistency
        result, msg = self._check_severity_confidence(report)
        if result != ValidationResult.VALID:
            return result, msg

        # Check 3: primary_channels not empty for confident reports
        result, msg = self._check_channels_present(report)
        if result != ValidationResult.VALID:
            return result, msg

        return ValidationResult.VALID, None

    def _check_prescriptive_verbs(
        self, report: SituationalReport
    ) -> tuple[ValidationResult, str | None]:
        """Fail if prescriptive action verbs appear in operator-facing text."""
        fields_to_check = {
            "explanation": report.explanation or "",
            "operator_assessment": report.operator_assessment or "",
            "operator_decision": report.operator_decision or "",
        }
        for field_name, text in fields_to_check.items():
            match = _PRESCRIPTIVE_PATTERN.search(text)
            if match:
                return (
                    ValidationResult.INVALID_RETRY,
                    f"Prescriptive verb '{match.group()}' found in field '{field_name}'. "
                    f"Use observational language only.",
                )
        return ValidationResult.VALID, None

    def _check_severity_confidence(
        self, report: SituationalReport
    ) -> tuple[ValidationResult, str | None]:
        """High/critical severity requires confidence ≥ 0.5."""
        if report.severity in ("high", "critical"):
            if report.confidence is not None and report.confidence < 0.5:
                return (
                    ValidationResult.INVALID_RETRY,
                    f"Severity '{report.severity}' requires confidence ≥ 0.5, "
                    f"but got {report.confidence:.2f}. Revise severity or confidence.",
                )
        return ValidationResult.VALID, None

    def _check_channels_present(
        self, report: SituationalReport
    ) -> tuple[ValidationResult, str | None]:
        """Confident reports must name at least one primary feature."""
        if not report.primary_features:
            return (
                ValidationResult.INVALID_RETRY,
                "primary_features is empty. At least one SHAP-attributed feature is required.",
            )
        return ValidationResult.VALID, None

    def check_citation_grounding(
        self,
        report: SituationalReport,
        retrieved_chunks: list[dict[str, Any]],
        fuzzy_threshold: float = 0.72,
    ) -> list[str]:
        """
        Check that the explanation references sources actually present in retrieved chunks.

        Uses RapidFuzz token_set_ratio to match phrases in the explanation against
        retrieved chunk text. Returns a list of violation strings (empty = grounded).

        A violation is raised if the explanation contains a document/section reference
        (e.g. "NASA NPR 8705.4A") that does not fuzzy-match any retrieved chunk.
        """
        from rapidfuzz import fuzz

        if not report.explanation or not retrieved_chunks:
            return []

        violations: list[str] = []

        # Build a set of all retrieved source identifiers
        retrieved_refs: list[str] = []
        for chunk in retrieved_chunks:
            doc = chunk.get("document", "")
            section = chunk.get("section", "")
            text = chunk.get("text", "")
            if doc:
                retrieved_refs.append(doc)
            if section:
                retrieved_refs.append(section)
            if text:
                retrieved_refs.append(text[:200])  # first 200 chars for matching

        # Extract candidate citations from explanation — look for patterns like
        # "NASA NPR ...", "EU AI Act ...", "Article ...", "Lessons Learned ..."
        import re
        citation_patterns = [
            r"NASA\s+(?:NPR|Lessons?\s+Learned?|LL)\s+[\w\.\-]+",
            r"EU\s+AI\s+Act\s+Article\s+\d+",
            r"Article\s+\d+[,\s]",
            r"NPR\s+\d+\.\d+\w*",
        ]
        found_citations: list[str] = []
        for pattern in citation_patterns:
            found_citations.extend(re.findall(pattern, report.explanation, re.IGNORECASE))

        # For each found citation, check if it fuzzy-matches any retrieved ref
        for citation in found_citations:
            best_score = max(
                (fuzz.token_set_ratio(citation, ref) for ref in retrieved_refs),
                default=0,
            )
            if best_score < fuzzy_threshold * 100:
                violations.append(
                    f"Citation '{citation}' in explanation not found in retrieved context "
                    f"(best match score: {best_score:.0f}/100, threshold: {fuzzy_threshold * 100:.0f})"
                )

        return violations
