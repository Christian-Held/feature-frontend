"""Test admin API endpoints."""

import requests
import json

BASE_URL = "http://localhost:8000"

# Login to get token
with open("test_login_payload.json") as f:
    login_data = json.load(f)

print("1. Login as superadmin...")
login_resp = requests.post(f"{BASE_URL}/v1/auth/login", json=login_data)
print(f"   Status: {login_resp.status_code}")

if login_resp.status_code == 200:
    token_data = login_resp.json()
    access_token = token_data.get("accessToken")
    print(f"   ✓ Got access token")

    headers = {"Authorization": f"Bearer {access_token}"}

    # Test /v1/admin/stats
    print("\n2. GET /v1/admin/stats (Platform Statistics)")
    stats_resp = requests.get(f"{BASE_URL}/v1/admin/stats", headers=headers)
    print(f"   Status: {stats_resp.status_code}")
    if stats_resp.status_code == 200:
        stats = stats_resp.json()
        print(f"   ✓ Platform Statistics:")
        print(f"      Total Users: {stats['total_users']}")
        print(f"      Active Users: {stats['active_users']}")
        print(f"      Superadmins: {stats['superadmins']}")
        print(f"      Users with MFA: {stats['users_with_mfa']}")
        print(f"      Active Sessions: {stats['active_sessions']}")
        print(f"      Subscriptions by Plan: {stats['subscriptions_by_plan']}")
        print(f"      Total API Calls (current month): {stats['total_api_calls']}")
    else:
        print(f"   ❌ Error: {stats_resp.text}")

    # Test /v1/admin/users
    print("\n3. GET /v1/admin/users (List Users)")
    users_resp = requests.get(f"{BASE_URL}/v1/admin/users?page=1&page_size=5", headers=headers)
    print(f"   Status: {users_resp.status_code}")
    if users_resp.status_code == 200:
        users_data = users_resp.json()
        print(f"   ✓ Found {users_data['total']} users (showing {len(users_data['items'])}):")
        for user in users_data['items']:
            print(f"      - {user['email']} (superadmin: {user.get('is_superadmin', False)})")
    else:
        print(f"   ❌ Error: {users_resp.text}")

    # Get a user ID for testing
    if users_resp.status_code == 200 and len(users_data['items']) > 0:
        test_user_id = users_data['items'][0]['id']

        # Test upgrade plan endpoint
        print(f"\n4. POST /v1/admin/users/{test_user_id}/upgrade-plan")
        upgrade_payload = {
            "plan_name": "pro",
            "duration_days": 30
        }
        upgrade_resp = requests.post(
            f"{BASE_URL}/v1/admin/users/{test_user_id}/upgrade-plan",
            headers=headers,
            json=upgrade_payload
        )
        print(f"   Status: {upgrade_resp.status_code}")
        if upgrade_resp.status_code == 200:
            upgrade_data = upgrade_resp.json()
            print(f"   ✓ Upgraded user to {upgrade_data['plan_name']} plan")
            print(f"      Subscription ID: {upgrade_data['subscription_id']}")
            print(f"      Expires At: {upgrade_data['expires_at']}")
        else:
            print(f"   ❌ Error: {upgrade_resp.text}")

        # Test revoke sessions endpoint
        print(f"\n5. POST /v1/admin/users/{test_user_id}/revoke-sessions")
        revoke_resp = requests.post(
            f"{BASE_URL}/v1/admin/users/{test_user_id}/revoke-sessions",
            headers=headers
        )
        print(f"   Status: {revoke_resp.status_code}")
        if revoke_resp.status_code == 200:
            revoke_data = revoke_resp.json()
            print(f"   ✓ Revoked {revoke_data['revoked_count']} sessions")
        else:
            print(f"   ❌ Error: {revoke_resp.text}")

        # Test clear rate limits endpoint
        print(f"\n6. POST /v1/admin/users/{test_user_id}/clear-rate-limits")
        clear_resp = requests.post(
            f"{BASE_URL}/v1/admin/users/{test_user_id}/clear-rate-limits",
            headers=headers
        )
        print(f"   Status: {clear_resp.status_code}")
        if clear_resp.status_code == 200:
            clear_data = clear_resp.json()
            print(f"   ✓ {clear_data['message']}")
        else:
            print(f"   ❌ Error: {clear_resp.text}")

    print("\n✅ All admin API endpoint tests completed!")

else:
    print(f"   ❌ Login failed: {login_resp.text}")
