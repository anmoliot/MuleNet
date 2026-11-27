"""Configure admin-only tenant attributes on an explicitly selected local Keycloak."""

import argparse
import json
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def configure(client, username, password):
    response = client.post(
        "/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": username,
            "password": password,
        },
    )
    response.raise_for_status()
    headers = {"Authorization": "Bearer " + response.json()["access_token"]}
    route = "/admin/realms/mulenet/users/profile"
    response = client.get(route, headers=headers)
    response.raise_for_status()
    profile = response.json()
    tenant = {
        "name": "tenant",
        "displayName": "Tenant",
        "multivalued": False,
        "permissions": {"view": ["admin"], "edit": ["admin"]},
        "validations": {"pattern": {"pattern": "^[a-zA-Z0-9_-]{1,64}$"}},
    }
    profile["attributes"] = [item for item in profile.get("attributes", []) if item["name"] != "tenant"] + [tenant]
    # Keycloak represents the disabled policy as null, not an enum named DISABLED.
    profile["unmanagedAttributePolicy"] = None
    response = client.put(route, headers=headers, json=profile)
    if response.status_code == 400:
        raise RuntimeError("Keycloak rejected the static user-profile configuration: " + response.text[:2000])
    response.raise_for_status()
    verified = client.get(route, headers=headers)
    verified.raise_for_status()
    current = next(item for item in verified.json()["attributes"] if item["name"] == "tenant")
    if current["permissions"] != tenant["permissions"] or verified.json().get("unmanagedAttributePolicy") is not None:
        raise RuntimeError("Keycloak tenant-edit restriction was not persisted")
    return {"tenant_edit": "admin_only", "unmanaged_attributes": "disabled", "users_created": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=ROOT / ".env")
    parser.add_argument(
        "--url", choices=["http://localhost:8081", "http://127.0.0.1:8081"], default="http://localhost:8081"
    )
    args = parser.parse_args()
    values = dotenv_values(args.env)
    with httpx.Client(base_url=args.url, timeout=15, trust_env=False) as client:
        report = configure(client, values["KEYCLOAK_ADMIN"], values["KEYCLOAK_ADMIN_PASSWORD"])
    (ROOT / "reports/keycloak-configuration.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
