#!/usr/bin/env python3
"""Scrape OWASP Web Security Testing Guide (latest) into local markdown files."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

BASE_URL = "https://owasp.org/www-project-web-security-testing-guide/latest/"
ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "security" / "owasp-wstg"
MANIFEST_PATH = OUT_DIR / "manifest.json"
INDEX_PATH = OUT_DIR / "README.md"
REQUEST_DELAY_SEC = 0.35


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if not href or href.startswith("#"):
            return
        if href.startswith("/www-project-web-security-testing-guide/latest/"):
            self.links.add(href.split("#", 1)[0])


def curl_get(url: str) -> str:
    result = subprocess.run(
        ["curl", "-sS", "-L", "--retry", "3", "--retry-delay", "2", url],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def normalize_page_path(page_path: str) -> str:
    path = page_path.split("#", 1)[0].rstrip("/")
    if path.endswith("/README"):
        path = path[: -len("/README")]
    if not path.endswith("/latest"):
        path = path + "/"
    return path.replace("//", "/").replace("/latest//", "/latest/")


def discover_pages() -> list[str]:
    pages: set[str] = {normalize_page_path("/www-project-web-security-testing-guide/latest/")}
    seeds = [
        BASE_URL,
        urljoin(BASE_URL, "4-Web_Application_Security_Testing/"),
        urljoin(BASE_URL, "2-Introduction/README"),
        urljoin(BASE_URL, "3-The_OWASP_Testing_Framework/0-The_Web_Security_Testing_Framework"),
        urljoin(BASE_URL, "5-Reporting/README"),
        urljoin(BASE_URL, "6-Appendix/F-Leveraging_Dev_Tools"),
    ]
    for seed in seeds:
        collector = LinkCollector()
        collector.feed(curl_get(seed))
        pages.update(normalize_page_path(link) for link in collector.links)
    return sorted(pages)


def extract_main_html(html: str) -> str:
    # Page body starts at the breadcrumb; earlier <main> wrappers repeat site chrome.
    match = re.search(
        r'<div class="breadcrumb"[^>]*>.*?</div>\s*(.*)</main>',
        html,
        re.S | re.I,
    )
    if not match:
        match = re.search(r"<main[^>]*>(.*)</main>", html, re.S | re.I)
    if not match:
        raise ValueError("No page content found")
    content = match.group(1)
    content = re.sub(r"<nav[^>]*>.*?</nav>", "", content, flags=re.S | re.I)
    content = re.sub(r"<aside[^>]*>.*?</aside>", "", content, flags=re.S | re.I)
    content = re.sub(r"<div class=\"contributors\"[^>]*>.*?</div>", "", content, flags=re.S | re.I)
    return content.strip()


def html_to_markdown(html_fragment: str, page_url: str) -> str:
    wrapped = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<base href='{page_url}'></head><body>{html_fragment}</body></html>"
    )
    result = subprocess.run(
        [
            "pandoc",
            "-f",
            "html",
            "-t",
            "gfm",
            "--wrap=none",
            "--markdown-headings=atx",
        ],
        input=wrapped,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def path_to_output(page_path: str) -> Path:
    rel = page_path.removeprefix("/www-project-web-security-testing-guide/latest/").strip("/")
    if not rel:
        return OUT_DIR / "index.md"
    if rel.endswith("/README"):
        rel = rel[: -len("/README")]
    parts = rel.split("/")
    filename = parts[-1]
    if filename and not rel.endswith("/"):
        # Keep dotted section ids like 05.1-Testing_for_Oracle as filenames.
        parts[-1] = f"{filename}.md"
        return OUT_DIR.joinpath(*parts)
    return OUT_DIR.joinpath(*parts) / "README.md"


def page_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def build_index(manifest: list[dict[str, str]]) -> str:
    lines = [
        "# OWASP Web Security Testing Guide (Latest)",
        "",
        "Offline mirror scraped from "
        "[OWASP WSTG](https://owasp.org/www-project-web-security-testing-guide/latest/).",
        "",
        f"**Pages:** {len(manifest)}",
        "",
        "## Table of Contents",
        "",
    ]
    for entry in manifest:
        lines.append(f"- [{entry['title']}]({entry['file']})")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pages = discover_pages()
    print(f"Discovered {len(pages)} pages", file=sys.stderr)

    manifest: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []

    for idx, page_path in enumerate(pages, start=1):
        page_url = urljoin("https://owasp.org", page_path)
        out_file = path_to_output(page_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        rel_file = out_file.relative_to(OUT_DIR).as_posix()

        try:
            html = curl_get(page_url)
            main_html = extract_main_html(html)
            markdown = html_to_markdown(main_html, page_url)
            if not markdown:
                raise ValueError("Empty markdown output")

            header = [
                f"<!-- source: {page_url} -->",
                f"<!-- scraped_at: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} -->",
                "",
            ]
            out_file.write_text("\n".join(header) + markdown + "\n", encoding="utf-8")
            title = page_title(markdown, out_file.stem)
            manifest.append({"title": title, "file": rel_file, "source_url": page_url})
            print(f"[{idx}/{len(pages)}] OK {rel_file}", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 - collect all page failures
            failures.append({"url": page_url, "error": str(exc)})
            print(f"[{idx}/{len(pages)}] FAIL {page_url}: {exc}", file=sys.stderr)

        time.sleep(REQUEST_DELAY_SEC)

    manifest.sort(key=lambda item: item["file"])
    deduped_manifest: list[dict[str, str]] = []
    seen_files: set[str] = set()
    for entry in manifest:
        if entry["file"] in seen_files:
            continue
        seen_files.add(entry["file"])
        deduped_manifest.append(entry)

    MANIFEST_PATH.write_text(json.dumps(deduped_manifest, indent=2), encoding="utf-8")
    INDEX_PATH.write_text(build_index(deduped_manifest), encoding="utf-8")

    summary = {
        "pages_discovered": len(pages),
        "pages_saved": len(manifest),
        "failures": failures,
        "output_dir": str(OUT_DIR),
    }
    (OUT_DIR / "scrape-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
