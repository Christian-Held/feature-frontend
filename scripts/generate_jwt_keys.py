from jwcrypto import jwk
import json, secrets, base64

# ES256 keypair
key = jwk.JWK.generate(kty='EC', crv='P-256')
print("JWT_JWK_CURRENT=", key.export(private_key=True))

# Random 32-byte encryption key (for MFA/recovery)
enc_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
print("ENCRYPTION_KEYS={\"v1\":\"%s\"}" % enc_key)
print("EMAIL_VERIFICATION_SECRET=", secrets.token_urlsafe(32))
