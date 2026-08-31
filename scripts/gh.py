"""A tiny GitHub REST + GraphQL client with no dependencies beyond the standard library.

Deliberately not `gh` or PyGithub: this script has to run inside a training environment where
neither is installed, and a dependency that fails on the day of a cohort is worse than fifty
lines of urllib.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"
GRAPHQL = "https://api.github.com/graphql"


class GitHubError(RuntimeError):
    def __init__(self, status, message, url=""):
        super().__init__(f"HTTP {status} on {url}: {message}")
        self.status = status
        self.message = message


def token() -> str:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not tok:
        sys.exit(
            "No GITHUB_TOKEN in the environment.\n\n"
            "Create a fine-grained personal access token with these repository permissions:\n"
            "  Contents: read/write · Issues: read/write · Discussions: read/write\n"
            "  Pull requests: read/write · Administration: read/write (for labels + settings)\n"
            "and, if you want the board, the account permission: Projects: read/write\n\n"
            "  export GITHUB_TOKEN=github_pat_<your token>"
        )
    # A token ending in "..." is the placeholder from the docs pasted verbatim. Saying so
    # here is worth a great deal more than the "Bad credentials" GitHub would answer with.
    if tok.endswith("...") or tok in {"github_pat_...", "ghp_...", "<your token>"}:
        sys.exit(
            f"GITHUB_TOKEN is set to the placeholder {tok!r}, not a real token.\n\n"
            "Create one at https://github.com/settings/tokens?type=beta and export the\n"
            "actual value:\n\n"
            "  export GITHUB_TOKEN=github_pat_11ABC...   # the full string GitHub showed you"
        )
    return tok


def request(method: str, path: str, payload=None, accept="application/vnd.github+json",
            retries: int = 3):
    url = path if path.startswith("http") else f"{API}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token()}")
    req.add_header("Accept", accept)
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "nanorag-setup")

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                body = resp.read().decode()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode()
            try:
                message = json.loads(body).get("message", body)
            except Exception:
                message = body
            # Secondary rate limit / abuse detection: back off and retry.
            if exc.code in (403, 429) and attempt < retries - 1 and "rate limit" in message.lower():
                wait = 2 ** (attempt + 3)
                print(f"    rate limited, waiting {wait}s…")
                time.sleep(wait)
                continue
            raise GitHubError(exc.code, message, url) from None
        except urllib.error.URLError as exc:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise GitHubError(0, str(exc.reason), url) from None
    raise GitHubError(0, "exhausted retries", url)


def graphql(query: str, variables: dict | None = None):
    payload = {"query": query, "variables": variables or {}}
    out = request("POST", GRAPHQL, payload)
    if "errors" in out:
        raise GitHubError(200, json.dumps(out["errors"])[:500], GRAPHQL)
    return out["data"]


def ok(label: str, detail: str = ""):
    print(f"  \033[32m✓\033[0m {label}" + (f"  {detail}" if detail else ""))


def skip(label: str, detail: str = ""):
    print(f"  \033[90m·\033[0m {label}" + (f"  {detail}" if detail else ""))


def warn(label: str, detail: str = ""):
    print(f"  \033[33m!\033[0m {label}" + (f"  {detail}" if detail else ""))


def fail(label: str, detail: str = ""):
    print(f"  \033[31m✗\033[0m {label}" + (f"  {detail}" if detail else ""))
