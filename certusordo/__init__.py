"""
certusordo — structured action receipts with hash-chained six-rubric
composite scoring for AI agent oversight.

The CertusOrdo doctrine, in code. Every state-changing AI action emits a
structured *splat*: a typed, scored, hash-chained receipt that is queryable
as data instead of reviewable as a transcript.

Quick start:

    from certusordo import Splat, score, emit

    splat = emit(
        harness_source="claude_code",
        interface="tool_call",
        intent="read /etc/hosts and report the loopback line",
        action_summary="open /etc/hosts via read_file; return line matching 127.0.0.1",
        output_excerpt="127.0.0.1 localhost",
        tool_called="read_file",
    )
    print(splat.composite_score, splat.co_gate)

See examples/score_an_action.py for an end-to-end runnable demo, and the
Aria Thesis White Paper at insynctech.io/docs for the full doctrine.

Author: Ian Steitz · InSync Tech, Inc.
License: Apache-2.0
"""

from certusordo.splat import Splat, emit
from certusordo.rubric import score, RUBRICS
from certusordo.doctrine import GATE_THRESHOLDS, gate_for

__version__ = "0.2.0"

__all__ = [
    "Splat",
    "emit",
    "score",
    "RUBRICS",
    "GATE_THRESHOLDS",
    "gate_for",
]
