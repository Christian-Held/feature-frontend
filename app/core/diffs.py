from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple

from .logging import get_logger

logger = get_logger(__name__)

HUNK_RE = re.compile(
    r"@@\s*-(?P<old_start>\d+)(?:,(?P<old_len>\d+))?\s+\+(?P<new_start>\d+)(?:,(?P<new_len>\d+))?\s*@@.*"
)

MARKER_FULL = "FULL"
MARKER_PATCH = "PATCH"


@dataclass
class DiffHeader:
    old_path: Optional[str]
    new_path: Optional[str]
    diff_mode: str
    header_state: str
    marker: Optional[str]
    old_raw: str
    new_raw: Optional[str]
    reason: Optional[str]


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


def _parse_diff_headers(lines: list[str], start_index: int) -> tuple[int, DiffHeader]:
    """Parse a unified diff header starting at the given index."""

    old_line = lines[start_index]
    old_raw = old_line[4:].strip() if old_line.startswith("--- ") else old_line.strip()
    next_index = start_index + 1
    reason: Optional[str] = None
    header_state = "incomplete"
    new_raw: Optional[str] = None

    if next_index < len(lines) and lines[next_index].startswith("+++ "):
        new_raw = lines[next_index][4:].strip()
        header_state = "valid"
        next_index += 1
    else:
        new_raw = old_raw
        reason = "missing_+++_header"

    old_path, old_marker = _parse_diff_path(old_raw)
    new_path, new_marker = _parse_diff_path(new_raw) if new_raw is not None else (None, None)
    marker = new_marker or old_marker
    diff_mode = MARKER_FULL if marker == MARKER_FULL else MARKER_PATCH
    if header_state != "valid":
        diff_mode = MARKER_FULL

    return next_index, DiffHeader(
        old_path=old_path,
        new_path=new_path,
        diff_mode=diff_mode,
        header_state=header_state,
        marker=marker,
        old_raw=old_raw,
        new_raw=new_raw,
        reason=reason,
    )


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
    diff_has_trailing_newline = diff_text.endswith("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.startswith("--- "):
            i += 1
            continue

        next_index, header = _parse_diff_headers(lines, i)
        i = next_index

        chunk_lines: list[str] = []
        while i < len(lines) and not lines[i].startswith("--- "):
            chunk_lines.append(lines[i])
            i += 1

        target_relative = header.new_path or header.old_path
        if target_relative is None:
            logger.warning(
                "diff_missing_target_path",
                diff_event="apply_diff",
                old_path=header.old_raw,
                new_path=header.new_raw,
            )
            continue

        target_path = base_path / target_relative
        effective_mode = header.diff_mode
        fallback_reason: Optional[str] = header.reason
        fallback_lines: list[str] = []
        handled_hunk = False

        logger.info(
            "diff_file_detected",
            diff_event="apply_diff",
            file=str(target_relative),
            path=str(target_path),
            diff_mode=effective_mode,
            header_state=header.header_state,
            file_path_normalized=target_relative,
        )

        if header.header_state != "valid":
            logger.warning(
                "diff_incomplete_header",
                diff_event="apply_diff",
                file=str(target_relative),
                mode=effective_mode,
                header_state=header.header_state,
                reason=header.reason,
                old_header=header.old_raw,
                new_header=header.new_raw,
            )

        if header.old_path is None:
            original_content = ""
        else:
            source_path = base_path / header.old_path
            original_content = (
                source_path.read_text(encoding="utf-8") if source_path.exists() else ""
            )

        source_lines = original_content.splitlines()
        rebuilt: list[str] = []
        cursor = 0

        j = 0
        try:
            while j < len(chunk_lines):
                hunk_header = chunk_lines[j]
                if not hunk_header.startswith("@@"):
                    j += 1
                    continue

                stripped_header = hunk_header.strip()
                if stripped_header == "@@":
                    logger.warning(
                        "diff_header_missing_ranges",
                        diff_event="apply_diff",
                        file=str(target_relative),
                        mode=effective_mode,
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
                            logger.warning(
                                "unknown_diff_line",
                                diff_event="apply_diff",
                                file=str(target_relative),
                                line=hunk_line,
                            )
                        j += 1
                    rebuilt = fallback_segment
                    handled_hunk = True
                    fallback_reason = fallback_reason or "missing_ranges"
                    continue

                match = HUNK_RE.match(hunk_header)
                if not match:
                    logger.warning(
                        "diff_invalid_hunk_header",
                        diff_event="apply_diff",
                        file=str(target_relative),
                        mode=effective_mode,
                        header=hunk_header,
                    )
                    fallback_reason = "invalid_hunk"
                    fallback_lines = chunk_lines[j + 1 :]
                    handled_hunk = False
                    effective_mode = MARKER_FULL
                    break

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
                        logger.warning(
                            "unknown_diff_line",
                            diff_event="apply_diff",
                            file=str(target_relative),
                            line=hunk_line,
                        )
                    j += 1
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning(
                "diff_hunk_parse_error",
                diff_event="apply_diff",
                file=str(target_relative),
                mode=effective_mode,
                error=str(exc),
            )
            fallback_reason = fallback_reason or "hunk_parse_error"
            fallback_lines = chunk_lines
            handled_hunk = False
            effective_mode = MARKER_FULL

        new_content: Optional[str] = None
        use_full_fallback = (
            effective_mode == MARKER_FULL
            or not handled_hunk
            or fallback_reason is not None
        )

        if use_full_fallback:
            reason = fallback_reason or ("no_hunks" if chunk_lines else "no_content")
            segment = fallback_lines if fallback_lines else chunk_lines
            full_lines = _collect_new_lines(segment)
            new_content = "\n".join(full_lines)
            if full_lines and (diff_has_trailing_newline or original_content.endswith("\n")):
                new_content += "\n"
            elif not full_lines and (original_content.endswith("\n") or diff_has_trailing_newline):
                new_content = "\n"
            logger.info(
                "diff_full_applied",
                diff_event="apply_diff",
                file=str(target_relative),
                path=str(target_path),
                diff_mode=MARKER_FULL,
                fallback_reason=reason,
                header_state=header.header_state,
            )
        else:
            rebuilt.extend(source_lines[cursor:])
            new_content = "\n".join(rebuilt)
            if original_content.endswith("\n") or diff_has_trailing_newline:
                new_content += "\n"
            logger.info(
                "diff_applied",
                diff_event="apply_diff",
                file=str(target_relative),
                path=str(target_path),
                diff_mode=effective_mode,
                fallback_reason=fallback_reason,
                header_state=header.header_state,
            )

        yield target_path, new_content


def _sanitize_write_path(path: Path) -> Path:
    raw_path = str(path)
    sanitized = raw_path
    reason: Optional[str] = None

    if "::" in raw_path:
        base, candidate = raw_path.rsplit("::", 1)
        if candidate in {MARKER_FULL, MARKER_PATCH}:
            sanitized = base
            reason = candidate.lower()

    sanitized_path = Path(sanitized)
    if sanitized != raw_path:
        logger.warning(
            "diff_path_sanitized",
            diff_event="apply_diff",
            original_path=raw_path,
            sanitized_path=str(sanitized_path),
            reason=f"remove_marker_{reason}" if reason else "normalize_suffix",
        )

    if ":" in sanitized_path.name and "::" not in raw_path:
        logger.warning(
            "diff_path_colon_detected",
            diff_event="apply_diff",
            original_path=raw_path,
            sanitized_path=str(sanitized_path),
        )

    return sanitized_path


def safe_write(path: Path, content: str) -> Path:
    sanitized_path = _sanitize_write_path(path)
    sanitized_path.parent.mkdir(parents=True, exist_ok=True)
    sanitized_path.write_text(content, encoding="utf-8")
    logger.info(
        "file_written",
        diff_event="apply_diff",
        path=str(sanitized_path),
        original_path=str(path),
    )
    return sanitized_path
