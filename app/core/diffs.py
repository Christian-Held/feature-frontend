from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Iterable, Optional, Tuple

from .logging import get_logger

logger = get_logger(__name__)

HUNK_RE = re.compile(
    r"@@\s*-(?P<old_start>\d+)(?:,(?P<old_len>\d+))?\s+\+(?P<new_start>\d+)(?:,(?P<new_len>\d+))?\s*@@.*"
)

MARKER_FULL = "FULL"
MARKER_PATCH = "PATCH"


def _parse_diff_path(raw_path: str) -> tuple[Optional[str], Optional[str]]:
    """Return the normalized path and optional diff marker."""

    marker: Optional[str] = None
    if raw_path == "/dev/null":
        return None, None

    path = raw_path
    if raw_path.startswith("a/") or raw_path.startswith("b/"):
        path = raw_path[2:]

    if "::" in path:
        base, candidate = path.rsplit("::", 1)
        if candidate in {MARKER_FULL, MARKER_PATCH}:
            marker = candidate
            path = base

    return path, marker


def _collect_new_lines(diff_lines: list[str]) -> list[str]:
    lines: list[str] = []
    for line in diff_lines:
        if line.startswith("+") or line.startswith(" "):
            lines.append(line[1:])
        elif line.startswith("\\"):
            # "\\ No newline at end of file" style metadata
            continue
        elif not line.startswith("-") and not line.startswith("@@"):
            lines.append(line)
    return lines


def generate_unified_diff(original: str, updated: str, filename: str) -> str:
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        updated.splitlines(keepends=True),
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
    )
    return "".join(diff)


def apply_unified_diff(base_path: Path, diff_text: str) -> Iterable[Tuple[Path, str]]:
    lines = diff_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.startswith("--- "):
            i += 1
            continue

        old_raw = line[4:].strip()
        i += 1
        if i >= len(lines):
            break

        new_line = lines[i]
        if not new_line.startswith("+++ "):
            raise ValueError("Invalid diff: missing '+++' line")
        new_raw = new_line[4:].strip()
        i += 1

        chunk_lines: list[str] = []
        while i < len(lines) and not lines[i].startswith("--- "):
            chunk_lines.append(lines[i])
            i += 1

        old_path, old_marker = _parse_diff_path(old_raw)
        new_path, new_marker = _parse_diff_path(new_raw)

        target_relative = new_path or old_path
        if target_relative is None:
            logger.warning("diff_missing_target_path", old_path=old_raw, new_path=new_raw)
            continue

        target_path = base_path / target_relative
        marker = new_marker or old_marker
        diff_mode = MARKER_FULL if marker == MARKER_FULL else MARKER_PATCH

        logger.info(
            "diff_file_detected",
            path=str(target_path),
            path_cleaned=target_relative,
            diff_mode=diff_mode,
        )

        if old_path is None:
            original_content = ""
        else:
            source_path = base_path / old_path
            original_content = (
                source_path.read_text(encoding="utf-8") if source_path.exists() else ""
            )

        source_lines = original_content.splitlines()
        rebuilt: list[str] = []
        cursor = 0
        handled_hunk = False
        fallback_reason: Optional[str] = None
        fallback_lines: list[str] = []

        j = 0
        while j < len(chunk_lines):
            header = chunk_lines[j]
            if not header.startswith("@@"):
                j += 1
                continue

            stripped_header = header.strip()
            if stripped_header == "@@":
                logger.warning(
                    "diff_header_missing_ranges",
                    header=header,
                    path=str(target_path),
                    diff_mode=diff_mode,
                )
                rebuilt = []
                cursor = len(source_lines)
                j += 1
                fallback_segment: list[str] = []
                while j < len(chunk_lines) and not chunk_lines[j].startswith("@@"):
                    hunk_line = chunk_lines[j]
                    if hunk_line.startswith("+") or hunk_line.startswith(" "):
                        fallback_segment.append(hunk_line[1:])
                    elif hunk_line.startswith("-"):
                        pass
                    else:
                        logger.warning("unknown_diff_line", line=hunk_line, path=str(target_path))
                    j += 1
                rebuilt = fallback_segment
                handled_hunk = True
                fallback_reason = fallback_reason or "missing_ranges"
                continue

            match = HUNK_RE.match(header)
            if not match:
                logger.warning(
                    "diff_invalid_hunk_header",
                    header=header,
                    path=str(target_path),
                    diff_mode=diff_mode,
                )
                if diff_mode == MARKER_FULL:
                    fallback_reason = "invalid_hunk"
                    fallback_lines = chunk_lines[j + 1 :]
                    handled_hunk = False
                    break
                raise ValueError(f"Invalid hunk header: {header}")

            handled_hunk = True
            old_start = int(match.group("old_start")) - 1
            if old_start > len(source_lines):
                old_start = len(source_lines)
            rebuilt.extend(source_lines[cursor:old_start])
            cursor = old_start

            j += 1
            while j < len(chunk_lines) and not chunk_lines[j].startswith("@@"):
                hunk_line = chunk_lines[j]
                if hunk_line.startswith(" "):
                    if cursor < len(source_lines):
                        rebuilt.append(source_lines[cursor])
                    else:
                        rebuilt.append(hunk_line[1:])
                    cursor += 1
                elif hunk_line.startswith("-"):
                    cursor += 1
                elif hunk_line.startswith("+"):
                    rebuilt.append(hunk_line[1:])
                else:
                    logger.warning("unknown_diff_line", line=hunk_line, path=str(target_path))
                j += 1

        new_content: Optional[str] = None
        if diff_mode == MARKER_FULL and (not handled_hunk or fallback_reason):
            reason = fallback_reason or "no_hunks"
            segment = fallback_lines if fallback_reason == "invalid_hunk" else chunk_lines
            full_lines = _collect_new_lines(segment)
            new_content = "\n".join(full_lines)
            if full_lines and (diff_text.endswith("\n") or original_content.endswith("\n")):
                new_content += "\n"
            elif not full_lines and (original_content.endswith("\n") or diff_text.endswith("\n")):
                new_content = "\n"
            logger.info(
                "diff_full_applied",
                path=str(target_path),
                path_cleaned=target_relative,
                diff_mode=diff_mode,
                fallback_reason=reason,
            )
        else:
            rebuilt.extend(source_lines[cursor:])
            new_content = "\n".join(rebuilt)
            if original_content.endswith("\n") or diff_text.endswith("\n"):
                new_content += "\n"
            logger.info(
                "diff_applied",
                path=str(target_path),
                path_cleaned=target_relative,
                diff_mode=diff_mode,
                fallback_reason=fallback_reason,
            )

        yield target_path, new_content


def safe_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.info("file_written", path=str(path))
