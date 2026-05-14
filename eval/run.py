"""
eval/run.py — Main evaluation harness for shap-to-report.

Usage:
    python eval/run.py --backend mock
    python eval/run.py --backend openai
    python eval/run.py --backend mock --run-id my_run

Outputs to eval/results/<run_id>/
  - results.jsonl   : per-event results with scores
  - summary.txt     : aggregate metrics
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.backends.mock_backend import MockBackend
from backend.schema.models import SituationalReport
from backend.validator.output_validator import OutputValidator, ValidationResult

TEST_CASES_DIR = Path(__file__).parent / "test_cases"
RESULTS_DIR = Path(__file__).parent / "results"


def normalize_event(event: dict) -> dict:
    """
    Normalize a test-case event dict into the flat shape the backends expect.

    Test cases store SHAP as:
        event.attribution.feature_names  (list)
        event.attribution.feature_attributions  (list)

    OpenAIBackend reads:
        event["shap_values"]  (dict: feature_name → float)
        event["gini_coefficient"]  (float)
        event["mission"]  (str)
        event["subsystem"]  (str)

    This function adds those keys without mutating the original.
    """
    ev = dict(event)

    attribution = ev.get("attribution", {})
    names = attribution.get("feature_names", [])
    values = attribution.get("feature_attributions", [])

    if names and values and "shap_values" not in ev:
        ev["shap_values"] = dict(zip(names, values))

    if "gini_coefficient" not in ev:
        ev["gini_coefficient"] = attribution.get("attribution_concentration")

    # Map spacecraft → mission, channel_id → subsystem for prompt readability
    if "mission" not in ev:
        ev["mission"] = ev.get("spacecraft", "unknown")
    if "subsystem" not in ev:
        ev["subsystem"] = ev.get("channel_id", "unknown")

    return ev


def load_test_cases() -> list[dict]:
    """Load all JSON test cases from eval/test_cases/."""
    cases = []
    for p in sorted(TEST_CASES_DIR.glob("*.json")):
        with open(p) as f:
            cases.append(json.load(f))
    return cases


def score_report(report: SituationalReport, event: dict) -> dict:
    """
    Score a single report against ground truth embedded in the event.

    Returns a dict of boolean checks:
      schema_valid          — report parsed without error (always True here)
      no_prescriptive_verbs — validator passes prescriptive check
      top_feature_correct   — top primary_feature matches ground_truth_top_feature
      severity_correct      — severity matches ground_truth_severity
      anomaly_type_correct  — anomaly_type matches ground_truth_anomaly_type
      citation_grounded     — explanation citations fuzzy-match retrieved chunks
      is_refusal            — report is degraded (not a failure, just noted)
    """
    validator = OutputValidator()

    schema_valid = True

    # Prescriptive verb check
    v_result, _ = validator._check_prescriptive_verbs(report)
    no_prescriptive_verbs = v_result == ValidationResult.VALID

    is_refusal = report.degraded_mode != "none"

    if is_refusal:
        return {
            "schema_valid": schema_valid,
            "no_prescriptive_verbs": True,
            "top_feature_correct": None,
            "severity_correct": None,
            "anomaly_type_correct": None,
            "citation_grounded": None,
            "is_refusal": True,
            "composite_score": None,
        }

    # Top feature: first predicted feature matches ground truth
    gt_top = event.get("ground_truth_top_feature")
    pred_top = (report.primary_features or [None])[0]
    top_feature_correct = (pred_top == gt_top) if gt_top else True

    # Severity match
    gt_severity = event.get("ground_truth_severity")
    severity_correct = (report.severity == gt_severity) if gt_severity else True

    # Anomaly type match
    gt_type = event.get("ground_truth_anomaly_type")
    anomaly_type_correct = (report.anomaly_type == gt_type) if gt_type else True

    # Citation grounding — check explanation cites retrieved sources
    # We don't have retrieved_chunks here, so use provenance as proxy
    provenance_chunks = []
    if report.provenance:
        for p in report.provenance:
            provenance_chunks.append({
                "document": p.document,
                "section": p.section,
                "text": p.text or "",
            })
    grounding_violations = validator.check_citation_grounding(report, provenance_chunks)
    citation_grounded = len(grounding_violations) == 0

    checks = [schema_valid, no_prescriptive_verbs, top_feature_correct, severity_correct,
              anomaly_type_correct, citation_grounded]
    composite_score = sum(checks) / len(checks)

    return {
        "schema_valid": schema_valid,
        "no_prescriptive_verbs": no_prescriptive_verbs,
        "top_feature_correct": top_feature_correct,
        "severity_correct": severity_correct,
        "anomaly_type_correct": anomaly_type_correct,
        "citation_grounded": citation_grounded,
        "is_refusal": False,
        "composite_score": composite_score,
    }


def run_eval(backend_name: str, run_id: str) -> None:
    """Run the full eval loop and write results."""
    # Load backend
    if backend_name == "mock":
        backend = MockBackend()
    elif backend_name == "openai":
        try:
            from backend.backends.openai_backend import OpenAIBackend
            backend = OpenAIBackend()
        except Exception as e:
            print(f"Failed to load OpenAIBackend: {e}")
            sys.exit(1)
    else:
        print(f"Unknown backend: {backend_name}")
        sys.exit(1)

    test_cases = load_test_cases()
    if not test_cases:
        print(f"No test cases found in {TEST_CASES_DIR}")
        sys.exit(1)

    print(f"Running eval: backend={backend_name}, run_id={run_id}, cases={len(test_cases)}")

    results_path = RESULTS_DIR / run_id
    results_path.mkdir(parents=True, exist_ok=True)

    # Set up retriever for openai backend (gracefully skip if ChromaDB not populated)
    retriever = None
    if backend_name == "openai":
        try:
            from backend.rag.retriever import Retriever
            retriever = Retriever()
            print("  Retriever loaded (ChromaDB)")
        except Exception as e:
            print(f"  Warning: retriever unavailable ({e}), running with empty context")

    rows = []
    scores = []
    refusal_count = 0

    for case in test_cases:
        raw_event = case["event"]
        event = normalize_event(raw_event)

        # Build retrieved context
        retrieved_context: dict = {"regulations": [], "historicals": []}
        if retriever is not None:
            shap_values = event.get("shap_values", {})
            top_features = sorted(shap_values.items(), key=lambda x: -abs(x[1]))[:5]
            feature_str = ", ".join(f"{k} ({v:+.3f})" for k, v in top_features)
            query_text = (
                f"spacecraft anomaly: {event.get('archetype', '')} "
                f"subsystem={event.get('subsystem', '')} "
                f"mission={event.get('mission', '')} "
                f"top_features={feature_str}"
            )
            try:
                retrieved_context["regulations"] = retriever.query(
                    query_text=query_text,
                    source_bodies=["EU_AI_Act", "NASA_NPR"],
                    n_results=4,
                )
                retrieved_context["historicals"] = retriever.query(
                    query_text=query_text,
                    source_bodies=["NASA_Lessons_Learned"],
                    n_results=3,
                )
            except Exception as e:
                print(f"    Retrieval failed for {raw_event['event_id']}: {e}")

        report = backend.generate(event, retrieved_context)
        score_dict = score_report(report, raw_event)

        # Save full report JSON for inspection
        report_path = results_path / f"{raw_event['event_id']}_report.json"
        report_path.write_text(
            json.dumps(report.model_dump(), indent=2, default=str),
            encoding="utf-8",
        )

        row = {
            "event_id": raw_event["event_id"],
            "channel_id": raw_event.get("channel_id", ""),
            "archetype": raw_event.get("archetype", ""),
            "degraded_mode": report.degraded_mode,
            "anomaly_type": report.anomaly_type,
            "severity": report.severity,
            "confidence": report.confidence,
            **score_dict,
        }
        rows.append(row)

        if score_dict["is_refusal"]:
            refusal_count += 1
        elif score_dict["composite_score"] is not None:
            scores.append(score_dict["composite_score"])

        status = "REFUSAL" if score_dict["is_refusal"] else f"{score_dict['composite_score']:.2f}"
        print(f"  {event['event_id']:20s}  {status}")

    # Write per-row CSV
    csv_path = results_path / "results.csv"
    if rows:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    # Write summary
    n_scored = len(scores)
    n_total = len(test_cases)
    mean_score = sum(scores) / n_scored if n_scored else 0.0

    summary_lines = [
        f"Run ID:          {run_id}",
        f"Backend:         {backend_name}",
        f"Timestamp:       {datetime.now(timezone.utc).isoformat()}",
        f"Total events:    {n_total}",
        f"Refusals:        {refusal_count}",
        f"Scored events:   {n_scored}",
        f"Mean composite:  {mean_score:.4f}",
        "",
        "Per-check averages (scored events only):",
    ]

    check_keys = ["schema_valid", "no_prescriptive_verbs", "top_feature_correct",
                  "severity_correct", "anomaly_type_correct", "citation_grounded"]
    for key in check_keys:
        vals = [r[key] for r in rows if r[key] is not None and not r["is_refusal"]]
        avg = sum(vals) / len(vals) if vals else 0.0
        summary_lines.append(f"  {key:30s}  {avg:.4f}")

    summary_text = "\n".join(summary_lines)
    print("\n" + summary_text)

    summary_path = results_path / "summary.txt"
    summary_path.write_text(summary_text + "\n")
    print(f"\nResults written to {results_path}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="shap-to-report eval harness")
    parser.add_argument(
        "--backend",
        choices=["mock", "openai"],
        default="mock",
        help="Backend to use for generation",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Run identifier (default: timestamp)",
    )
    args = parser.parse_args()

    run_id = args.run_id or f"{args.backend}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    run_eval(args.backend, run_id)
