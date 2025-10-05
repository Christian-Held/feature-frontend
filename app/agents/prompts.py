from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict

from app.core.logging import get_logger

logger = get_logger(__name__)


class AgentsSpec:
    def __init__(self, sections: Dict[str, str], digest: str):
        self.sections = sections
        self.digest = digest

    def section(self, name: str) -> str:
        key = name.upper()
        if key not in self.sections:
            raise KeyError(f"Section {name} not found in AGENTS.md")
        return self.sections[key]


def parse_agents_file(path: Path = Path("AGENTS.md")) -> AgentsSpec:
    if not path.exists():
        raise FileNotFoundError("AGENTS.md not found")
    content = path.read_text(encoding="utf-8")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    sections: Dict[str, str] = {}
    current_header = None
    buffer: list[str] = []
    for line in content.splitlines():
        if line.startswith("# "):
            if current_header:
                sections[current_header] = "\n".join(buffer).strip()
            current_header = line[2:].strip().upper()
            buffer = []
        else:
            buffer.append(line)
    if current_header:
        sections[current_header] = "\n".join(buffer).strip()
    logger.info("agents_parsed", sections=list(sections.keys()), digest=digest)
    return AgentsSpec(sections, digest)


def build_prompt(section_text: str, context: str) -> str:
    prompt = f"{section_text}\n\nContext:\n{context.strip()}"
    logger.debug("prompt_built", prompt_length=len(prompt))
    return prompt
