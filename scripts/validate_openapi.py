from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi import FastAPI

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app as fastapi_app

SPEC_PATH = Path("docs/integration/API_CONTRACTS.yaml")
HTTP_METHODS = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}


def load_expected_spec() -> dict:
    if not SPEC_PATH.exists():
        raise FileNotFoundError(f"Spec file not found: {SPEC_PATH}")
    return json.loads(SPEC_PATH.read_text())


def normalize_paths(data: dict[str, dict]) -> dict[str, set[str]]:
    normalized: dict[str, set[str]] = {}
    for path, raw_ops in data.items():
        if isinstance(raw_ops, dict) and raw_ops.get("x-kind") == "websocket":
            # WebSocket-Routen sind nicht Teil des FastAPI OpenAPI-Schemas
            continue
        ops: set[str] = set()
        for method in raw_ops.keys():
            method_lower = method.lower()
            if method_lower in HTTP_METHODS:
                ops.add(method_lower)
        if ops:
            normalized[path] = ops
    return normalized


def validate_paths(app: FastAPI, expected: dict[str, dict]) -> list[str]:
    openapi = app.openapi()
    generated_paths = normalize_paths(openapi.get("paths", {}))
    expected_paths = normalize_paths(expected.get("paths", {}))

    errors: list[str] = []

    missing_paths = sorted(set(expected_paths.keys()) - set(generated_paths.keys()))
    extra_paths = sorted(set(generated_paths.keys()) - set(expected_paths.keys()))
    if missing_paths:
        errors.append(f"Missing paths in FastAPI schema: {missing_paths}")
    if extra_paths:
        errors.append(f"Paths exposed by FastAPI but not in spec: {extra_paths}")

    for path, methods in expected_paths.items():
        generated_methods = generated_paths.get(path, set())
        missing_methods = sorted(methods - generated_methods)
        if missing_methods:
            errors.append(f"Missing methods for {path}: {missing_methods}")
    return errors


def validate_components(app: FastAPI, expected: dict[str, dict]) -> list[str]:
    openapi = app.openapi()
    generated_components = openapi.get("components", {}).get("schemas", {})
    expected_components = expected.get("components", {}).get("schemas", {})

    missing = sorted(set(expected_components.keys()) - set(generated_components.keys()))
    if missing:
        print(f"[WARN] Schemas missing in generated OpenAPI: {missing}")
    return []


def main() -> int:
    expected_spec = load_expected_spec()
    path_errors = validate_paths(fastapi_app, expected_spec)
    component_errors = validate_components(fastapi_app, expected_spec)

    errors = path_errors + component_errors
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1
    print("OpenAPI contract matches generated schema.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
