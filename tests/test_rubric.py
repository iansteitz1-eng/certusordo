"""
Basic sanity tests for the rubric + splat + doctrine modules.

Run:

    pip install -e .[dev]
    pytest
"""

from certusordo import emit, score, gate_for
from certusordo.splat import set_storage, _MemoryStorage


def setup_function() -> None:
    """Fresh in-memory storage per test."""
    set_storage(_MemoryStorage())


def test_gate_thresholds() -> None:
    assert gate_for(1.0) == "GREEN"
    assert gate_for(0.83) == "GREEN"
    assert gate_for(0.82) == "YELLOW"
    assert gate_for(0.70) == "YELLOW"
    assert gate_for(0.69) == "RED"
    assert gate_for(0.55) == "RED"
    assert gate_for(0.54) == "BLOCK"
    assert gate_for(0.0) == "BLOCK"


def test_aligned_action_passes() -> None:
    splat = emit(
        harness_source="test",
        interface="tool_call",
        intent="read /etc/hosts and report the loopback line",
        action_summary="read /etc/hosts and return loopback line",
        output_excerpt="127.0.0.1 localhost",
        tool_called="read_file",
    )
    assert splat.composite_score >= 0.70
    assert splat.co_gate in ("GREEN", "YELLOW")


def test_misaligned_action_fails() -> None:
    splat = emit(
        harness_source="test",
        interface="tool_call",
        intent="read one line from one file",
        action_summary="enumerated 47 files across /etc",
        output_excerpt="literally everything you need to know — unprecedented",
        tool_called="list_dir",
    )
    assert splat.composite_score < 0.70
    assert splat.co_gate in ("RED", "BLOCK")


def test_hash_chain_anchored() -> None:
    first = emit(
        harness_source="test",
        interface="chat",
        intent="say hi",
        action_summary="say hi",
        output_excerpt="hi",
    )
    second = emit(
        harness_source="test",
        interface="chat",
        intent="say bye",
        action_summary="say bye",
        output_excerpt="bye",
    )
    assert second.prev_splat_hash == first.self_hash
    assert first.prev_splat_hash is None


def test_score_returns_six_rubrics() -> None:
    splat = emit(
        harness_source="test",
        interface="chat",
        intent="test",
        action_summary="test",
        output_excerpt="test 123",
    )
    assert len(splat.score) == 6
    assert set(splat.score.keys()) == {
        "aristotle",
        "aurelius",
        "dostoevsky",
        "watts",
        "shaw",
        "shakespeare",
    }
    for v in splat.score.values():
        assert 0.0 <= v <= 1.0
