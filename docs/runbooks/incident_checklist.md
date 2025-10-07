# Incident Checklist

## Severity Levels
- **SEV1**: Full authentication outage or data compromise.
- **SEV2**: Partial degradation affecting >10% of users (e.g., refresh failures).
- **SEV3**: Minor degradation or localized issue.

## Initial Response
1. Assign incident commander (IC) and communications lead.
2. Create incident channel (Slack/Teams) and bridge line if SEV1.
3. Acknowledge alerts in PagerDuty and document start time.

## Timeline Management
- IC maintains minute-by-minute timeline of actions and findings.
- Communications lead updates status page and stakeholders every 15 minutes (SEV1) or 30 minutes (SEV2).
- Capture metrics snapshots (Grafana dashboard links) for post-incident review.

## Communication Templates
- **External**: "We are investigating increased authentication failures. Users may experience login errors. Next update in 15 minutes."
- **Internal**: Summarize impact, suspected root cause, and immediate mitigations.

## After Resolution
1. Declare incident resolved and note stop time.
2. Schedule post-incident review within 48 hours.
3. File Jira task for action items and update runbooks/alerts as needed.
