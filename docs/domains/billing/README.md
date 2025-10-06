# Billing Domain

## Purpose
- Plant eine spätere Abrechnungsschicht für Agenten- und Infrastrukturkosten.
- Ziel ist Kosten-Transparenz pro Kunde, Projekt und Agent bereitzustellen.

## Boundaries
- Wird Kostendaten aus `cost_entries` aggregieren und mit Provider-Raten (OpenAI, Claude, etc.) korrelieren.
- Budget-Limits aus Orchestration dienen als Input, Auth liefert Zuordnung zu Konten/Teams.
- Aktuell nicht umgesetzt; fungiert als Dokumentationsanker für zukünftige Entwicklung.

## API
- Geplante Services:
  - `GET /billing/statements` für periodische Reports.
  - `POST /billing/allocations` zur Budgetzuordnung.
  - `GET /billing/providers` für Kostenmodelle.

## Dependencies
- Pricing-Datenquelle (`pricing.json` und Settings-API).
- Externe Abrechnungssysteme oder ERP-Schnittstellen.
- Datenbankerweiterungen für Rechnungen und Buchungssätze.

## Integration Points
- Orchestration Domain: konsumiert Budgetwarnungen und liefert Kosten-Einzelposten.
- Finance Tools: Export als CSV/JSON, Webhooks für Accounting.

## Extension Points
- Multi-Währungsunterstützung.
- Usage-basiertes Alerting (PagerDuty, Slack, E-Mail).
- Automatisierte Chargeback-Berechnung pro Team.
