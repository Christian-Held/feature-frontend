# Database Migration Failure Runbook

## Context
Zero-downtime migrations use alembic with transactional DDL. Failures must be detected early to prevent data corruption.

## Detection
- CI or deploy pipeline reports alembic error.
- `/readyz` returns 503 with database error annotations.
- Logs show migration script exceptions or lock timeouts.

## Immediate Response
1. Halt further deployments; notify database owner and incident commander.
2. Identify the migration revision that failed (`alembic history --verbose`).
3. Check database locks and long-running transactions (`pg_stat_activity`).

## Rollback Strategy
- If migration is non-destructive: issue `alembic downgrade <previous>` and verify schema.
- For destructive changes: restore from latest backup or failover replica.
- Ensure application version matches database schema before resuming traffic.

## Zero-Downtime Guidelines
- Prefer additive migrations with `ADD COLUMN` + backfill jobs.
- For column drops/renames, deploy in phases (add new column, dual-write, cutover, cleanup).
- Use feature flags to gate new logic until schema confirmed.

## Post-Mortem
- Document failure mode, impacted queries, and remediation steps.
- Add automated migration dry-run in staging replicating production data volume.
