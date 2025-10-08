"""Test subscription API endpoints."""

import requests
import json

BASE_URL = "http://localhost:8000"

# Login to get token
with open("test_login_payload.json") as f:
    login_data = json.load(f)

print("1. Login...")
login_resp = requests.post(f"{BASE_URL}/v1/auth/login", json=login_data)
print(f"   Status: {login_resp.status_code}")

if login_resp.status_code == 200:
    token_data = login_resp.json()
    access_token = token_data.get("access_token")
    print(f"   ✓ Got access token")

    headers = {"Authorization": f"Bearer {access_token}"}

    # Test /v1/subscription/plans (public endpoint)
    print("\n2. GET /v1/subscription/plans")
    plans_resp = requests.get(f"{BASE_URL}/v1/subscription/plans")
    print(f"   Status: {plans_resp.status_code}")
    if plans_resp.status_code == 200:
        plans = plans_resp.json()
        print(f"   ✓ Found {len(plans['plans'])} plans:")
        for plan in plans['plans']:
            print(f"      - {plan['display_name']} ({plan['name']}): ${plan['price_cents']/100}/mo")

    # Test /v1/subscription/me
    print("\n3. GET /v1/subscription/me")
    my_sub_resp = requests.get(f"{BASE_URL}/v1/subscription/me", headers=headers)
    print(f"   Status: {my_sub_resp.status_code}")
    if my_sub_resp.status_code == 200:
        sub_data = my_sub_resp.json()
        plan = sub_data['plan']
        subscription = sub_data['subscription']
        print(f"   ✓ Current plan: {plan['display_name']}")
        print(f"      Subscription status: {subscription['status'] if subscription else 'No active subscription (using default free plan)'}")

    # Test /v1/subscription/usage
    print("\n4. GET /v1/subscription/usage")
    usage_resp = requests.get(f"{BASE_URL}/v1/subscription/usage", headers=headers)
    print(f"   Status: {usage_resp.status_code}")
    if usage_resp.status_code == 200:
        usage_data = usage_resp.json()
        usage = usage_data['usage']
        limits = usage_data['limits']
        print(f"   ✓ Usage (current period):")
        if usage:
            print(f"      Jobs: {usage['jobs_created']}/{limits['jobs'] if limits['jobs'] else 'unlimited'}")
            print(f"      API calls: {usage['api_calls']}/{limits['api_calls'] if limits['api_calls'] else 'unlimited'}")
            print(f"      Storage: {usage['storage_used_mb']} MB / {limits['storage'] if limits['storage'] else 'unlimited'} MB")
        else:
            print(f"      No usage recorded yet")
            print(f"      Limits: Jobs={limits['jobs']}, API calls={limits['api_calls']}, Storage={limits['storage']} MB")

    print("\n✅ All subscription API endpoints working!")

else:
    print(f"   ❌ Login failed: {login_resp.text}")
