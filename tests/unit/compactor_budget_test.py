from app.context.compactor import compact_candidates
from app.context.compactor import compact_candidates
from app.context.curator import RankedCandidate


def test_compactor_reduces_large_candidate():
    candidate = RankedCandidate(
        id="repo::file.py",
        source="repo",
        content="``\nprint('hello')\n``\n" * 200,
        score=1.0,
        tokens=1000,
        metadata={},
    )
    compacted, ops = compact_candidates([candidate], available_tokens=200, threshold_ratio=0.5)
    assert ops == 1
    assert compacted[0].tokens < candidate.tokens
