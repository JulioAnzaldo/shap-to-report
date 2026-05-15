"""
OpenAIBackend: Calls gpt-4o-mini with vision input and structured output.

Implements the full pipeline:
  1. Encode SHAP image as base64 (if path provided)
  2. Compose prompt from event SHAP values + metadata + retrieved chunks
  3. Call OpenAI with structured JSON output (strict schema)
  4. Parse and validate response into SituationalReport
  5. On validation failure: append assistant message and retry once
  6. On second failure or low confidence: return degraded report
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from backend.backends.base import LLMBackend
from backend.schema.models import SituationalReport
from backend.schema.strict import to_strict_schema
from backend.validator.output_validator import OutputValidator, ValidationResult

load_dotenv(Path(__file__).parent.parent.parent / ".env")

MODEL = "gpt-4o-mini"
TEMPERATURE = 0
CONFIDENCE_THRESHOLD = 0.3

SYSTEM_PROMPT = """\
You are a spacecraft anomaly analysis assistant. Your role is to generate structured \
diagnostic reports based on SHAP (SHapley Additive exPlanations) attribution data \
and retrieved regulatory and historical context.

Rules you must follow:
1. Base every claim on the retrieved context provided. Do not invent regulatory citations.
2. Do NOT use prescriptive action verbs: verify, check, adjust, command, recommend, \
suggest, ensure. Use observational language only.
3. The operator_decision field must frame the situation for the operator to decide — \
it must not instruct them to take a specific action.
4. Set confidence to reflect genuine uncertainty. If attribution is diffuse \
(Gini coefficient < 0.3), confidence should be ≤ 0.65.
5. Populate provenance only with sources actually present in the retrieved context.
6. Respond with valid JSON matching the SituationalReport schema exactly.
7. primary_features must contain ONLY the features whose absolute SHAP value is at \
least 20% of the top feature's absolute value. For concentrated attribution \
(Gini > 0.5), this will typically be one or two features. Do NOT list all features.
8. The explanation field must use the FEATURE INTERPRETATION GUIDE to characterize \
the physical signal behavior (e.g. "a transient voltage dip" not "the min feature \
was dominant"). Then connect that behavior to a retrieved source by name. \
Never write sentences like "the min/max/mean feature contributed most" — \
translate the statistics into what they imply about the subsystem.
9. anomaly_type must reflect the channel and attribution pattern, not default to \
sensor_fault for every event. Use the channel prefix and SHAP feature pattern as \
evidence: D-channels with concentrated mean deviation → sensor_fault; \
A-channels with slope trend → attitude_anomaly; power-related channels → power_anomaly; \
diffuse multi-feature attribution with low ensemble agreement → unknown.
10. historical_precedent must be populated whenever a NASA Lessons Learned chunk \
appears in the retrieved context with relevance_score ≥ 0.65. Use the document title \
and section name from the retrieved chunk — do not leave it null if relevant \
historical context was retrieved.
11. operator_decision must be specific to this event's attribution pattern and \
channel. It must name the channel, the Gini coefficient or ensemble agreement ratio, \
and what aspect of the situation is available for operator judgment. \
Generic phrases like 'the operator may consider the implications' are not acceptable.\
"""

# Build the response_format once at module load
_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "SituationalReport",
        "schema": to_strict_schema(SituationalReport),
        "strict": True,
    },
}


def _encode_image(image_path: str) -> str:
    """Base64 encode a PNG image for the OpenAI vision API."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _format_retrieved_chunks(retrieved_context: dict[str, list[dict[str, Any]]]) -> str:
    """Format retrieved chunks into a readable block for the prompt."""
    lines: list[str] = []
    for corpus_name, chunks in retrieved_context.items():
        if not chunks:
            continue
        lines.append(f"\n=== {corpus_name.upper()} ===")
        for i, chunk in enumerate(chunks, 1):
            lines.append(
                f"[{i}] {chunk.get('source_body', corpus_name)} — "
                f"{chunk.get('document', '')} {chunk.get('section', '')}\n"
                f"    Score: {chunk.get('relevance_score', 0):.3f}\n"
                f"    {chunk.get('text', chunk.get('content', ''))}"
            )
    return "\n".join(lines) if lines else "\n(No context retrieved)"


def _build_initial_messages(event: dict[str, Any], retrieved_context: dict[str, list[dict[str, Any]]], image_b64: str | None,) -> list[dict[str, Any]]:
    """Build the initial messages list for the first API call."""
    # Format SHAP values prominently: they are the primary signal
    shap_values = event.get("shap_values", {})
    shap_block = "\n".join(
        f"  {ch}: {val:+.4f}" for ch, val in sorted(shap_values.items(), key=lambda x: -abs(x[1]))
    ) or "  (no SHAP values provided)"

    metadata_block = json.dumps(
        {k: v for k, v in event.items() if k not in ("shap_values", "shap_image_path", "channel_attributions")},
        indent=2,
    )

    # Subsystem context — use explicit fields if present, fall back to prefix inference
    chan_id = str(event.get("channel_id", ""))
    subsystem_name = event.get("subsystem") or {
        "P": "Power Subsystem",
        "R": "Radiation/RF Subsystem",
        "T": "Thermal Control Subsystem",
        "A": "Attitude Control Subsystem",
        "D": "Data Handling/Downlink",
        "E": "Electrical Power Subsystem",
        "F": "Fault Detection/Flag Channels",
        "G": "Guidance/Navigation",
    }.get(chan_id[0].upper() if chan_id else "", "Unknown Subsystem")
    param_desc = event.get("parameter_description", "")
    anomaly_class = event.get("anomaly_class", "unknown")
    subsystem_block = (
        f"SUBSYSTEM CONTEXT:\n"
        f"  Parameter: {chan_id} — {subsystem_name}\n"
        + (f"  Description: {param_desc}\n" if param_desc else "")
        + f"  Anomaly class: {anomaly_class} "
        f"({'isolated spike/dropout' if anomaly_class == 'point' else 'context-dependent deviation' if anomaly_class == 'contextual' else 'unknown'})\n"
        f"  Labeled anomaly window: indices "
        f"{event.get('labeled_anomaly_start', '?')}–{event.get('labeled_anomaly_end', '?')}"
    )
    # Build attribution block from structured attribution data
    attribution = event.get("attribution", {})
    feat_names = attribution.get("feature_names", [])
    feat_vals = attribution.get("feature_attributions", [])
    gini = attribution.get("attribution_concentration", None)
    if feat_names and feat_vals:
        paired = sorted(zip(feat_names, feat_vals), key=lambda x: -abs(x[1]))
        attribution_block = "\n".join(f"  {n}: {v:+.4f}" for n, v in paired)
        if gini is not None:
            attribution_block += f"\n  Gini (concentration): {gini:.4f}"
    else:
        attribution_block = shap_block

    # Physical interpretation guide — map feature patterns to signal behavior
    FEATURE_GUIDE = """\
FEATURE INTERPRETATION GUIDE (use this to reason about physical signal behavior):
  mean dominant (+) → sustained upward shift from baseline across the window
  mean dominant (-) → sustained downward shift / level drop from baseline
  min dominant (-)  → transient dip or dropout — signal briefly fell well below normal
  max dominant (+)  → transient spike — signal briefly exceeded normal range
  std dominant      → increased variability or noise in the signal
  slope dominant (+)→ gradual upward drift across the window
  slope dominant (-) → gradual downward drift / decay trend

Cross-reference with the subsystem role to characterize the physical behavior:
  Power + min dip     → transient voltage excursion below nominal band
  Power + max spike   → load surge or bus overvoltage transient
  Thermal + mean shift→ temperature drift outside nominal operating band
  Attitude + slope    → attitude drift or reaction wheel desaturation trend
  Data + max spike    → buffer overflow, bit error, or packet rate burst
  Fault/Flag + any    → FDIR trigger event or fault flag state change
  Electrical + std    → power conditioning instability or ripple
  Guidance + slope    → orbit determination drift or IMU bias accumulation"""

    context_block = _format_retrieved_chunks(retrieved_context)

    text_content = (
        f"FEATURE ATTRIBUTIONS (sorted by |magnitude|):\n{attribution_block}\n\n"
        f"{FEATURE_GUIDE}\n\n"
        f"{subsystem_block}\n\n"
        f"EVENT METADATA:\n{metadata_block}\n\n"
        f"RETRIEVED CONTEXT:{context_block}\n\n"
        "Generate a SituationalReport JSON for this event."
    )

    content: list[dict[str, Any]] = [{"type": "text", "text": text_content}]

    if image_b64:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_b64}",
                    "detail": "low",
                },
            }
        )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]


class OpenAIBackend(LLMBackend):
    """
    Production backend using gpt-4o-mini with vision and structured output.

    Retry logic mirrors Project 4: on ValidationError, append the assistant's
    bad response and a corrective user message, then call once more.
    On second failure or confidence below threshold, return a degraded report.
    """

    def __init__(self) -> None:
        self.client = OpenAI()
        self.validator = OutputValidator()

    def generate(self, event: dict[str, Any], retrieved_context: dict[str, list[dict[str, Any]]],) -> SituationalReport:
        event_id = str(event.get("event_id", "unknown"))

        # Encode SHAP image if path provided
        image_b64: str | None = None
        image_path = event.get("shap_image_path")
        if image_path and Path(image_path).exists():
            image_b64 = _encode_image(image_path)

        messages = _build_initial_messages(event, retrieved_context, image_b64)

        # First attempt
        raw, exc = self._call(messages)
        if exc:
            return SituationalReport(
                event_id=event_id,
                degraded_mode="llm_unavailable",
                refusal_reason=f"API call failed: {exc}",
            )

        report, error_msg = self._parse_and_validate(raw, event_id)

        if report is None:
            # Retry once; Append assistant message and corrective user message
            messages = messages + [
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": (
                        f"Your response failed validation:\n{error_msg}\n\n"
                        "Please return a corrected JSON that satisfies the schema."
                    ),
                },
            ]
            raw, exc = self._call(messages)
            if exc:
                return SituationalReport(
                    event_id=event_id,
                    degraded_mode="validation_failed",
                    refusal_reason=f"Retry API call failed: {exc}",
                )
            report, error_msg = self._parse_and_validate(raw, event_id)

        if report is None:
            return SituationalReport(
                event_id=event_id,
                degraded_mode="validation_failed",
                refusal_reason=f"Output failed validation after retry: {error_msg}",
            )

        # Confidence gate
        if report.confidence is not None and report.confidence < CONFIDENCE_THRESHOLD:
            return SituationalReport(
                event_id=event_id,
                degraded_mode="model_low_confidence",
                refusal_reason=(
                    f"Model confidence {report.confidence:.2f} is below threshold "
                    f"{CONFIDENCE_THRESHOLD}. Report withheld."
                ),
            )

        return report

    def _call(
        self, messages: list[dict[str, Any]]
    ) -> tuple[str, Exception | None]:
        """Make one API call. Returns (raw_content, exception_or_None)."""
        try:
            response = self.client.chat.completions.create(
                model = MODEL,
                temperature = TEMPERATURE,
                response_format = _RESPONSE_FORMAT,
                messages = messages,
            )
            return response.choices[0].message.content or "", None
        except Exception as exc:
            return "", exc

    def _parse_and_validate(
        self, raw: str, event_id: str
    ) -> tuple[SituationalReport | None, str | None]:
        """
        Parse raw JSON string into SituationalReport and run content validation.

        Returns (report, None) on success, (None, error_msg) on failure.
        """
        try:
            data = json.loads(raw)
            data["event_id"] = event_id
            data.setdefault("degraded_mode", "none")
            report = SituationalReport.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            return None, str(exc)

        result, violation = self.validator.validate(report)
        if result == ValidationResult.VALID:
            return report, None
        return None, f"Content validation: {violation}"
