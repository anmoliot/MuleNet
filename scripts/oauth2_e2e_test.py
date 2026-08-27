import requests
import time
import sys

KEYCLOAK_URL = "http://localhost:8081/realms/mule-realm/protocol/openid-connect/token"
BACKEND_URL = "http://localhost:8080/api/prediction"

print("Waiting for Keycloak to be ready...")
for _ in range(30):
    try:
        if requests.get("http://localhost:8081/realms/mule-realm/.well-known/openid-configuration").status_code == 200:
            print("Keycloak is ready.")
            break
    except requests.exceptions.ConnectionError:
        pass
    time.sleep(2)
else:
    print("Error: Keycloak not ready.")
    sys.exit(1)

print("Waiting for Backend to be ready...")
for _ in range(30):
    try:
        if requests.get("http://localhost:8080/api/health").status_code == 200:
            print("Backend is ready.")
            break
    except requests.exceptions.ConnectionError:
        pass
    time.sleep(2)
else:
    print("Error: Backend not ready.")
    sys.exit(1)

print("Fetching token from Keycloak...")
data = {
    "client_id": "mulenet-app",
    "username": "investigator1",
    "password": "password",
    "grant_type": "password"
}

response = requests.post(KEYCLOAK_URL, data=data)
if response.status_code != 200:
    print(f"Failed to fetch token: {response.text}")
    sys.exit(1)

token = response.json().get("access_token")
print("Token fetched successfully.")

print("Calling protected endpoint...")
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

payload = {
    "accountId": "AC-123",
    "intakeRequest": {
        "transactions": []
    }
}

api_response = requests.post(BACKEND_URL, json=payload, headers=headers)
# In case the ML service is not up, we might get a 500, but we shouldn't get a 401 or 403.
if api_response.status_code in [401, 403]:
    print(f"Auth failed. Expected 200 or 500, got {api_response.status_code}")
    sys.exit(1)

print(f"Success! API returned status: {api_response.status_code}")
