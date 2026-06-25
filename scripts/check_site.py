#!/usr/bin/env python3
"""Validate the static/Jekyll website without external Python packages."""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PUBLIC_FILES = {
    "index.html",
    "ghosttune-app.html",
    "ghostbridge.html",
    "ghosttune.html",
    "support.html",
    "privacy.html",
    "terms-of-sale.html",
    "404.html",
    "robots.txt",
    "sitemap.xml",
}
INCLUDE_RE = re.compile(r"{%\s*include\s+([^\s%]+)\s*%}")
VARIABLE_RE = re.compile(r"{{\s*([^}]+?)\s*}}")
IF_RE = re.compile(r"{%\s*if\s+.*?%}(.*?){%\s*endif\s*%}", re.DOTALL)


def read_front_matter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    marker = text.find("\n---\n", 4)
    if marker < 0:
        raise ValueError(f"{path}: unterminated front matter")
    values: dict[str, str] = {}
    for raw_line in text[4:marker].splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if ":" not in raw_line:
            raise ValueError(f"{path}: malformed front matter line: {raw_line}")
        key, value = raw_line.split(":", 1)
        values[key.strip()] = value.strip().strip('"\'')
    return values, text[marker + 5 :]


def expand_includes(text: str, owner: Path) -> str:
    for _ in range(20):
        match = INCLUDE_RE.search(text)
        if not match:
            return text
        include_path = ROOT / "_includes" / match.group(1)
        if not include_path.is_file():
            raise ValueError(f"{owner}: missing include {match.group(1)}")
        text = text[: match.start()] + include_path.read_text(encoding="utf-8") + text[match.end() :]
    raise ValueError(f"{owner}: include expansion exceeded safe recursion limit")


def render_page(path: Path) -> tuple[dict[str, str], str]:
    page, body = read_front_matter(path)
    body = expand_includes(body, path)
    layout_name = page.get("layout")
    if layout_name:
        layout_path = ROOT / "_layouts" / f"{layout_name}.html"
        if not layout_path.is_file():
            raise ValueError(f"{path}: missing layout {layout_name}")
        output = layout_path.read_text(encoding="utf-8").replace("{{ content }}", body)
    else:
        output = body
    output = IF_RE.sub(lambda match: match.group(1), output)

    def replace_variable(match: re.Match[str]) -> str:
        expression = match.group(1).strip()
        parts = [part.strip() for part in expression.split("|")]
        value = ""
        if parts[0].startswith("page."):
            value = page.get(parts[0][5:], "")
        for modifier in parts[1:]:
            if modifier.startswith("default:") and not value:
                value = modifier.split(":", 1)[1].strip().strip('"\'')
        return value

    return page, VARIABLE_RE.sub(replace_variable, output)


class DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.links: list[str] = []
        self.images_without_alt: list[str] = []
        self.controls: list[str] = []
        self.main_count = 0
        self.h1_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"] or "")
        if tag == "a" and values.get("href"):
            self.links.append(values["href"] or "")
        if tag == "img" and "alt" not in values:
            self.images_without_alt.append(values.get("src") or "unknown image")
        if values.get("aria-controls"):
            self.controls.append(values["aria-controls"] or "")
        if tag == "main":
            self.main_count += 1
        if tag == "h1":
            self.h1_count += 1


def public_html_files() -> list[Path]:
    candidates = list(ROOT.glob("*.html")) + list((ROOT / "blog").glob("*.html"))
    pages: list[Path] = []
    for path in candidates:
        if not path.is_file():
            continue
        # Files such as Google Search Console verification tokens are intentionally
        # plain text/HTML and are not user-facing pages with landmarks or metadata.
        if path.read_text(encoding="utf-8").startswith("---\n"):
            pages.append(path)
    return sorted(pages)


def public_target(href: str, source: Path) -> tuple[Path | None, str]:
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or href.startswith(("mailto:", "tel:")):
        return None, ""
    path_text = parsed.path
    fragment = parsed.fragment
    if not path_text:
        return source, fragment
    if path_text == "/":
        return ROOT / "index.html", fragment
    if path_text.startswith("/"):
        relative = path_text.lstrip("/")
        target = ROOT / relative
    else:
        target = source.parent / path_text
    if path_text.endswith("/"):
        target = target / "index.html"
    return target.resolve(), fragment


def main() -> int:
    failures: list[str] = []
    for required in sorted(REQUIRED_PUBLIC_FILES):
        if not (ROOT / required).is_file():
            failures.append(f"missing required public file: {required}")

    rendered: dict[Path, tuple[dict[str, str], str, DocumentParser]] = {}
    for path in public_html_files():
        try:
            front_matter, html = render_page(path)
        except Exception as error:  # noqa: BLE001 - report all validation failures together
            failures.append(str(error))
            continue
        parser = DocumentParser()
        parser.feed(html)
        rendered[path.resolve()] = (front_matter, html, parser)

        relative = path.relative_to(ROOT)
        if parser.main_count != 1:
            failures.append(f"{relative}: expected one main landmark, found {parser.main_count}")
        if parser.h1_count != 1:
            failures.append(f"{relative}: expected one h1, found {parser.h1_count}")
        duplicate_ids = sorted({value for value in parser.ids if parser.ids.count(value) > 1})
        if duplicate_ids:
            failures.append(f"{relative}: duplicate IDs: {', '.join(duplicate_ids)}")
        if parser.images_without_alt:
            failures.append(f"{relative}: images missing alt: {', '.join(parser.images_without_alt)}")
        missing_controls = sorted(set(parser.controls) - set(parser.ids))
        if missing_controls:
            failures.append(f"{relative}: aria-controls targets missing: {', '.join(missing_controls)}")
        if not front_matter.get("canonical"):
            failures.append(f"{relative}: canonical URL missing from front matter")

    for source, (_, _, parser) in rendered.items():
        for href in parser.links:
            target, fragment = public_target(href, source)
            if target is None:
                continue
            try:
                target.relative_to(ROOT)
            except ValueError:
                failures.append(f"{source.relative_to(ROOT)}: link escapes repository: {href}")
                continue
            if not target.exists():
                failures.append(f"{source.relative_to(ROOT)}: broken internal link: {href}")
                continue
            if fragment and target in rendered:
                target_ids = set(rendered[target][2].ids)
                if fragment not in target_ids:
                    failures.append(
                        f"{source.relative_to(ROOT)}: missing fragment #{fragment} in {target.relative_to(ROOT)}"
                    )

    privacy, _ = read_front_matter(ROOT / "privacy.html")
    if privacy.get("canonical") != "https://cruxresolve.com/privacy.html":
        failures.append("privacy.html: App Store canonical URL must remain unchanged")

    if failures:
        print("Site validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"Site validation passed for {len(rendered)} rendered HTML pages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
