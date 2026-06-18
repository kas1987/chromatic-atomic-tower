#!/usr/bin/env python3
"""
Generate a GitHub App JWT and installation access token.

Usage:
  python scripts/github_app_token.py jwt                        # print JWT only
  python scripts/github_app_token.py token [--install-id ID]    # print installation token
  python scripts/github_app_token.py installations              # list installation IDs

Env vars (required):
  GITHUB_APP_ID               Client ID (e.g. Iv23li...) or numeric App ID
  GITHUB_APP_PRIVATE_KEY_PATH path to .pem private key file
     OR
  GITHUB_APP_PRIVATE_KEY      raw PEM content (for CI secrets managers)

GitHub now accepts Client ID as the JWT issuer — preferred over numeric App ID.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

try:
    import jwt as pyjwt
except ImportError:
    sys.exit("Missing PyJWT — run: pip install PyJWT cryptography")


def load_env() -> tuple[str, str]:
    app_id = os.environ.get("GITHUB_APP_ID")
    if not app_id:
        sys.exit("Set GITHUB_APP_ID to your Client ID or numeric App ID")

    pem = os.environ.get("GITHUB_APP_PRIVATE_KEY")
    if not pem:
        path = os.environ.get("GITHUB_APP_PRIVATE_KEY_PATH")
        if not path:
            sys.exit("Set GITHUB_APP_PRIVATE_KEY_PATH or GITHUB_APP_PRIVATE_KEY")
        with open(path) as fh:
            pem = fh.read()

    return app_id, pem


def make_jwt(app_id: str, pem: str) -> str:
    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 540, "iss": app_id}
    token = pyjwt.encode(payload, pem, algorithm="RS256")
    # PyJWT 1.x returns bytes; 2.x returns str. Normalize to str.
    if isinstance(token, bytes):
        return token.decode("utf-8")
    return token


def gh_api(path: str, token: str, method: str = "GET", body: dict | None = None) -> dict | list:
    url = f"https://api.github.com{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"GitHub API error {e.code}: {e.read().decode('utf-8', errors='ignore')}")
    except urllib.error.URLError as e:
        sys.exit(f"Network error: {e.reason}")


def cmd_jwt(app_id: str, pem: str) -> None:
    print(make_jwt(app_id, pem))


def cmd_installations(app_id: str, pem: str) -> None:
    token = make_jwt(app_id, pem)
    installs = gh_api("/app/installations", token)
    for i in installs:
        print(f"  id={i['id']}  account={i['account']['login']}  type={i['account']['type']}")


def cmd_token(app_id: str, pem: str, install_id: str | None = None) -> None:
    token = make_jwt(app_id, pem)

    if not install_id:
        installs = gh_api("/app/installations", token)
        if not installs:
            sys.exit("No installations found for this App")
        if len(installs) == 1:
            install_id = str(installs[0]["id"])
        else:
            print("Multiple installations — pass --install-id ID. Available:")
            for i in installs:
                print(f"  {i['id']}  {i['account']['login']}")
            sys.exit(1)

    result = gh_api(f"/app/installations/{install_id}/access_tokens", token, method="POST")
    print(result["token"])


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    app_id, pem = load_env()
    cmd = args[0]

    if cmd == "jwt":
        cmd_jwt(app_id, pem)
    elif cmd == "installations":
        cmd_installations(app_id, pem)
    elif cmd == "token":
        install_id = None
        if "--install-id" in args:
            idx = args.index("--install-id")
            if idx + 1 < len(args):
                install_id = args[idx + 1]
            else:
                sys.exit("Error: --install-id requires a value")
        cmd_token(app_id, pem, install_id)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
