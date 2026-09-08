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
        "Connect legacy hardware to modern devices.",
        "Veteran-Owned Small Business",
        "GhostBridge v1.0 (GB-01)",
        "Looking for wireless RS232?",
        "What are you trying to connect?",
        "I have a device, but I am not sure the interface matches",
        "My old software still expects a COM port",
        "I need repeat deployments or application-specific behavior",
        "RS232 over WiFi guide",
        "Buy GhostBridge · $89",
        "From the technical library",
        "Connect RS232 Equipment Over WiFi",
        "/ghostbridge.html#compatibility-request",
        "/oem-serial-solutions.html",
        "/rs232-wifi.html",
        "/go/ghostbridge-checkout.html",
    ),
    "https://cruxresolve.com/rs232-wifi.html": (
        "Connect RS232 equipment over WiFi.",
        "Transparent serial transport.",
        "The market is much broader than automotive.",
        "Check the interface, not just the connector.",
        "Start from the problem you are trying to solve.",
        "No router. No cloud. No subscription.",
        "Current GhostBridge GB-01 interface",
        "/ghostbridge.html#compatibility-request",
        "/blog/connect-legacy-rs232-equipment-modern-computer.html",
        "/oem-serial-solutions.html",
        "/ghostbridge.html#specifications",
    ),
    "https://cruxresolve.com/oem-serial-solutions.html": (
        "Need a WiFi serial bridge for your product?",
        "More than a one-off adapter.",
        "Know what firmware can—and cannot—change.",
        "Describe the device and the deployment.",
        "GhostBridge OEM / Custom Firmware Inquiry",
        "GhostBridge OEM Custom Firmware Inquiry",
        "/ghostbridge.html",
        "/rs232-wifi.html",
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
        "Put RS232 on WiFi.",
        "A transparent local RS232 bridge.",
        "Know the interface before you connect it.",
        "Will GhostBridge work with my device?",
        "Tell us what you want to connect.",
        "GhostBridge Compatibility Request",
        "GhostBridge Stock Updates",
        "Standard 3-wire RS232",
        "Buy GhostBridge · $89",
        "+$8 U.S. shipping",
        "Using GhostBridge with GhostTune?",
        "/oem-serial-solutions.html",
        "/rs232-wifi.html",
        "/go/ghosttune.html",
        "/go/ghostbridge-checkout.html",
    ),
    "https://cruxresolve.com/blog/": (
        "Crux Resolve technical library",
        "Practical guides for serial connectivity and mobile ECU tuning.",
        "How to Connect Legacy RS232 Equipment to a Modern Computer",
        "TCP to RS232 Explained: What a Serial Device Server Does",
        "3-Wire RS232 Explained: TX, RX, and Ground",
        "RS232 DTE vs DCE and Null-Modem Cables Explained",
        "Can You Tune a Car From Your Phone? What Mobile ECU Tuning Can—and Can’t—Do",
        "September 8, 2026",
    ),
    "https://cruxresolve.com/blog/connect-legacy-rs232-equipment-modern-computer.html": (
        "How to connect legacy RS232 equipment to a modern computer",
        "Three common ways to bridge the gap",
        "Step 1: verify the electrical interface",
        "Where GhostBridge GB-01 fits",
        "When WiFi is better than USB serial",
        "/ghostbridge.html#compatibility-request",
    ),
    "https://cruxresolve.com/blog/tcp-to-rs232-serial-device-server.html": (
        "TCP to RS232 explained: what a serial device server does",
        "What “transparent” means",
        "TCP server versus TCP client",
        "What about old software that only opens COM ports?",
        "Where GhostBridge fits",
        "/rs232-wifi.html",
    ),
    "https://cruxresolve.com/blog/3-wire-rs232-tx-rx-ground.html": (
        "3-wire RS232 explained: TX, RX, and ground",
        "The three signals",
        "What 3-wire RS232 leaves out",
        "DB9 does not automatically mean standard 3-wire RS232",
        "GhostBridge GB-01 as a 3-wire RS232 bridge",
        "/ghostbridge.html#compatibility-request",
    ),
    "https://cruxresolve.com/blog/rs232-dte-dce-null-modem.html": (
        "RS232 DTE vs DCE and null-modem cables explained",
        "What DTE and DCE mean",
        "What a null-modem cable does",
        "GhostBridge GB-01 orientation",
        "What if the device uses RTS/CTS?",
        "/ghostbridge.html#compatibility-request",
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
        "Direct product and compatibility support.",
        "Have an RS232 device?",
        "OEM and custom firmware",
        "Can GhostBridge be used without GhostTune?",
        "Do you offer custom GhostBridge firmware?",
        "/ghostbridge.html#compatibility-request",
        "/oem-serial-solutions.html",
        "support@cruxresolve.com",
    ),
    "https://cruxresolve.com/privacy.html": (
        "Privacy Policy",
        "Effective September 8, 2026",
        "Version 5.4",
        "OEM or custom-firmware project inquiries",
        "standard UTM campaign parameters",
        "traffic-source attribution for that submitted request",
        "support@cruxresolve.com",
        "Formspree",
        "GhostBridge checkout is provided by Stripe.",
        "https://cruxresolve.com/privacy.html",
    ),
    "https://cruxresolve.com/terms-of-sale.html": (
        "Terms of Sale",
        "Effective September 8, 2026",
        "All sales are final.",
        "WiFi-to-RS232 TCP bridge",
        "standard 3-wire RS232 applications",
        "pin 2 RX into GhostBridge",
    ),
}

FORBIDDEN = {
    "https://cruxresolve.com/privacy.html": (
        "privacy@cruxresolve.com",
        "Version 3.0",
        "Version 5.1",
        "Version 5.2",
        "Version 5.3",
        "June 23, 2026",
        "Effective June 28, 2026",
        "Effective August 8, 2026",
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
        "optimized and verified as the wireless hardware companion for GhostTune",
    ),
    SITE_ROOT: (
        "GhostBridge v2.0",
        "GB-02",
        "development progress",
        "Engineering practical connections between vehicles, hardware, and software.",
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
