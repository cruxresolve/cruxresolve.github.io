#!/usr/bin/env python3
"""Submit only changed public Crux Resolve URLs to IndexNow.

The script is intended for the post-deployment GitHub Actions validation job.
It derives affected public URLs from the Git diff, then sends one batch to the
IndexNow global endpoint. It intentionally avoids re-submitting the entire
sitemap for every deployment.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

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
    if path == "index.html":
        return SITE_ORIGIN
    if path == "404.html":
        return None
    if path.endswith(".html") and not path.startswith(("_", ".")):
        return urljoin(SITE_ORIGIN, path)
    if path == "llms.txt":
        return urljoin(SITE_ORIGIN, path)
    return None


def affected_urls(changes: list[tuple[str, str]], sitemap_urls: set[str]) -> list[str]:
    urls: set[str] = set()

    for status, path in changes:
        direct = direct_public_url(path)
        if direct:
            urls.add(direct)
            continue

        if path.startswith("_includes/ghosttune/"):
            urls.update(
                {
                    urljoin(SITE_ORIGIN, "ghosttune-app.html"),
                    urljoin(SITE_ORIGIN, "start.html"),
                }
            )
        elif path.startswith("_includes/ghostbridge/"):
            urls.add(urljoin(SITE_ORIGIN, "ghostbridge.html"))
        elif path.startswith("_includes/privacy/"):
            urls.add(urljoin(SITE_ORIGIN, "privacy.html"))
        elif path.startswith("_includes/terms/"):
            urls.add(urljoin(SITE_ORIGIN, "terms-of-sale.html"))
        elif path.startswith("_layouts/"):
            # A shared layout change modifies every canonical page.
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
