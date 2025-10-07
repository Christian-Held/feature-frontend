# Authentication Service SLOs

## Availability & Latency
- **Auth API Latency**: p95 of `/v1/auth/login` and `/v1/auth/refresh` < **150 ms** over rolling 7 days.
  - Metric: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{path=~"/v1/auth/(login|refresh)"}[5m]))`
  - Alert: `AuthLoginFailureRatioHigh`, `AuthRefreshFailureRatioHigh` provide early warning of elevated errors.

## Reliability
- **Login Error Rate**: < **1%** of total logins over rolling 7 days.
  - Metric: `auth_login_failure_total` vs `auth_login_success_total`.
  - Alert mapping: `AuthLoginFailureRatioHigh` (0.2 threshold) ensures rapid detection; manual review adjusts thresholds during incidents.

- **Email Dispatch Latency**: p95 time from enqueue to send < **30 s**.
  - Metric: `histogram_quantile(0.95, rate(email_send_latency_ms_bucket[5m]))`.
  - Alert mapping: `EmailPipelineFailures` triggers when failures or backlog observed.

## Disaster Recovery
- **Recovery Time Objective (RTO)**: 1 hour for production incident.
- **Recovery Point Objective (RPO)**: 15 minutes for critical data.
  - Processes: automated backups every 15 minutes, restore playbooks tested quarterly.

## Alerting Strategy
- Alerts tuned to fire well before SLO breach (e.g., 20% login failure vs 1% budget) to allow intervention.
- Dashboards (`Auth Overview`, `Email Pipeline`, `Infrastructure Health`) provide operators with SLI visualization for ongoing compliance.
