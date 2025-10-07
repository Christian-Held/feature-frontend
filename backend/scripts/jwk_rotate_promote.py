"""Promote NEXT JWK to CURRENT and generate a new NEXT key."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from .jwk_generate import create_jwk


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote NEXT JWK to CURRENT and rotate keys")
    parser.add_argument("store", type=Path, help="Directory containing current.json and next.json")
    args = parser.parse_args()

    store = args.store
    current_path = store / "current.json"
    next_path = store / "next.json"
    previous_path = store / "previous.json"

    if not current_path.exists() or not next_path.exists():
        raise SystemExit("Expected current.json and next.json to exist in the store directory")

    current_data = current_path.read_text()
    next_data = next_path.read_text()

    previous_path.write_text(current_data)
    current_path.write_text(next_data)

    new_next = create_jwk(kid=uuid.uuid4().hex)
    next_path.write_text(json.dumps(new_next, indent=2))

    print("Promoted NEXT to CURRENT")
    print("Previous key stored at", previous_path)
    print("New NEXT kid:", new_next["kid"])


if __name__ == "__main__":  # pragma: no cover - CLI utility
    main()
