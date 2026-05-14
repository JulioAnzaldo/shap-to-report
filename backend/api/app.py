"""
FastAPI application for shap-to-report.

Endpoints:
  POST /explain   — generate a SituationalReport for an event
  GET  /events    — list available test events
  GET  /health    — liveness check
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.cache import ReportCache
from backend.rag.retriever import Retriever
from backend.schema.models import SituationalReport

load_dotenv(Path(__file__).parent.parent.parent / ".env")

app = FastAPI(
    title="shap-to-report",
    description="RAG-grounded LLM pipeline for spacecraft anomaly report generation",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-load backends to avoid import errors when API key is missing
_backends: dict[str, Any] = {}

# Retriever is initialised once and reused across requests
_retriever: "Retriever | None" = None

# Disk cache — eliminates repeat API calls at temperature=0
_cache = ReportCache()


def _get_retriever() -> "Retriever":
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever

TEST_CASES_DIR = Path(__file__).parent.parent.parent / "eval" / "test_cases"


def _get_backend(name: str = "mock"):
    if name not in _backends:
        if name == "mock":
            from backend.backends.mock_backend import MockBackend
            _backends["mock"] = MockBackend()
        elif name == "openai":
            from backend.backends.openai_backend import OpenAIBackend
            _backends["openai"] = OpenAIBackend()
        else:
            raise ValueError(f"Unknown backend: {name}")
    return _backends[name]


def _load_event(event_id: str) -> dict[str, Any] | None:
    """Load a test event by ID from eval/test_cases/."""
    for p in TEST_CASES_DIR.glob("*.json"):
        with open(p) as f:
            case = json.load(f)
        if case["event"]["event_id"] == event_id:
            return case["event"]
    return None


class ExplainRequest(BaseModel):
    event_id: str
    source_bodies: list[str] = []
    backend: Literal["mock", "openai"] = "mock"
    force_refresh: bool = False


class ExplainResponse(BaseModel):
    report: SituationalReport
    cached: bool = False


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/cache/stats")
def cache_stats() -> dict[str, Any]:
    """Return cache statistics."""
    return _cache.stats()


@app.delete("/cache")
def clear_cache() -> dict[str, Any]:
    """Clear all cached reports."""
    count = _cache.clear_all()
    return {"cleared": count}


@app.get("/events")
def list_events() -> dict[str, list[dict[str, Any]]]:
    """Return a list of available test events with basic metadata."""
    events = []
    for p in sorted(TEST_CASES_DIR.glob("*.json")):
        with open(p) as f:
            case = json.load(f)
        ev = case["event"]
        events.append(
            {
                "event_id": ev["event_id"],
                "archetype": ev.get("archetype", "unknown"),
                "mission": ev.get("mission", ev.get("spacecraft", "unknown")),
                "subsystem": ev.get("subsystem", ev.get("channel_id", "unknown")),
                "gini_coefficient": ev.get("attribution", {}).get("attribution_concentration", ev.get("gini_coefficient")),
                "ensemble_agreement": ev.get("ensemble_agreement"),
                "ensemble_score": ev.get("ensemble_score"),
                "n_models_in_ensemble": ev.get("n_models_in_ensemble"),
                "window_start_index": ev.get("window_start_index"),
                "window_size": ev.get("window_size"),
                "attribution": ev.get("attribution"),
                "channel_attributions": ev.get("channel_attributions"),
                "anomaly_class": ev.get("anomaly_class"),
                "labeled_anomaly_start": ev.get("labeled_anomaly_start"),
                "labeled_anomaly_end": ev.get("labeled_anomaly_end"),
                "ground_truth_anomaly_type": ev.get("ground_truth_anomaly_type"),
                "ground_truth_severity": ev.get("ground_truth_severity"),
            }
        )
    return {"events": events}


@app.post("/explain", response_model=ExplainResponse)
def explain(request: ExplainRequest) -> ExplainResponse:
    """
    Generate a SituationalReport for the given event.

    If source_bodies is empty, the pipeline will fire an
    insufficient_context_retrieval refusal (no regulatory grounding available).
    """
    event = _load_event(request.event_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"Event '{request.event_id}' not found")

    # Cache check: skip for mock backend (fast enough, no API cost)
    if request.backend == "openai" and not request.force_refresh:
        cached = _cache.get(request.event_id, request.source_bodies, request.backend)
        if cached is not None:
            return ExplainResponse(report=cached, cached=True)

    # Retrieve relevant context from ChromaDB
    # Build a query string from the event's top SHAP features + metadata
    # Build query string: include subsystem type from channel prefix
    chan_id = event.get("channel_id", "")
    prefix_map = {
        "P": "power", "R": "radiation", "T": "thermal",
        "A": "attitude_control", "D": "data_handling",
        "E": "electrical", "F": "fault_detection", "G": "guidance",
    }
    subsystem_type = prefix_map.get(chan_id[0].upper() if chan_id else "", "unknown")
    anomaly_class = event.get("anomaly_class", "")

    shap_values: dict[str, float] = event.get("shap_values", {})
    top_features = sorted(shap_values.items(), key=lambda x: -abs(x[1]))[:5]
    feature_str = ", ".join(f"{k} ({v:+.3f})" for k, v in top_features)
    query_text = (
        f"spacecraft anomaly: {event.get('archetype', '')} "
        f"subsystem={subsystem_type} channel={chan_id} "
        f"anomaly_class={anomaly_class} "
        f"mission={event.get('mission', '')} "
        f"top_features={feature_str}"
    )

    retriever = _get_retriever()
    retrieved_context: dict[str, list[dict[str, Any]]] = {
        "regulations": [],
        "historicals": [],
    }

    # Only retrieve if source_bodies are specified (or backend is mock)
    if request.source_bodies or request.backend == "mock":
        regulatory_bodies = [
            b for b in request.source_bodies if b in ("EU_AI_Act", "NASA_NPR")
        ]
        historical_bodies = [
            b for b in request.source_bodies if b == "NASA_Lessons_Learned"
        ]

        try:
            if regulatory_bodies:
                retrieved_context["regulations"] = retriever.query(
                    query_text=query_text,
                    source_bodies=regulatory_bodies,
                    n_results=5,
                )
            if historical_bodies:
                retrieved_context["historicals"] = retriever.query(
                    query_text=query_text,
                    source_bodies=historical_bodies,
                    n_results=5,
                )
            # If no filter specified (mock mode), retrieve from all sources
            if not request.source_bodies:
                all_chunks = retriever.query(query_text=query_text, n_results=6)
                retrieved_context["regulations"] = [
                    c for c in all_chunks
                    if c["source_body"] in ("EU_AI_Act", "NASA_NPR")
                ][:3]
                retrieved_context["historicals"] = [
                    c for c in all_chunks
                    if c["source_body"] == "NASA_Lessons_Learned"
                ][:3]
        except Exception:
            # ChromaDB not yet populated — fall through with empty context
            pass

    # Simulate refusal when no source bodies selected
    if not request.source_bodies and request.backend == "openai":
        return ExplainResponse(
            report=SituationalReport(
                event_id=request.event_id,
                degraded_mode="insufficient_context_retrieval",
                refusal_reason=(
                    "No regulatory bodies selected. "
                    "Select at least one source body to generate a grounded report."
                ),
            )
        )

    backend = _get_backend(request.backend)
    report = backend.generate(event, retrieved_context)

    # Enrich provenance entries with full chunk text for UI display
    if report.provenance:
        chunk_lookup: dict[tuple[str, str], str] = {}
        for chunks in retrieved_context.values():
            for chunk in chunks:
                key = (chunk.get("source_body", ""), chunk.get("section", ""))
                chunk_lookup[key] = chunk.get("text", "")

        enriched = []
        for entry in report.provenance:
            text = chunk_lookup.get((entry.source_body, entry.section))
            enriched.append(entry.model_copy(update={"text": text}) if text else entry)
        report = report.model_copy(update={"provenance": enriched})

    # Write to cache for openai backend
    if request.backend == "openai":
        _cache.put(request.event_id, request.source_bodies, request.backend, report)

    return ExplainResponse(report=report, cached=False)
