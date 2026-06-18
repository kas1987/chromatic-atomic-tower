"""Unit tests for scripts/github_app_token.py.

Generates a throwaway RSA key in-process to exercise JWT minting, mocks
urllib for the GitHub API client, and drives the command dispatchers. No real
network calls and no real credentials are used.
"""
from __future__ import annotations

import json

import pytest

from scripts import github_app_token as gat


# ---------------------------------------------------------------------------
# A real (throwaway) RSA private key so make_jwt/encode works for real.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def rsa_pem() -> str:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    # Module-scoped: generated once per session, so 2048-bit costs are one-time.
    # 1024-bit would trip PyJWT's InsecureKeyLengthWarning on decode.
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


# ---------------------------------------------------------------------------
# load_env
# ---------------------------------------------------------------------------

def test_load_env_from_inline_pem(monkeypatch):
    monkeypatch.setenv("GITHUB_APP_ID", "Iv23liABC")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "PEMDATA")
    monkeypatch.delenv("GITHUB_APP_PRIVATE_KEY_PATH", raising=False)
    app_id, pem = gat.load_env()
    assert app_id == "Iv23liABC"
    assert pem == "PEMDATA"


def test_load_env_from_key_path(monkeypatch, tmp_path):
    key_file = tmp_path / "key.pem"
    key_file.write_text("FILE-PEM", encoding="utf-8")
    monkeypatch.setenv("GITHUB_APP_ID", "123")
    monkeypatch.delenv("GITHUB_APP_PRIVATE_KEY", raising=False)
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", str(key_file))
    app_id, pem = gat.load_env()
    assert app_id == "123"
    assert pem == "FILE-PEM"


def test_load_env_missing_app_id_exits(monkeypatch):
    monkeypatch.delenv("GITHUB_APP_ID", raising=False)
    with pytest.raises(SystemExit):
        gat.load_env()


def test_load_env_missing_key_exits(monkeypatch):
    monkeypatch.setenv("GITHUB_APP_ID", "x")
    monkeypatch.delenv("GITHUB_APP_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("GITHUB_APP_PRIVATE_KEY_PATH", raising=False)
    with pytest.raises(SystemExit):
        gat.load_env()


# ---------------------------------------------------------------------------
# make_jwt
# ---------------------------------------------------------------------------

def test_make_jwt_roundtrip(rsa_pem):
    import jwt as pyjwt
    from cryptography.hazmat.primitives import serialization

    token = gat.make_jwt("Iv23liABC", rsa_pem)
    assert isinstance(token, str)

    public_key = serialization.load_pem_private_key(
        rsa_pem.encode("utf-8"), password=None
    ).public_key()
    decoded = pyjwt.decode(token, public_key, algorithms=["RS256"])
    assert decoded["iss"] == "Iv23liABC"
    assert decoded["exp"] > decoded["iat"]


# ---------------------------------------------------------------------------
# gh_api (urllib mocked)
# ---------------------------------------------------------------------------

class _FakeResp:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_gh_api_get_success(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=0):
        captured["url"] = req.full_url
        captured["auth"] = req.headers.get("Authorization")
        return _FakeResp({"ok": True})

    monkeypatch.setattr(gat.urllib.request, "urlopen", fake_urlopen)
    out = gat.gh_api("/app/installations", "TOK")
    assert out == {"ok": True}
    assert captured["url"] == "https://api.github.com/app/installations"
    assert captured["auth"] == "Bearer TOK"


def test_gh_api_http_error_exits(monkeypatch):
    import urllib.error
    import io

    def fake_urlopen(req, timeout=0):
        raise urllib.error.HTTPError(
            req.full_url, 401, "Unauthorized", {}, io.BytesIO(b"bad creds")
        )

    monkeypatch.setattr(gat.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(SystemExit, match="401"):
        gat.gh_api("/x", "TOK")


def test_gh_api_network_error_exits(monkeypatch):
    import urllib.error

    def fake_urlopen(req, timeout=0):
        raise urllib.error.URLError("no route")

    monkeypatch.setattr(gat.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(SystemExit, match="Network error"):
        gat.gh_api("/x", "TOK")


# ---------------------------------------------------------------------------
# command dispatchers
# ---------------------------------------------------------------------------

def test_cmd_jwt_prints_token(rsa_pem, capsys):
    gat.cmd_jwt("app", rsa_pem)
    out = capsys.readouterr().out.strip()
    assert out.count(".") == 2  # header.payload.signature


def test_cmd_installations_lists(monkeypatch, rsa_pem, capsys):
    monkeypatch.setattr(gat, "make_jwt", lambda a, p: "JWT")
    monkeypatch.setattr(gat, "gh_api", lambda *a, **k: [
        {"id": 42, "account": {"login": "octocat", "type": "User"}},
    ])
    gat.cmd_installations("app", rsa_pem)
    out = capsys.readouterr().out
    assert "id=42" in out
    assert "octocat" in out


def test_cmd_token_single_installation(monkeypatch, rsa_pem, capsys):
    monkeypatch.setattr(gat, "make_jwt", lambda a, p: "JWT")
    calls = {"n": 0}

    def fake_api(path, token, method="GET", body=None):
        calls["n"] += 1
        if path == "/app/installations":
            return [{"id": 7, "account": {"login": "o"}}]
        assert path == "/app/installations/7/access_tokens"
        assert method == "POST"
        return {"token": "ghs_secret"}

    monkeypatch.setattr(gat, "gh_api", fake_api)
    gat.cmd_token("app", rsa_pem)
    assert capsys.readouterr().out.strip() == "ghs_secret"


def test_cmd_token_explicit_install_id(monkeypatch, rsa_pem, capsys):
    monkeypatch.setattr(gat, "make_jwt", lambda a, p: "JWT")

    def fake_api(path, token, method="GET", body=None):
        assert path == "/app/installations/99/access_tokens"
        return {"token": "ghs_99"}

    monkeypatch.setattr(gat, "gh_api", fake_api)
    gat.cmd_token("app", rsa_pem, install_id="99")
    assert capsys.readouterr().out.strip() == "ghs_99"


def test_cmd_token_multiple_installations_exits(monkeypatch, rsa_pem):
    monkeypatch.setattr(gat, "make_jwt", lambda a, p: "JWT")
    monkeypatch.setattr(gat, "gh_api", lambda *a, **k: [
        {"id": 1, "account": {"login": "a"}},
        {"id": 2, "account": {"login": "b"}},
    ])
    with pytest.raises(SystemExit):
        gat.cmd_token("app", rsa_pem)


def test_cmd_token_no_installations_exits(monkeypatch, rsa_pem):
    monkeypatch.setattr(gat, "make_jwt", lambda a, p: "JWT")
    monkeypatch.setattr(gat, "gh_api", lambda *a, **k: [])
    with pytest.raises(SystemExit):
        gat.cmd_token("app", rsa_pem)


# ---------------------------------------------------------------------------
# main dispatch
# ---------------------------------------------------------------------------

def test_main_no_args_prints_doc(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["github_app_token.py"])
    with pytest.raises(SystemExit) as exc:
        gat.main()
    assert exc.value.code == 0


def test_main_jwt_subcommand(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["github_app_token.py", "jwt"])
    monkeypatch.setattr(gat, "load_env", lambda: ("app", "pem"))
    monkeypatch.setattr(gat, "cmd_jwt", lambda a, p: print("JWT-OUT"))
    gat.main()
    assert "JWT-OUT" in capsys.readouterr().out


def test_main_token_with_install_id(monkeypatch):
    monkeypatch.setattr("sys.argv", [
        "github_app_token.py", "token", "--install-id", "55",
    ])
    monkeypatch.setattr(gat, "load_env", lambda: ("app", "pem"))
    captured = {}
    monkeypatch.setattr(
        gat, "cmd_token",
        lambda a, p, install_id=None: captured.update(id=install_id),
    )
    gat.main()
    assert captured["id"] == "55"


def test_main_token_install_id_missing_value_exits(monkeypatch):
    monkeypatch.setattr("sys.argv", ["github_app_token.py", "token", "--install-id"])
    monkeypatch.setattr(gat, "load_env", lambda: ("app", "pem"))
    with pytest.raises(SystemExit, match="requires a value"):
        gat.main()


def test_main_unknown_subcommand_exits(monkeypatch):
    monkeypatch.setattr("sys.argv", ["github_app_token.py", "bogus"])
    monkeypatch.setattr(gat, "load_env", lambda: ("app", "pem"))
    with pytest.raises(SystemExit) as exc:
        gat.main()
    assert exc.value.code == 1
