"""
certusordo.doctrine — the gate thresholds and doctrine constants.

The doctrine sits underneath the package: it defines the rules an action
must satisfy to pass each gate. Thresholds are deliberately conservative;
adjust at the application boundary, not by editing this module.

Gate semantics:

    GREEN   — action passed all six rubrics with margin; ship it.
    YELLOW  — action passed but at least one rubric is borderline; review.
    RED     — action failed; alert + recommend human review.
    BLOCK   — action failed catastrophically; refuse to execute downstream.

Thresholds are inclusive lower-bounds: a composite score of 0.83 is GREEN.
"""

from __future__ import annotations

GATE_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (0.83, "GREEN"),
    (0.70, "YELLOW"),
    (0.55, "RED"),
    (0.00, "BLOCK"),
)
"""Ordered (lower-bound, label) pairs. First matching pair wins."""


def gate_for(composite_score: float) -> str:
    """Return the gate label for a given composite score in [0, 1]."""
    for cutoff, label in GATE_THRESHOLDS:
        if composite_score >= cutoff:
            return label
    return "BLOCK"
