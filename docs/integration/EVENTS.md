# Event Streams

Job-bezogene Ereignisse werden über Redis Pub/Sub (`job-events`) verteilt und über den WebSocket-Endpunkt `/ws/jobs` ausgespielt. Alle Nachrichten besitzen folgende Grundstruktur:

```json
{
  "type": "job.updated",
  "payload": {
    "id": "<job-id>",
    "status": "running",
    "task": "...",
    "repo_owner": "...",
    "repo_name": "...",
    "branch_base": "main",
    "budget_usd": 50.0,
    "max_requests": 30,
    "max_minutes": 45,
    "model_cto": "gpt-4o-mini-plan",
    "model_coder": "gpt-4o-coder",
    "cost_usd": 3.2,
    "tokens_in": 4500,
    "tokens_out": 3200,
    "requests_made": 4,
    "progress": 0.66,
    "last_action": "plan",
    "pr_links": ["https://github.com/org/repo/pull/123"],
    "created_at": "2024-09-18T10:15:00Z",
    "updated_at": "2024-09-18T10:25:00Z"
  }
}
```

## Event Types

| Event            | Auslöser                                                   | Hinweise |
|------------------|------------------------------------------------------------|----------|
| `job.created`    | `/tasks` legt neuen Job an                                  | Payload enthält initiale Budget-/Repo-Daten. |
| `job.updated`    | Statusänderung, Step-Fortschritt, Kostenupdate (`execute_job`) | `progress` berechnet Completed Steps / Total Steps. |
| `job.cancelled`  | `/jobs/{id}/cancel` markiert Job als abgebrochen             | Konsumenten sollten laufende Anzeigen schließen. |
| `job.completed`  | Alle Steps erfolgreich abgeschlossen, optional PR erstellt   | Letzte Aktion (`last_action`) gibt finalen Step an. |
| `job.failed`     | Fehler im Worker, Budget überschritten oder Hard-Failure    | Folgeaktionen: Incident-Workflow, Alerting. |

## Konsum über WebSocket

1. Öffne WebSocket-Verbindung zu `ws://<host>/ws/jobs`.
2. Nach `101 Switching Protocols` liefert der Server JSON-Nachrichten wie oben.
3. Verbindung wird serverseitig geschlossen, wenn Redis oder Worker nicht verfügbar ist. Client sollte automatische Reconnects implementieren.

## Fehlertoleranz

- Bei JSON-Parsing-Fehlern im Pub/Sub-Stream wird das Ereignis verworfen, der Stream bleibt aktiv (`job_event_decode_failed`).
- Redis-Verbindungsfehler werden geloggt; Clients sehen ggf. keine neuen Events bis zum Reconnect.
- `payload.pr_links` kann leer sein, wenn kein Pull Request erzeugt wurde.
