#!/usr/bin/env python3
"""Standalone verification script for Zoho Catalyst QuickML integration.

Verifies:
1. Existing OAuth logic in CatalystRestDatastore successfully retrieves an access token.
2. QuickML endpoint is reachable.
3. Authentication and CATALYST-ORG header work.
4. Request format is accepted by QuickML.
5. Response is successfully received and parsed.

Exit codes:
- 0: Success
- 1: Authentication failed
- 2: QuickML request failed
- 3: Invalid/missing environment variables
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path to enable imports from backend
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv

    load_dotenv()
    env_file = PROJECT_ROOT / "configs" / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

import requests

from backend.app.db.catalyst import CatalystRestDatastore


def parse_json_env(var_name: str) -> dict[str, str] | None:
    """Parse a JSON-formatted environment variable if present."""
    raw = os.getenv(var_name)
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {str(k): str(v) for k, v in parsed.items()}
    except json.JSONDecodeError:
        pass
    return None


def get_config() -> tuple[dict[str, str], dict[str, str], str, str]:
    """Retrieve and validate required configuration from environment variables.

    Returns:
        tuple containing (auth, options, org_id, project_id)

    Exits:
        Code 3 if essential environment variables are missing or invalid.
    """
    # 1. Catalyst OAuth credentials (auth)
    auth = parse_json_env("CATALYST_AUTH")
    if not auth:
        client_id = os.getenv("CATALYST_CLIENT_ID") or os.getenv("CLIENT_ID")
        client_secret = os.getenv("CATALYST_CLIENT_SECRET") or os.getenv("CLIENT_SECRET")
        refresh_token = os.getenv("CATALYST_REFRESH_TOKEN") or os.getenv("REFRESH_TOKEN")
        if client_id and client_secret and refresh_token:
            auth = {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
            }

    # 2. Catalyst options (options)
    options = parse_json_env("CATALYST_OPTIONS")
    if not options:
        project_id = os.getenv("CATALYST_PROJECT_ID") or os.getenv("QUICKML_PROJECT_ID")
        if project_id:
            options = {
                "project_id": project_id,
                "api_domain": os.getenv("CATALYST_API_DOMAIN", "https://api.catalyst.zoho.in"),
                "accounts_domain": os.getenv("CATALYST_ACCOUNTS_DOMAIN", "https://accounts.zoho.in"),
                "environment": os.getenv("CATALYST_ENVIRONMENT", "Development"),
            }
            project_key = os.getenv("CATALYST_PROJECT_KEY")
            if project_key:
                options["project_key"] = project_key

    # Ensure default fields are populated and project_key is safely defaulted if absent
    if options:
        options.setdefault("api_domain", os.getenv("CATALYST_API_DOMAIN", "https://api.catalyst.zoho.in"))
        options.setdefault("accounts_domain", os.getenv("CATALYST_ACCOUNTS_DOMAIN", "https://accounts.zoho.in"))
        options.setdefault("environment", os.getenv("CATALYST_ENVIRONMENT", "Development"))
        options.setdefault("project_key", os.getenv("CATALYST_PROJECT_KEY", ""))

    # 3. Catalyst Org ID header
    org_id = os.getenv("CATALYST_ORG") or os.getenv("CATALYST_ORG_ID")

    # Validate auth dict
    if not auth or not all(k in auth for k in ("client_id", "client_secret", "refresh_token")):
        print("Error: Missing or incomplete Catalyst OAuth credentials.", file=sys.stderr)
        print("Please set CATALYST_AUTH JSON or individual CATALYST_CLIENT_ID, CATALYST_CLIENT_SECRET, CATALYST_REFRESH_TOKEN.", file=sys.stderr)
        sys.exit(3)

    # Validate options dict (requires project_id, api_domain, accounts_domain, environment)
    required_options = ("project_id", "api_domain", "accounts_domain", "environment")
    if not options or not all(options.get(k) for k in required_options):
        print("Error: Missing or incomplete Catalyst options.", file=sys.stderr)
        print("Please set CATALYST_OPTIONS JSON or individual CATALYST_PROJECT_ID (or QUICKML_PROJECT_ID).", file=sys.stderr)
        sys.exit(3)

    # Validate Org ID
    if not org_id:
        print("Error: Missing CATALYST-ORG environment variable.", file=sys.stderr)
        print("Please set CATALYST_ORG or CATALYST_ORG_ID in environment.", file=sys.stderr)
        sys.exit(3)

    project_id = options["project_id"]
    return auth, options, org_id, project_id


def main() -> None:
    # Step 1: Read and validate environment variables
    auth, options, org_id, project_id = get_config()

    # Step 2: Reuse CatalystRestDatastore to acquire access token
    try:
        datastore = CatalystRestDatastore(auth=auth, options=options)
        token = datastore.access_token()
        print("=== OAuth ===")
        print("Access token acquired")
    except Exception as e:
        print("=== OAuth ===")
        print(f"Authentication failed: {e}")
        sys.exit(1)

    # Step 3: Prepare QuickML endpoint URL, headers, and body
    api_domain = str(options.get("api_domain") or "https://api.catalyst.zoho.in").rstrip("/")
    url = f"{api_domain}/quickml/v1/project/{project_id}/glm/chat"

    headers = {
        "Authorization": f"Zoho-oauthtoken {token}",
        "CATALYST-ORG": org_id,
        "Content-Type": "application/json",
    }

    body = {
        "model": "crm-di-glm47b_30b_it",
        "messages": [
            {
                "role": "user",
                "content": "Reply with exactly SUCCESS."
            }
        ],
        "temperature": 0,
        "max_tokens": 20,
        "stream": False,
        "chat_template_kwargs": {
            "enable_thinking": False
        }
    }

    # Step 4: Send POST request to QuickML chat endpoint
    print("\n=== Request ===")
    print("Sending request...")

    try:
        response = requests.post(
            url,
            headers=headers,
            json=body,
            timeout=datastore.timeout,
        )

        print("\n=== Response ===")
        print(f"HTTP status: {response.status_code}")

        if response.status_code in (200, 201):
            try:
                json_resp = response.json()
                print(json.dumps(json_resp, indent=2))
            except Exception:
                print(response.text)
            sys.exit(0)
        else:
            print(f"Headers: {dict(response.headers)}")
            print(f"Body: {response.text}")
            sys.exit(2)

    except requests.RequestException as e:
        print("\n=== Response ===")
        print(f"HTTP status: Request Error - {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Headers: {dict(e.response.headers)}")
            print(f"Body: {e.response.text}")
        else:
            print("Headers: None")
            print(f"Body: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
