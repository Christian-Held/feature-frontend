"""Generate ES256 JSON Web Keys with unique key identifiers."""

from __future__ import annotations

import argparse
import base64
import json
import uuid
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ec


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def create_jwk(*, kid: str | None = None) -> dict[str, str]:
    key = ec.generate_private_key(ec.SECP256R1())
    numbers = key.private_numbers()
    public_numbers = numbers.public_numbers
    kid_value = kid or uuid.uuid4().hex
    return {
        "kty": "EC",
        "crv": "P-256",
        "kid": kid_value,
        "use": "sig",
        "alg": "ES256",
        "x": _b64url(public_numbers.x.to_bytes(32, "big")),
        "y": _b64url(public_numbers.y.to_bytes(32, "big")),
        "d": _b64url(numbers.private_value.to_bytes(32, "big")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an ES256 JWK with a kid header")
    parser.add_argument("--kid", help="Explicit key identifier to use")
    parser.add_argument("--out", type=Path, help="Optional output file to write the JWK JSON")
    args = parser.parse_args()

    jwk = create_jwk(kid=args.kid)
    payload = json.dumps(jwk, indent=2)
    if args.out:
        args.out.write_text(payload)
    print(payload)


if __name__ == "__main__":  # pragma: no cover - CLI utility
    main()
