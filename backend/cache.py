"""
Disk-based report cache for shap-to-report.

Cache key: SHA-256 of (event_id + sorted source_bodies + backend).
Cache location: .report_cache/ at project root (gitignored).

At temperature=0 the pipeline is deterministic, so the same inputs
always produce the same report. Caching eliminates repeat API costs
and makes the UI feel instant on re-runs.

Usage:
    from backend.cache import ReportCache
    cache = ReportCache()
    hit = cache.get(event_id, source_bodies, backend)
    if hit:
        return hit
    report = generate(...)
    cache.put(event_id, source_bodies, backend, report)
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from backend.schema.models import SituationalReport

_ROOT = Path(__file__).parent.parent
CACHE_DIR = _ROOT / ".report_cache"


def _cache_key(event_id: str, source_bodies: list[str], backend: str) -> str:
    """Stable SHA-256 key — order of source_bodies doesn't matter."""
    payload = f"{event_id}|{','.join(sorted(source_bodies))}|{backend}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class ReportCache:
    """Simple JSON file cache. Thread-safe for single-process use."""

    def __init__(self, cache_dir: Path = CACHE_DIR) -> None:
        self._dir = cache_dir
        self._dir.mkdir(exist_ok=True)

    def _path(self, key: str) -> Path:
        return self._dir / f"{key}.json"

    def get(self, event_id: str, source_bodies: list[str], backend: str,) -> SituationalReport | None:
        """Return cached report or None if not found."""
        p = self._path(_cache_key(event_id, source_bodies, backend))
        if not p.exists():
            return None
        try:
            data: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
            return SituationalReport.model_validate(data)
        except Exception:
            # Corrupt cache entry — delete and return None
            p.unlink(missing_ok=True)
            return None

    def put(self,event_id: str, source_bodies: list[str], backend: str, report: SituationalReport,) -> None:
        """Write report to cache."""
        self._dir.mkdir(exist_ok=True)  # recreate if deleted
        p = self._path(_cache_key(event_id, source_bodies, backend))
        p.write_text(
            json.dumps(report.model_dump(), indent=2, default=str),
            encoding="utf-8",
        )

    def invalidate(self, event_id: str, source_bodies: list[str], backend: str,) -> bool:
        """Delete a specific cache entry. Returns True if it existed."""
        p = self._path(_cache_key(event_id, source_bodies, backend))
        if p.exists():
            p.unlink()
            return True
        return False

    def clear_all(self) -> int:
        """Delete all cache entries. Returns count deleted."""
        count = 0
        for p in self._dir.glob("*.json"):
            p.unlink()
            count += 1
        return count

    def stats(self) -> dict[str, int]:
        entries = list(self._dir.glob("*.json"))
        size = sum(p.stat().st_size for p in entries)
        return {"entries": len(entries), "bytes": size}
