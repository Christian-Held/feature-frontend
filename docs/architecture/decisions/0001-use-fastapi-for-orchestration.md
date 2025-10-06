# ADR 0001: Use FastAPI for the orchestration service

- **Status:** accepted
- **Date:** 2024-09-18
- **Decision Makers:** Platform Architecture Guild
- **Related Requirements:** Stable REST API, async-ready worker coordination

## Context

Wir benötigen einen Backend-Service, der REST- und WebSocket-Endpunkte bereitstellt, Celery-Worker orchestriert und dynamische Einstellungen handhabt. Das System muss mit modernen Python-Versionen harmonieren, asynchrones I/O unterstützen und eine klare OpenAPI-Schnittstelle erzeugen. Alternativen wie Flask oder Django würden zusätzliche Libraries bzw. monolithische Strukturen erfordern.

## Decision

Wir setzen FastAPI als zentrale Web-Schicht ein. FastAPI stellt automatische OpenAPI-Generierung bereit, integriert sich nahtlos mit Pydantic 2.x und unterstützt asynchrone Endpunkte für WebSockets und Streaming. Die bestehende Codebasis (`app/main.py`, `app/routers/*`) nutzt bereits FastAPI-Routerstrukturen.

## Consequences

- **Positiv:** Schnelle Entwicklung von typisierten Endpunkten, native OpenAPI-Spezifikation und Kompatibilität mit modernem Python.
- **Negativ:** Höhere Lernkurve für Teammitglieder ohne Erfahrung mit Pydantic 2.x oder async Patterns.

## Alternatives Considered

1. **Flask + Flask-RESTX** – würde mehr Boilerplate für Typisierung und async Support erfordern.
2. **Django REST Framework** – schwergewichtiger für den Microservice-Charakter, benötigt eigene ORM/Settings-Struktur.
