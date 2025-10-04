from pathlib import Path

from app.core.diffs import apply_unified_diff, generate_unified_diff, safe_write


def test_apply_unified_diff(tmp_path):
    file_path = tmp_path / "sample.txt"
    original = "hello\nworld\n"
    updated = "hello\npython\n"
    file_path.write_text(original, encoding="utf-8")
    diff = generate_unified_diff(original, updated, "sample.txt")
    for path, content in apply_unified_diff(tmp_path, diff):
        safe_write(path, content)
    assert file_path.read_text(encoding="utf-8") == updated
