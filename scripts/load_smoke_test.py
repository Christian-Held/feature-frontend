"""Simple load smoke test for login and refresh endpoints."""

from __future__ import annotations

import argparse
import time
from typing import List

import requests


def percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    k = max(int(round((pct / 100.0) * len(values))) - 1, 0)
    return sorted(values)[k]


def run_smoke_test(base_url: str, email: str, password: str, iterations: int, threshold_ms: float) -> None:
    login_durations: List[float] = []
    refresh_durations: List[float] = []

    for _ in range(iterations):
        start = time.perf_counter()
        login_response = requests.post(
            f"{base_url}/v1/auth/login",
            json={"email": email, "password": password},
            timeout=10,
        )
        login_duration = (time.perf_counter() - start) * 1000
        login_durations.append(login_duration)
        if login_response.status_code != 200:
            raise SystemExit(f"Login failed with status {login_response.status_code}: {login_response.text}")

        payload = login_response.json()
        refresh_token = payload.get("refresh_token")
        if not refresh_token:
            raise SystemExit("Login response missing refresh_token")

        start = time.perf_counter()
        refresh_response = requests.post(
            f"{base_url}/v1/auth/refresh",
            json={"refresh_token": refresh_token},
            timeout=10,
        )
        refresh_duration = (time.perf_counter() - start) * 1000
        refresh_durations.append(refresh_duration)
        if refresh_response.status_code != 200:
            raise SystemExit(f"Refresh failed with status {refresh_response.status_code}: {refresh_response.text}")

    login_p95 = percentile(login_durations, 95)
    refresh_p95 = percentile(refresh_durations, 95)

    print(f"Login durations ms: min={min(login_durations):.2f} max={max(login_durations):.2f} p95={login_p95:.2f}")
    print(f"Refresh durations ms: min={min(refresh_durations):.2f} max={max(refresh_durations):.2f} p95={refresh_p95:.2f}")

    if login_p95 > threshold_ms or refresh_p95 > threshold_ms:
        raise SystemExit(
            f"p95 latency exceeded threshold {threshold_ms}ms (login={login_p95:.2f}, refresh={refresh_p95:.2f})"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Load smoke test for auth endpoints")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL for the auth API")
    parser.add_argument("--email", required=True, help="Test account email")
    parser.add_argument("--password", required=True, help="Test account password")
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--threshold-ms", type=float, default=150.0)
    args = parser.parse_args()

    run_smoke_test(args.base_url, args.email, args.password, args.iterations, args.threshold_ms)


if __name__ == "__main__":  # pragma: no cover - manual utility
    main()
