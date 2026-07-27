#!/usr/bin/env python3
"""Discover Claude share links by searching `site:claude.ai/share/` and
append any new ones to links.txt.

Uses DuckDuckGo (free, no API key) to find publicly shared Claude chats.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse

LINKS_FILE = Path(__file__).parent / "links.txt"

# UUID pattern for Claude share links
UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
CLAUDE_URL_RE = re.compile(r"https?://claude\.ai/share/" + UUID_RE.pattern)


def discover_via_duckduckgo(max_results: int = 50) -> list[str]:
    """Search DuckDuckGo for `site:claude.ai/share/` and return found URLs."""
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            print("Installing ddgs...", file=sys.stderr)
            import subprocess
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "ddgs"]
            )
            from ddgs import DDGS

    found: set[str] = set()
    with DDGS() as ddgs:
        for i, result in enumerate(ddgs.text(
            "site:claude.ai/share/",
            max_results=max_results,
        )):
            url = result.get("href", "")
            if CLAUDE_URL_RE.match(url):
                found.add(url)
            # Also try to find UUIDs in the link or snippet
            for field in ("href", "link", "url", "snippet", "body", "title"):
                val = result.get(field, "")
                m = UUID_RE.search(val)
                if m:
                    found.add(f"https://claude.ai/share/{m.group(0)}")

    return sorted(found)


def discover_via_google(max_results: int = 30) -> list[str]:
    """Fallback: try to search Google (no API key needed via scraping).
    
    This is less reliable than DuckDuckGo and may get rate-limited.
    """
    import urllib.request
    import urllib.parse

    found: set[str] = set()
    query = urllib.parse.quote("site:claude.ai/share/")
    url = f"https://www.google.com/search?q={query}&num={max_results}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  Google search failed: {e}", file=sys.stderr)
        return []

    # Find claude.ai/share URLs in the HTML
    for m in CLAUDE_URL_RE.finditer(html):
        found.add(m.group(0))
    for m in UUID_RE.finditer(html):
        found.add(f"https://claude.ai/share/{m.group(0)}")

    return sorted(found)


def read_existing_links() -> set[str]:
    """Read existing links from links.txt, returning normalized UUIDs."""
    if not LINKS_FILE.exists():
        return set()
    existing: set[str] = set()
    for line in LINKS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = UUID_RE.search(line)
        if m:
            existing.add(m.group(0).lower())
    return existing


def append_links(new_urls: list[str]) -> int:
    """Append new discovered URLs to links.txt. Returns count of new links."""
    existing_uuids = read_existing_links()
    new_count = 0

    # Also check what's already in the file (full URLs)
    existing_text = LINKS_FILE.read_text(encoding="utf-8") if LINKS_FILE.exists() else ""

    with LINKS_FILE.open("a", encoding="utf-8") as f:
        for url in new_urls:
            m = UUID_RE.search(url)
            if not m:
                continue
            uuid = m.group(0).lower()
            if uuid in existing_uuids:
                continue
            if url in existing_text:
                continue
            f.write(url + "\n")
            existing_uuids.add(uuid)
            new_count += 1

    return new_count


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Discover Claude share links from search engines"
    )
    parser.add_argument(
        "--max", type=int, default=50,
        help="Maximum results to fetch (default: 50)"
    )
    parser.add_argument(
        "--engine", choices=["duckduckgo", "google", "auto"], default="auto",
        help="Search engine to use (default: auto = try duckduckgo first)"
    )
    args = parser.parse_args()

    print(f"🔍 Discovering Claude share links (max {args.max})...")

    urls: list[str] = []
    if args.engine in ("auto", "duckduckgo"):
        try:
            urls = discover_via_duckduckgo(args.max)
            if urls:
                print(f"  Found {len(urls)} URLs via DuckDuckGo")
            elif args.engine == "duckduckgo":
                print("  No results from DuckDuckGo", file=sys.stderr)
        except Exception as e:
            print(f"  DuckDuckGo failed: {e}", file=sys.stderr)
            if args.engine == "auto":
                print("  Falling back to Google...")
            else:
                return

    if not urls and args.engine in ("auto", "google",):
        urls = discover_via_google(args.max)
        if urls:
            print(f"  Found {len(urls)} URLs via Google")

    if not urls:
        print("  No links discovered.", file=sys.stderr)
        return

    new_count = append_links(urls)
    if new_count > 0:
        print(f"✅ Added {new_count} new link(s) to {LINKS_FILE.name}")
    else:
        print(f"  No new links — {LINKS_FILE.name} is already up to date.")

    existing = len(read_existing_links())
    print(f"  Total links tracked: {existing}")


if __name__ == "__main__":
    main()
