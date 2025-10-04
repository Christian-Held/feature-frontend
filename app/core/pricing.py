from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from .config import get_settings


@dataclass
class Pricing:
    input: float
    output: float


class PricingTable:
    def __init__(self, data: Dict[str, Dict[str, float]]):
        self.data = data

    @classmethod
    def load(cls, path: Path) -> "PricingTable":
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        return cls(raw)

    def get(self, model: str) -> Pricing:
        entry = self.data.get(model, self.data.get("default"))
        if not entry:
            raise KeyError(f"No pricing for model {model} and no default entry")
        return Pricing(input=float(entry["input"]), output=float(entry["output"]))


_pricing_table: PricingTable | None = None


def get_pricing_table() -> PricingTable:
    global _pricing_table
    if _pricing_table is None:
        settings = get_settings()
        path = Path("pricing.json")
        if not path.exists():
            raise FileNotFoundError("pricing.json missing")
        _pricing_table = PricingTable.load(path)
    return _pricing_table
