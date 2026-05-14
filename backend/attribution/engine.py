"""
Attribution engine ABC and CPSC 491 integration stub.

AttributionEngine   — abstract interface
RealAttributionEngine — stub; wired in CPSC 491 Phase 3 once score_components() exists

The boundary is clean: implement RealAttributionEngine without touching any
pipeline or LLM code.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from backend.schema.models import AttributionResult, Archetype


class AttributionEngine(ABC):
    """
    Produces an AttributionResult for an anomaly event.

    CPSC 491 Phase 3 replaces the prototype path with RealAttributionEngine
    wrapping AnomalyEnsemble.score_components() from telemetry-anomdet.
    """

    @abstractmethod
    def attribute(self, channel_id: str, archetype: Archetype | None = None) -> AttributionResult:
        """
        Produce an AttributionResult for the given channel.

        Args:
            channel_id: SMAP channel ID, e.g. 'D-2'
            archetype:  Optional hint. Ignored by RealAttributionEngine.

        Returns:
            AttributionResult with feature_attributions and attribution_concentration.
        """
        ...


class RealAttributionEngine(AttributionEngine):
    """
    Production attribution engine wrapping AnomalyEnsemble.score_components().

    NOT IMPLEMENTED. This is the v0/v1 handoff point for CPSC 491 Phase 3.

    Integration point:
        from telemetry_anomdet.models.ensemble import AnomalyEnsemble

        ensemble: AnomalyEnsemble  # fitted on nominal data
        X_window: np.ndarray       # shape (1, window_size, n_features)

        components = ensemble.score_components(X_window)
        # {"pca": array([score]), "kmeans": array([score]), ...}
        # Perturb each feature channel, measure delta in components → SHAP values

    Mohamed Aiad wires this up in CPSC 491 once score_components() is stable.
    """

    def attribute(
        self, channel_id: str, archetype: Archetype | None = None
    ) -> AttributionResult:
        raise NotImplementedError(
            "RealAttributionEngine is not implemented in the prototype. "
            "See CPSC 491 Phase 3 for integration with score_components()."
        )
