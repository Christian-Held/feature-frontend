# CAPTCHA Outage Runbook

## Symptoms
- Login conversions drop while `CaptchaErrorRateHigh` alert fires.
- Grafana shows spike in 400 responses from `/v1/auth/login` requiring CAPTCHA.
- Support reports users blocked by CAPTCHA verification errors.

## Immediate Actions
1. Confirm outage with CAPTCHA provider (Turnstile/hCaptcha) status page.
2. Toggle feature flag to fail-open CAPTCHA challenges for low-risk segments while maintaining rate limits.
3. Increase global rate limit deny lists for abusive IPs and monitor `rate_limit_block_total` to avoid abuse.
4. Notify security and support teams about temporary CAPTCHA bypass.

## Mitigation Steps
- Adjust `AUTH_LOGIN_FAILURE_RATIO` alert threshold temporarily if noise persists.
- Consider enabling additional friction (email verification prompts, cooldown) for high-risk cohorts.

## Recovery
- Once provider recovers, revert feature flags to enforce CAPTCHA.
- Monitor `auth_captcha_challenges_total` and login success to ensure normal operation.
- Document incident timeline and update guardrails if manual intervention required.
