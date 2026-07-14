#!/usr/bin/env python3
"""Verify that GitHub Pages rendered and published the expected public pages."""

from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request

CHECKS = {
    "https://cruxresolve.com/": (
        "Tune your MicroSquirt",
        "No laptop. No cable.",
        "GhostBridge",
    ),
    "https://cruxresolve.com/ghosttune-app.html": (
        "Live-ECU testing is underway.",
        "MicroSquirt",
        "MS2/Extra 3.4.4",
    ),
    "https://cruxresolve.com/ghostbridge.html": (
        "Confirm the complete setup.",
        "97.95 × 77.01 × 22.55 mm",
        "Buy GhostBridge · $89",
    ),
    "https://cruxresolve.com/support.html": (
        "Direct product support.",
        "support@cruxresolve.com",
    ),
    "https://cruxresolve.com/privacy.html": (
        "Privacy Policy",
        "Formspree",
        "Stripe",
        "https://cruxresolve.com/privacy.html",
    ),
    "https://cruxresolve.com/terms-of-sale.html": (
        "Terms of Sale",
        "All sales are final.",
    ),
}

ATTEMPTS = 36
DELAY_SECONDS = 10


def fetch(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CruxResolve-Site-Check/1.0",
            "Accept": "text/html,application/xhtml+xml",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            raise RuntimeError(f"unexpected content type: {content_type}")
        return response.read().decode("utf-8", errors="replace")


def validate_page(url: str, expected: tuple[str, ...]) -> list[str]:
    html = fetch(url)
    failures: list[str] = []
    if "{%" in html or "{{" in html:
        failures.append("unrendered Liquid/Jekyll markup is present")
    for value in expected:
        if value not in html:
            failures.append(f"missing expected text: {value}")
    return failures


def main() -> int:
    last_failures: list[str] = []
    for attempt in range(1, ATTEMPTS + 1):
        failures: list[str] = []
        for url, expected in CHECKS.items():
            try:
                page_failures = validate_page(url, expected)
            except (OSError, RuntimeError, urllib.error.URLError) as error:
                failures.append(f"{url}: {error}")
                continue
            failures.extend(f"{url}: {failure}" for failure in page_failures)

        if not failures:
            print(f"Live deployment validation passed for {len(CHECKS)} pages.")
            return 0

        last_failures = failures
        print(f"Attempt {attempt}/{ATTEMPTS} did not pass:")
        for failure in failures:
            print(f"- {failure}")
        if attempt < ATTEMPTS:
            time.sleep(DELAY_SECONDS)

    print("Live deployment validation failed after all retries:")
    for failure in last_failures:
        print(f"- {failure}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
