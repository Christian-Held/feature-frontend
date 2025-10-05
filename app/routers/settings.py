from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import dotenv_values
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.pricing import get_pricing_table

router = APIRouter(prefix="/api", tags=["settings"])
logger = get_logger(__name__)
_ENV_FILE = Path(".env")


class EnvVariable(BaseModel):
    key: str
    value: str
    description: Optional[str] = None
    isSecret: bool = Field(False, alias="is_secret")

    class Config:
        populate_by_name = True


class EnvUpdateRequest(BaseModel):
    value: str


class ModelVariant(BaseModel):
    id: str
    label: str
    description: Optional[str] = None


class ModelConfig(BaseModel):
    id: str
    name: str
    provider: str
    description: Optional[str] = None
    variants: List[ModelVariant] = Field(default_factory=list)
    selectedVariant: Optional[str] = None
    parameters: Dict[str, str] = Field(default_factory=dict)


class ModelUpdateRequest(BaseModel):
    selectedVariant: Optional[str] = None
    parameters: Dict[str, str] = Field(default_factory=dict)


_ENV_DEFINITIONS = {
    "OPENAI_API_KEY": EnvVariable(
        key="OPENAI_API_KEY",
        value="",
        description="OpenAI API key for orchestrator agents",
        is_secret=True,
    ),
    "GITHUB_TOKEN": EnvVariable(
        key="GITHUB_TOKEN",
        value="",
        description="GitHub token used for repository automation",
        is_secret=True,
    ),
    "MODEL_CTO": EnvVariable(
        key="MODEL_CTO",
        value="gpt-4.1-mini",
        description="Default model used by the CTO agent",
    ),
    "MODEL_CODER": EnvVariable(
        key="MODEL_CODER",
        value="gpt-4.1",
        description="Default model used by the Coder agent",
    ),
}

_MODEL_DEFINITIONS = {
    "cto": {
        "name": "CTO Agent",
        "provider": "OpenAI",
        "description": "Model used for planning and orchestration",
        "env_key": "MODEL_CTO",
    },
    "coder": {
        "name": "Coder Agent",
        "provider": "OpenAI",
        "description": "Model used for code generation",
        "env_key": "MODEL_CODER",
    },
}


def _load_env_file() -> Dict[str, str]:
    if not _ENV_FILE.exists():
        return {}
    return {k: v for k, v in dotenv_values(_ENV_FILE).items() if v is not None}


def _write_env_file(values: Dict[str, str]) -> None:
    lines = [f"{key}={value}\n" for key, value in sorted(values.items())]
    _ENV_FILE.write_text("".join(lines), encoding="utf-8")


def _get_current_env() -> Dict[str, str]:
    settings = get_settings()
    data = {
        "OPENAI_API_KEY": settings.openai_api_key,
        "GITHUB_TOKEN": settings.github_token,
        "MODEL_CTO": settings.model_cto,
        "MODEL_CODER": settings.model_coder,
    }
    file_values = _load_env_file()
    data.update(file_values)
    return data


@router.get("/env", response_model=List[EnvVariable])
def list_env_variables() -> List[EnvVariable]:
    current = _get_current_env()
    variables: List[EnvVariable] = []
    for key, definition in _ENV_DEFINITIONS.items():
        variables.append(
            EnvVariable(
                key=key,
                value=current.get(key, definition.value),
                description=definition.description,
                is_secret=definition.isSecret,
            )
        )
    return variables


@router.put("/env/{key}", response_model=EnvVariable)
def update_env_variable(key: str, payload: EnvUpdateRequest) -> EnvVariable:
    if key not in _ENV_DEFINITIONS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown environment variable")
    existing = _load_env_file()
    existing[key] = payload.value
    _write_env_file(existing)
    os.environ[key] = payload.value
    get_settings.cache_clear()
    current = _get_current_env()
    definition = _ENV_DEFINITIONS[key]
    logger.info("env_variable_updated", key=key)
    return EnvVariable(
        key=key,
        value=current.get(key, ""),
        description=definition.description,
        is_secret=definition.isSecret,
    )


@router.get("/models", response_model=List[ModelConfig])
def list_model_configs() -> List[ModelConfig]:
    pricing = get_pricing_table()
    current = _get_current_env()
    variants = [ModelVariant(id=model_id, label=model_id) for model_id in pricing.keys()]
    configs: List[ModelConfig] = []
    for model_id, meta in _MODEL_DEFINITIONS.items():
        env_key = meta["env_key"]
        configs.append(
            ModelConfig(
                id=model_id,
                name=meta["name"],
                provider=meta["provider"],
                description=meta.get("description"),
                variants=variants,
                selectedVariant=current.get(env_key),
                parameters={},
            )
        )
    return configs


@router.put("/models/{model_id}", response_model=ModelConfig)
def update_model_config(model_id: str, payload: ModelUpdateRequest) -> ModelConfig:
    if model_id not in _MODEL_DEFINITIONS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown model configuration")
    definition = _MODEL_DEFINITIONS[model_id]
    env_key = definition["env_key"]
    if payload.selectedVariant:
        existing = _load_env_file()
        existing[env_key] = payload.selectedVariant
        _write_env_file(existing)
        os.environ[env_key] = payload.selectedVariant
        get_settings.cache_clear()
    current = _get_current_env()
    logger.info("model_configuration_updated", model_id=model_id, selected=payload.selectedVariant)
    pricing = get_pricing_table()
    variants = [ModelVariant(id=model_name, label=model_name) for model_name in pricing.keys()]
    return ModelConfig(
        id=model_id,
        name=definition["name"],
        provider=definition["provider"],
        description=definition.get("description"),
        variants=variants,
        selectedVariant=current.get(env_key),
        parameters=payload.parameters or {},
    )
