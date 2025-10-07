# JWT Key Rotation Runbook

## Prerequisites
- Ensure `JWT_JWK_CURRENT`, `JWT_JWK_NEXT`, and `JWT_JWK_PREVIOUS` environment variables are configured.
- Celery workers and API pods have access to new keys prior to promotion.

## Generate NEXT Key
1. Run `python -m backend.scripts.jwk_generate --out jwks/next.json` to create a new ES256 JWK.
2. Distribute the generated JSON to secure storage and update `JWT_JWK_NEXT` across environments.
3. Deploy application with new NEXT key and verify `/healthz` and JWKS exposure.

## Promote NEXT to CURRENT
1. Execute `python -m backend.scripts.jwk_rotate_promote jwks/` to promote NEXT->CURRENT and generate a fresh NEXT.
2. Update environment configuration: set `JWT_JWK_CURRENT` to promoted key, `JWT_JWK_PREVIOUS` to prior CURRENT, and `JWT_JWK_NEXT` to new value.
3. Deploy API and worker pods; confirm they pick up updated keys.

## Post-Rotation Validation
- Call `/v1/auth/login` to obtain access/refresh tokens; ensure `kid` header matches new CURRENT.
- Verify refresh flows using tokens minted before rotation for 24 hours (grace period) and ensure they succeed.
- Monitor alerts: `AuthRefreshFailureRatioHigh`, `AuthLoginFailureRatioHigh`, and application logs for signature errors.

## Rollback
- If issues arise, revert `JWT_JWK_CURRENT`/`JWT_JWK_NEXT` to previous values and redeploy.
- Investigate errors, regenerate NEXT once stable, and resume runbook.
