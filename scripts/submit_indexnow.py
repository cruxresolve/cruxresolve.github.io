#!/usr/bin/env python3
"""Submit changed public Crux Resolve URLs to IndexNow.

The script runs after deployment. It derives affected public URLs from the Git
diff, follows Jekyll include dependencies to the indexable pages that actually
use them, and sends one batch to the IndexNow global endpoint.

Direct edits to legacy/noindex HTML pages may still be submitted so search
engines can discover a redirect, noindex directive, or deletion. Shared include
changes, however, fan out only to canonical URLs that are present in the
sitemap. This prevents a normal product/include edit from repeatedly announcing
retired or intentionally noindex pages.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SITE_ORIGIN = "https://cruxresolve.com/"
SITE_HOST = "cruxresolve.com"
DEFAULT_ENDPOINT = "https://api.indexnow.org/indexnow"
DEFAULT_KEY_FILE = "a30252b4152841dbbd7ec13fe4e10dd2.txt"


def load_sitemap_urls(path: Path) -> set[str]:
    if not path.exists():
        return set()
    root = ET.parse(path).getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return {
        loc.text.strip()
        for loc in root.findall("sm:url/sm:loc", ns)
        if loc.text and loc.text.strip().startswith(SITE_ORIGIN)
    }


def changed_paths(base_sha: str, head_sha: str) -> list[tuple[str, str]]:
    if not base_sha or set(base_sha) == {"0"}:
        base_sha = f"{head_sha}^"
    result = subprocess.run(
        ["git", "diff", "--name-status", "--find-renames", base_sha, head_sha],
        check=True,
        text=True,
        capture_output=True,
    )
    changes: list[tuple[str, str]] = []
    for raw in result.stdout.splitlines():
        if not raw.strip():
            continue
        fields = raw.split("\t")
        status = fields[0]
        # For renames, notify both the old and new public URL when applicable.
        if status.startswith("R") and len(fields) >= 3:
            changes.append(("D", fields[1]))
            changes.append(("A", fields[2]))
        elif len(fields) >= 2:
            changes.append((status[0], fields[1]))
    return changes


def direct_public_url(path: str) -> str | None:
    """Return the browser-facing URL for a directly changed public HTML file."""
    if path == "index.html":
        return SITE_ORIGIN
    if path in {"404.html"} or path.startswith(("_", ".", "go/")):
        return None
    if path == "licenses/index.html":
        return urljoin(SITE_ORIGIN, "licenses")
    if path.endswith("/index.html"):
        return urljoin(SITE_ORIGIN, path[: -len("index.html")])
    if path.endswith(".html"):
        return urljoin(SITE_ORIGIN, path)
    return None


def pages_using_include(include_path: str, sitemap_urls: set[str]) -> set[str]:
    """Resolve a changed include to all indexable public pages that depend on it."""
    affected: set[str] = set()
    pending = [include_path]
    seen: set[str] = set()

    html_files = [
        path
        for path in ROOT.rglob("*.html")
        if ".git" not in path.parts and "_site" not in path.parts
    ]

    while pending:
        include_name = pending.pop()
        if include_name in seen:
            continue
        seen.add(include_name)
        pattern = re.compile(r"{%\s*include\s+" + re.escape(include_name) + r"\s*%}")

        for candidate in html_files:
            try:
                text = candidate.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if not pattern.search(text):
                continue

            relative = candidate.relative_to(ROOT).as_posix()
            if relative.startswith("_includes/"):
                pending.append(relative[len("_includes/") :])
                continue

            public_url = direct_public_url(relative)
            if public_url and public_url in sitemap_urls:
                affected.add(public_url)

    return affected


def affected_urls(changes: list[tuple[str, str]], sitemap_urls: set[str]) -> list[str]:
    urls: set[str] = set()

    for _status, path in changes:
        direct = direct_public_url(path)
        if direct:
            # Direct changes are intentionally allowed even when a page is not in
            # the sitemap. This lets IndexNow discover a new noindex directive,
            # redirect, or deletion on a legacy URL such as /start.html.
            urls.add(direct)
            continue

        if path.startswith("_includes/"):
            include_name = path[len("_includes/") :]
            urls.update(pages_using_include(include_name, sitemap_urls))
        elif path.startswith("_layouts/"):
            # A shared layout change modifies every canonical, indexable page.
            urls.update(sitemap_urls)

    return sorted(urls)


def submit(urls: list[str], key_file: Path, endpoint: str) -> int:
    if not urls:
        print("IndexNow: no changed public URLs to submit.")
        return 0

    key = key_file.read_text(encoding="utf-8").strip()
    expected_key = key_file.stem
    if key != expected_key:
        raise RuntimeError(
            f"IndexNow key file content does not match its filename: {key_file}"
        )

    key_location = urljoin(SITE_ORIGIN, key_file.name)
    payload = {
        "host": SITE_HOST,
        "key": key,
        "keyLocation": key_location,
        "urlList": urls,
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )

    print(f"IndexNow: submitting {len(urls)} changed URL(s):")
    for url in urls:
        print(f"  {url}")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            code = response.getcode()
            response_body = response.read().decode("utf-8", errors="replace").strip()
    except urllib.error.HTTPError as exc:
        code = exc.code
        response_body = exc.read().decode("utf-8", errors="replace").strip()

    if response_body:
        print(f"IndexNow response body: {response_body}")
    print(f"IndexNow HTTP status: {code}")

    # 200 = accepted; 202 = received while key validation is pending.
    if code not in (200, 202):
        raise RuntimeError(f"IndexNow submission failed with HTTP {code}")
    return 0


def main() -> int:
    base_sha = os.environ.get("BASE_SHA", "").strip()
    head_sha = os.environ.get("HEAD_SHA", "HEAD").strip() or "HEAD"
    sitemap_path = Path(os.environ.get("SITEMAP_PATH", "sitemap.xml"))
    key_file = Path(os.environ.get("INDEXNOW_KEY_FILE", DEFAULT_KEY_FILE))
    endpoint = os.environ.get("INDEXNOW_ENDPOINT", DEFAULT_ENDPOINT)

    sitemap_urls = load_sitemap_urls(sitemap_path)
    changes = changed_paths(base_sha, head_sha)
    urls = affected_urls(changes, sitemap_urls)
    return submit(urls, key_file, endpoint)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - CI should fail loudly with context.
        print(f"IndexNow error: {exc}", file=sys.stderr)
        raise SystemExit(1)
