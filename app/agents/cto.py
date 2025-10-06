from __future__ import annotations

import json
from typing import Dict, List

from app.core.logging import get_logger
from app.llm.provider import BaseLLMProvider

from .prompts import AgentsSpec, build_prompt

logger = get_logger(__name__)


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[-1].startswith("```"):
            return "\n".join(lines[1:-1]).strip()
    return text


class CTOAgent:
    def __init__(self, provider: BaseLLMProvider, spec: AgentsSpec, model: str, dry_run: bool = False):
        self.provider = provider
        self.spec = spec
        self.model = model
        self.dry_run = dry_run

    async def create_plan(
        self, task: str, *, messages: List[Dict[str, str]] | None = None
    ) -> tuple[List[Dict[str, str]], int, int, str]:
        if messages is None:
            context = f"Task: {task}"
            section = self.spec.section("CTO-AI")
            prompt = build_prompt(section, context)
            messages = [{"role": "system", "content": prompt}]
        logger.info("cto_plan_request", model=self.model)
        response = await self.provider.generate(model=self.model, messages=messages)
        plan_text = response.text
        plan_payload = _strip_json_fence(plan_text)
        if self.dry_run:
            logger.info("cto_plan_dry_run")
            return ([
                {
                    "title": "Analyse Task",
                    "rationale": "Dry run analysis",
                    "acceptance": "Plan documented",
                    "files": [],
                    "commands": [],
                }
            ], response.tokens_in, response.tokens_out, plan_text)
        try:
            plan = json.loads(plan_payload)
            if not isinstance(plan, list):
                raise ValueError("Plan must be a list")
            return plan, response.tokens_in, response.tokens_out, plan_text
        except json.JSONDecodeError as exc:
            logger.error("cto_plan_parse_error", error=str(exc), response=plan_text)
            raise
