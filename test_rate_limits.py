"""Test rate limit endpoint."""

import requests
import json

# Login first to get a token
with open("test_login_payload.json") as f:
    login_data = json.load(f)

login_response = requests.post(
    "http://localhost:8000/v1/auth/login",
    json=login_data
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    print(login_response.text)
    exit(1)

token = login_response.json()["accessToken"]
headers = {"Authorization": f"Bearer {token}"}

# Test rate limit endpoint
print("\n📊 Testing Rate Limit Endpoint")
print("=" * 60)

response = requests.get(
    "http://localhost:8000/v1/subscription/rate-limits",
    headers=headers
)

if response.status_code == 200:
    data = response.json()
    print(f"✅ Rate Limit Info - 200 OK")
    print(f"   Base Limit: {data['base_limit']} req/min")
    print(f"   Multiplier: {data['multiplier']}x")
    print(f"   Effective Limit: {data['effective_limit']} req/min")
    print(f"   Plan: {data['plan_name']}")
else:
    print(f"❌ Rate Limit Info - {response.status_code}")
    print(response.text)

print("\n" + "=" * 60)
print("✅ All tests completed!")
