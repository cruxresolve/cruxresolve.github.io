#!/usr/bin/env python3
"""Verify that GitHub Pages rendered and published the expected public pages and images."""

from __future__ import annotations

from html.parser import HTMLParser
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SITE_ROOT = "https://cruxresolve.com/"

CHECKS = {
    SITE_ROOT: (
        "Engineering practical connections between vehicles, hardware, and software.",
        "Veteran-Owned Small Business",
        "GhostBridge v1.0 (GB-01)",
        "Already know what you need?",
        "Get GhostTune · App Store",
        "Buy GhostBridge · $89",
        "From the technical library",
        "Can You Tune a Car From Your Phone?",
        "/go/ghosttune.html",
        "/go/ghostbridge-checkout.html",
    ),
    "https://cruxresolve.com/ghosttune-app.html": (
        "Production validation complete",
        "Get GhostTune on the App Store",
        "Can I tune a MicroSquirt from an iPhone or iPad?",
        "MicroSquirt",
        "MS2/Extra 3.4.4",
        "Pair GhostTune with GhostBridge.",
        "Need the WiFi bridge? See GhostBridge",
        "/go/ghosttune.html",
    ),
    "https://cruxresolve.com/ghostbridge.html": (
        "GhostBridge GB-01",
        "RS232-to-WiFi TCP bridge",
        "Confirm the complete setup.",
        "Built for practical use",
        "Buy GhostBridge · $89",
        "+$8 U.S. shipping",
        "Pair GhostBridge with GhostTune.",
        "/go/ghosttune.html",
        "/go/ghostbridge-checkout.html",
    ),
    "https://cruxresolve.com/blog/": (
        "Crux Resolve technical library",
        "Can You Tune a Car From Your Phone? What Mobile ECU Tuning Can—and Can’t—Do",
        "September 6, 2026",
        "MicroSquirt WiFi Troubleshooting",
    ),
    "https://cruxresolve.com/blog/can-you-tune-a-car-from-your-phone.html": (
        "Can You Tune a Car From Your Phone?",
        "The four pieces that have to work together",
        "What a capable mobile tuning app can do",
        "Where GhostTune fits",
        "Where GhostBridge fits",
        "/go/ghosttune.html",
        "View GhostBridge · $89 + $8 shipping",
    ),
    "https://cruxresolve.com/blog/how-to-tune-microsquirt-from-iphone.html": (
        "How to Tune a MicroSquirt From an iPhone",
        "How the wireless connection works",
        "Step 5: Make supported calibration changes",
        "Related guides",
    ),
    "https://cruxresolve.com/go/ghosttune.html": (
        "Opening GhostTune on the App Store",
        "https://apps.apple.com/us/app/id6778061607",
    ),
    "https://cruxresolve.com/go/ghostbridge-checkout.html": (
        "Opening secure GhostBridge checkout",
        "https://buy.stripe.com/8x28wR9Za8n81oxcDe1VK00",
    ),
    "https://cruxresolve.com/support.html": (
        "Direct product support.",
        "Can GhostBridge be used without GhostTune?",
        "support@cruxresolve.com",
    ),
    "https://cruxresolve.com/privacy.html": (
        "Privacy Policy",
        "Effective August 8, 2026",
        "Version 5.2",
        "support@cruxresolve.com",
        "Formspree",
        "GhostBridge checkout is provided by Stripe.",
        "https://cruxresolve.com/privacy.html",
    ),
    "https://cruxresolve.com/terms-of-sale.html": (
        "Terms of Sale",
        "All sales are final.",
        "RS232-to-WiFi TCP bridge",
    ),
}

FORBIDDEN = {
    "https://cruxresolve.com/privacy.html": (
        "privacy@cruxresolve.com",
        "Version 3.0",
        "Version 5.1",
        "June 23, 2026",
        "Effective June 28, 2026",
        "requires users to be at least 18 years old",
    ),
    "https://cruxresolve.com/ghosttune-app.html": (
        "Live-ECU testing is underway.",
        "Live-ECU testing in progress",
        "Join release updates",
        "Additional ECU platforms are under development",
    ),
    "https://cruxresolve.com/ghostbridge.html": (
        "GhostBridge v2.0",
        "GB-02",
        "Next generation",
        "Planned GB-02",
    ),
    SITE_ROOT: (
        "GhostBridge v2.0",
        "GB-02",
        "development progress",
    ),
}

ATTEMPTS = 36
DELAY_SECONDS = 10
MIN_IMAGE_BYTES = 128


class ImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.sources: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return
        values = dict(attrs)
        src = values.get("src")
        if src:
            self.sources.add(src)


def request(url: str, accept: str):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CruxResolve-Site-Check/1.1",
            "Accept": accept,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    return urllib.request.urlopen(req, timeout=20)


def fetch_html(url: str) -> str:
    with request(url, "text/html,application/xhtml+xml") as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            raise RuntimeError(f"unexpected content type: {content_type}")
        return response.read().decode("utf-8", errors="replace")


def fetch_image(url: str) -> None:
    with request(url, "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8") as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if not content_type.startswith("image/"):
            raise RuntimeError(f"unexpected content type: {content_type or 'missing'}")
        data = response.read()
        if len(data) < MIN_IMAGE_BYTES:
            raise RuntimeError(f"image payload too small: {len(data)} bytes")


def same_site_image_urls(page_url: str, html: str) -> set[str]:
    parser = ImageParser()
    parser.feed(html)
    images: set[str] = set()
    site_host = urllib.parse.urlparse(SITE_ROOT).netloc

    for src in parser.sources:
        if src.startswith(("data:", "blob:")):
            continue
        absolute = urllib.parse.urljoin(page_url, src)
        parsed = urllib.parse.urlparse(absolute)
        if parsed.scheme in {"http", "https"} and parsed.netloc == site_host:
            images.add(absolute)
    return images


def validate_page(url: str, expected: tuple[str, ...]) -> tuple[list[str], set[str]]:
    html = fetch_html(url)
    failures: list[str] = []
    if "{%" in html or "{{" in html:
        failures.append("unrendered Liquid/Jekyll markup is present")
    for value in expected:
        if value not in html:
            failures.append(f"missing expected text: {value}")
    for value in FORBIDDEN.get(url, ()):
        if value in html:
            failures.append(f"forbidden stale text is present: {value}")
    return failures, same_site_image_urls(url, html)


def main() -> int:
    last_failures: list[str] = []
    for attempt in range(1, ATTEMPTS + 1):
        failures: list[str] = []
        image_urls: set[str] = set()

        for url, expected in CHECKS.items():
            try:
                page_failures, page_images = validate_page(url, expected)
            except (OSError, RuntimeError, urllib.error.URLError) as error:
                failures.append(f"{url}: {error}")
                continue
            failures.extend(f"{url}: {failure}" for failure in page_failures)
            image_urls.update(page_images)

        if not failures:
            for image_url in sorted(image_urls):
                try:
                    fetch_image(image_url)
                except (OSError, RuntimeError, urllib.error.URLError) as error:
                    failures.append(f"{image_url}: image check failed: {error}")

        if not failures:
            print(
                f"Live deployment validation passed for {len(CHECKS)} pages "
                f"and {len(image_urls)} referenced images."
            )
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
