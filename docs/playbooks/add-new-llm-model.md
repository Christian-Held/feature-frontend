# Playbook: Add a new LLM model

## Preconditions
- Pricing-Eintrag in `pricing.json` oder externer Quelle vorhanden.
- API-Key und Provider-spezifische Zugangsdaten verfügbar.
- Tests (`uv run pytest`) laufen lokal.

## Steps
1. **Pricing aktualisieren**
   - Ergänze `pricing.json` um Tarifinformationen (`prompt`, `completion`, `currency`).
   - Falls neues Preismodell erforderlich ist, aktualisiere `app/core/pricing.py`.
2. **Settings-API erweitern**
   - Füge das Modell als Variant in `docs/integration/API_CONTRACTS.yaml` (`ModelVariant`) hinzu, wenn API-Kunden es sehen sollen.
   - Stelle sicher, dass `get_pricing_table()` das Modell zurückliefert.
3. **Environment Defaults setzen**
   - Aktualisiere `.env.example` mit neuem Default (falls erforderlich).
   - Verwende `PUT /api/models/{model}` oder `make docs-validate` nach Anpassung der Spezifikation.
4. **Provider Implementation**
   - Implementiere ggf. neue Klasse in `app/llm/` (z. B. `my_provider.py`).
   - Registriere sie im Agent Router oder in den Settings.
5. **Tests & Validierung**
   - Führe `uv run pytest tests` aus.
   - Optional: Smoke-Test via `scripts/run_agent.py --agent coder --model <model>`.
6. **Dokumentation**
   - Aktualisiere `AGENTS.md` mit Kostencharakteristik.
   - Ergänze Release Notes.

## Rollback
- Entferne den Pricing-Eintrag und setze Modell-Env-Wert auf vorherige Variante.
- Verifiziere, dass `docs/integration/API_CONTRACTS.yaml` keine Referenzen mehr enthält.
