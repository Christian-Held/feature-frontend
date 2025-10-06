from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

from .provider import BaseLLMProvider, LLMResponse, estimate_tokens

logger = get_logger(__name__)


class OpenAILLMProvider(BaseLLMProvider):
    name = "openai"

    async def generate(self, *, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> LLMResponse:
        settings = get_settings()
        default_base_url = "https://api.openai.com/v1"
        configured_base_url = (settings.openai_base_url or default_base_url).rstrip("/")
        if configured_base_url != default_base_url:
            logger.warning(
                "openai_base_url_override",
                configured_base_url=configured_base_url,
                expected_base_url=default_base_url,
            )
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": model, "messages": messages}
        payload.update(kwargs)

        endpoint_path = "/chat/completions"

        async def _perform_request(base_url: str) -> Tuple[httpx.Response, str]:
            sanitized_base_url = base_url.rstrip("/")
            resolved_url = f"{sanitized_base_url}{endpoint_path}"
            logger.info(
                "openai_request",
                model=model,
                base_url=sanitized_base_url,
                endpoint=endpoint_path,
                resolved_url=resolved_url,
            )
            async with httpx.AsyncClient(base_url=sanitized_base_url, timeout=60) as client:
                response = await client.post(
                    endpoint_path,
                    content=json.dumps(payload),
                    headers=headers,
                )
            return response, sanitized_base_url

        response, attempted_base_url = await _perform_request(configured_base_url)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.error(
                    "openai_404_response",
                    model=model,
                    endpoint=endpoint_path,
                    attempted_base_url=attempted_base_url,
                    resolved_url=f"{attempted_base_url}{endpoint_path}",
                )
                if attempted_base_url != default_base_url:
                    logger.info(
                        "openai_retry_default_base_url",
                        model=model,
                        endpoint=endpoint_path,
                        fallback_base_url=default_base_url,
                    )
                    response, attempted_base_url = await _perform_request(default_base_url)
                    try:
                        response.raise_for_status()
                    except httpx.HTTPStatusError as retry_exc:
                        if retry_exc.response.status_code == 404:
                            logger.error(
                                "openai_404_response_final",
                                model=model,
                                endpoint=endpoint_path,
                                attempted_base_url=attempted_base_url,
                                resolved_url=f"{attempted_base_url}{endpoint_path}",
                            )
                        raise
                else:
                    raise
            else:
                raise
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", estimate_tokens(json.dumps(messages)))
        tokens_out = usage.get("completion_tokens", estimate_tokens(text))
        logger.info("openai_call", model=model, tokens_in=tokens_in, tokens_out=tokens_out)
        return LLMResponse(text=text, tokens_in=tokens_in, tokens_out=tokens_out)

    def count_tokens(self, messages: List[Dict[str, str]]) -> int:
        payload = json.dumps(messages)
        return estimate_tokens(payload)
