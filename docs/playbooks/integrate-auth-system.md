# Playbook: Integrate authentication system (future)

## Goal
Rollout eines zentralen Authentifizierungsdienstes für API, Dashboard und Worker-Komponenten.

## Preparation
- Entscheide über Auth-Provider (z. B. Auth0, Keycloak, Azure AD).
- Definiere Rollenmodell (Viewer, Operator, Admin) und Zuordnung zu Agentenaktionen.
- Plane Migrationspfad für bestehende Deployments ohne Downtime.

## Target Architecture
1. **Identity Provider** stellt OIDC/OAuth2 Tokens bereit.
2. **FastAPI Backend** validiert Tokens via Middleware/Dependencies.
3. **Frontend** nutzt PKCE Flow und persistiert Tokens sicher.
4. **Worker** authentifizieren sich über Client Credentials für Management-Endpunkte.

## Integration Steps (Draft)
1. **Bootstrap Provider**
   - Erstelle Tenants, Clients und Secrets.
   - Konfiguriere Redirect-URIs (`http://localhost:5173/callback`, Produktionsdomains).
2. **Backend Anpassung**
   - Ergänze Auth-Dependency (z. B. `fastapi.security.OAuth2AuthorizationCodeBearer`).
   - Sichere kritische Routen (`/tasks`, `/jobs/*`, `/api/env`, `/api/models`).
   - Hinterlege Rollenprüfungen (z. B. Operator darf `/tasks`, Admin darf `/api/env`).
3. **Frontend Update**
   - Implementiere Login-Flow, Token-Speicher (Secure Storage) und Logout.
   - Zeige Rollen im UI an und verstecke geschützte Aktionen.
4. **Service Accounts**
   - Für Celery Worker / Automationen Client-Credential-Flows bereitstellen.
   - Secrets über `.env` und Settings-API verwalten.
5. **Observability & Auditing**
   - Aktivere Access Logs, Audit Events und Alarmierung bei Auth-Fehlern.
   - Ergänze Telemetrie (`app/telemetry`) für Auth-Status.

## Validation
- End-to-End Tests mit verschiedenen Rollen.
- Penetrationstest oder Security Review einplanen.
- Update `docs/domains/authentication/README.md` mit finalem Design.

## Rollback Plan
- Feature-Flag einführen (`AUTH_ENABLED`).
- Bei Problemen Flag deaktivieren, Tokens invalidieren und UIs informieren.
