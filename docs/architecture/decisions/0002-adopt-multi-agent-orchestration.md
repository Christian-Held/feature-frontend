# ADR 0002: Adopt a multi-agent orchestration model

- **Status:** accepted
- **Date:** 2024-09-18
- **Decision Makers:** Platform Architecture Guild
- **Related Requirements:** Kostenkontrolle, Spezialisierbare Workflows, Resilienz

## Context

Die Roadmap fordert skalierbare Automatisierung mit unterschiedlichen Qualitäts- und Kostenniveaus. Ein einziger LLM-Agent konnte entweder die Qualitäts- oder Kostenanforderungen nicht erfüllen. Unsere Policy-Datei `AGENTS.md` beschreibt bereits klare Rollen (CTO, Coder, CustomCoder, ClaudeCode, Codex) und deren Interaktionen.

## Decision

Wir etablieren einen Router, der Aufgaben anhand von Komplexität, Budget und Profilzuordnung auf spezialisierte Agents verteilt. Jeder Agent implementiert das `BaseAgent`-Interface und kann unabhängig skaliert und ausgetauscht werden. Redis Pub/Sub unterstützt Fallback-Mechanismen, und Kosten werden pro Agent nachverfolgt.

## Consequences

- **Positiv:** Verbesserte Qualität durch Spezialisierung, flexibel skalierbare Kostenprofile, robuste Fallbacks.
- **Negativ:** Höhere Komplexität beim Betrieb (mehr Services, Monitoring-Aufwand) und erhöhter Bedarf an klarer Dokumentation.

## Alternatives Considered

1. **Single-Agent-Architektur** – scheiterte an Budget- und Spezialisierungsanforderungen.
2. **Externes Orchestrierungstool** – hätte zusätzliche Latenz und Integrationsaufwand erzeugt, ohne direkten Nutzen für unsere Agent-Policies.
