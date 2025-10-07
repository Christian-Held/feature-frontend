# Email Outage Runbook

## Symptoms
- Prometheus `EmailPipelineFailures` alert firing.
- Grafana `Email Pipeline` dashboard shows failed deliveries or growing latency.
- Support tickets indicating missing verification or reset emails.

## Immediate Actions
1. Acknowledge the alert in PagerDuty and assign an incident commander.
2. Verify provider status (SES, SendGrid, etc.) and check for maintenance notices.
3. Inspect Celery queue depth (`celery_task_queue_length{queue="auth-emails"}`) and worker logs for delivery errors.
4. If provider outage is confirmed, disable non-critical templates via feature flags or config to reduce volume.
5. Retry failed jobs by re-queuing `auth-emails` tasks once provider is stable.
6. Communicate status to support and update status page with impact and ETA.

## Recovery Steps
- After provider recovers, re-enable templates and monitor `email_send_latency_ms` histogram for normalization.
- Verify backlog drains below 100 queued emails.
- Send post-incident summary and update runbook with any new learnings.
