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


def test_apply_unified_diff_without_space_after_hunk_prefix(tmp_path):
    diff = """--- /dev/null
+++ b/new_file.txt
@@-0,0 +1 @@
+content line
"""
    results = list(apply_unified_diff(tmp_path, diff))
    assert results == [(tmp_path / "new_file.txt", "content line\n")]


def test_apply_unified_diff_with_context_header_suffix(tmp_path):
    original = "def greet():\n    return 'hi'\n"
    updated = "def greet():\n    return 'hello'\n"
    file_path = tmp_path / "module.py"
    file_path.write_text(original, encoding="utf-8")
    diff = """--- a/module.py
+++ b/module.py
@@ -1,2 +1,2 @@ def greet():
 def greet():
-    return 'hi'
+    return 'hello'
"""
    for path, content in apply_unified_diff(tmp_path, diff):
        safe_write(path, content)
    assert file_path.read_text(encoding="utf-8") == updated


def test_apply_unified_diff_with_minimal_hunk_header(tmp_path):
    original = "print('old')\n"
    updated = "print('new')\n"
    file_path = tmp_path / "script.py"
    file_path.write_text(original, encoding="utf-8")
    diff = """--- a/script.py
+++ b/script.py
@@
-print('old')
+print('new')
"""
    for path, content in apply_unified_diff(tmp_path, diff):
        safe_write(path, content)
    assert file_path.read_text(encoding="utf-8") == updated
