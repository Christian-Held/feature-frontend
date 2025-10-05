import os
from pathlib import Path

from app.core.pricing import get_pricing_table


def test_pricing_table_loads(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(os.getcwd()))
    table = get_pricing_table()
    pricing = table.get("gpt-4.1")
    assert pricing.input == 0.01
    assert pricing.output == 0.03
