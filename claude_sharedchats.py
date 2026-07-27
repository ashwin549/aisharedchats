#!/usr/bin/env python3
"""Export claude.ai share links to markdown transcripts."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    sys.exit("error: curl_cffi is required. Install it with: pip install curl_cffi")


_firebase_initialized = False

def _upload_to_firestore(uuid: str, title: str, markdown: str, author: str,
                         created: str, message_count: int, source_url: str,
                         collection: str = "chats") -> bool:
    global _firebase_initialized
    if not _firebase_initialized:
        key_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY")
        if not key_path:
            return False
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore
        except ImportError:
            print("warning: firebase-admin not installed", file=sys.stderr)
            return False
        try:
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)
            globals()["_firestore_client"] = firestore.client()
            _firebase_initialized = True
        except Exception as exc:
            print(f"warning: Firebase init failed: {exc}", file=sys.stderr)
            return False

    db = globals().get("_firestore_client")
    if db is None:
        return False

    doc_ref = db.collection(collection).document(uuid)
    try:
        doc_ref.set({
            "uuid": uuid,
            "title": title,
            "markdown": markdown,
            "author": author,
            "created": created,
            "messageCount": message_count,
            "sourceUrl": source_url,
            "exportedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        return True
    except Exception as exc:
        print(f"warning: Firestore upload failed for {uuid}: {exc}", file=sys.stderr)
        return False


API_URL = "https://claude.ai/api/chat_snapshots/{uuid}"
SHARE_URL = "https://claude.ai/share/{uuid}"
UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
IMPERSONATE = "chrome"
TIMEOUT = 30
MAX_SLUG = 80
MANIFEST_NAME = ".claude-share-export.json"


class ExportError(Exception):
    """A single link failed; the batch continues."""


def extract_uuid(raw: str) -> str:
    match = UUID_RE.search(raw)
    if not match:
        raise ExportError("no UUID found")
    return match.group(0).lower()


def fetch_snapshot(uuid: str) -> dict:
    try:
        response = cffi_requests.get(
            API_URL.format(uuid=uuid),
            impersonate=IMPERSONATE,
            timeout=TIMEOUT,
            headers={"Accept": "*/*", "Referer": SHARE_URL.format(uuid=uuid)},
        )
    except Exception as exc:
        raise ExportError(f"network error: {type(exc).__name__}: {exc}") from exc

    if response.status_code == 404:
        raise ExportError("share not found (deleted or never public)")
    if response.status_code == 403:
        detail = ""
        try:
            error = response.json().get("error")
            detail = (error or {}).get("message") or ""
        except Exception:
            pass
        if detail:
            raise ExportError(f"not public: {detail}")
        raise ExportError("blocked by Cloudflare")
    if response.status_code != 200:
        raise ExportError(f"HTTP {response.status_code}")

    try:
        payload = response.json()
    except Exception as exc:
        raise ExportError("response was not JSON") from exc

    if not isinstance(payload, dict):
        raise ExportError("unexpected JSON shape")
    return payload


def _blocks_to_text(blocks: list, include_thinking: bool) -> str:
    parts: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind == "text":
            text = (block.get("text") or "").strip()
            if text:
                parts.append(text)
        elif kind == "thinking":
            if not include_thinking:
                continue
            thinking = (block.get("thinking") or block.get("text") or "").strip()
            if thinking:
                quoted = "\n".join(f"> {line}" for line in thinking.splitlines())
                parts.append(f"> **Thinking**\n>\n{quoted}")
        elif kind in ("tool_use", "server_tool_use"):
            parts.append(f"_[Tool: {block.get('name') or 'unknown'}]_")
        elif kind in ("tool_result", "web_search_tool_result"):
            parts.append("_[Tool result (content not available via share API)]_")
        else:
            parts.append(f"_[{kind or 'unknown'} block]_")
    return "\n\n".join(parts)


def message_body(message: dict, include_thinking: bool) -> str:
    content = message.get("content")
    if isinstance(content, list) and content:
        body = _blocks_to_text(content, include_thinking)
        if body.strip():
            return body
    return (message.get("text") or "").strip()


def _attachment_names(message: dict) -> list[str]:
    names = []
    for item in (message.get("attachments") or []) + (message.get("files") or []):
        if not isinstance(item, dict):
            continue
        name = item.get("file_name") or item.get("name")
        if name:
            names.append(str(name))
    return names


def render_markdown(snapshot: dict, uuid: str, include_thinking: bool) -> tuple[str, int]:
    title = (snapshot.get("snapshot_name") or "").strip() or "Untitled"
    creator = snapshot.get("creator") or {}
    author = (snapshot.get("created_by") or "").strip() or (creator.get("full_name") or "").strip()
    created = (snapshot.get("created_at") or "")[:10]
    messages = sorted(
        (m for m in (snapshot.get("chat_messages") or []) if isinstance(m, dict)),
        key=lambda m: m.get("index") or 0,
    )

    lines = [f"# {title}", ""]
    lines.append(f"- Source: {SHARE_URL.format(uuid=uuid)}")
    if author:
        lines.append(f"- Author: {author}")
    if created:
        lines.append(f"- Created: {created}")
    lines.append(f"- Messages: {len(messages)}")

    if not messages:
        lines += ["", "---", "", "_This snapshot contains no messages._"]
        return "\n".join(lines) + "\n", 0

    for message in messages:
        sender = (message.get("sender") or "").lower()
        label = {"human": "Human", "assistant": "Assistant"}.get(sender, sender.title() or "Unknown")
        lines += ["", "---", "", f"## {label}", ""]
        body = message_body(message, include_thinking)
        lines.append(body if body else "_[empty message]_")
        names = _attachment_names(message)
        if names:
            lines += ["", f"_Attachments: {', '.join(names)}_"]

    return "\n".join(lines) + "\n", len(messages)


def slugify(text: str, fallback: str) -> str:
    normalised = unicodedata.normalize("NFC", text or "")
    kept = []
    for char in normalised:
        if char.isalnum():
            kept.append(char)
        elif char in " -_.":
            kept.append("-")
    slug = re.sub(r"-+", "-", "".join(kept)).strip("-")
    return slug[:MAX_SLUG].strip("-") or fallback


def unique_path(directory: Path, slug: str) -> Path:
    candidate = directory / f"{slug}.md"
    counter = 2
    while candidate.exists():
        candidate = directory / f"{slug}-{counter}.md"
        counter += 1
    return candidate


def read_link_file(path: Path) -> list[str]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ExportError(f"cannot read {path}: {exc}") from exc
    links = []
    for line in raw.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            links.append(line)
    return links


def collect_links(positionals: list[str], link_files: list[str]) -> list[str]:
    links: list[str] = []
    for item in positionals:
        candidate = Path(item)
        if not UUID_RE.search(item) and candidate.is_file():
            links.extend(read_link_file(candidate))
        else:
            links.append(item)
    for item in link_files:
        links.extend(read_link_file(Path(item)))
    return links


class Manifest:
    def __init__(self, path: Path, outdir: Path, entries: dict):
        self.path = path
        self.outdir = outdir
        self.entries = entries
        self.dirty = False
        self._by_name: dict[str, Path] | None = None

    @classmethod
    def load(cls, outdir: Path) -> "Manifest":
        path = cls._locate(outdir)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls(path, outdir, {})
        entries = data.get("exports") if isinstance(data, dict) else None
        return cls(path, outdir, entries if isinstance(entries, dict) else {})

    @staticmethod
    def _locate(outdir: Path) -> Path:
        here = outdir / MANIFEST_NAME
        if here.exists():
            return here
        for parent in list(outdir.resolve().parents)[:2]:
            candidate = parent / MANIFEST_NAME
            if candidate.exists():
                return candidate
        return here

    def _index(self) -> dict[str, Path]:
        if self._by_name is not None:
            return self._by_name
        index: dict[str, Path] = {}
        roots = {self.outdir, self.path.parent}
        for root in roots:
            for child in self._listdir(root):
                if child.is_dir():
                    if not child.name.startswith("."):
                        for grandchild in self._listdir(child):
                            if grandchild.suffix == ".md" and grandchild.is_file():
                                index.setdefault(grandchild.name, grandchild)
                elif child.suffix == ".md":
                    index.setdefault(child.name, child)
        self._by_name = index
        return index

    @staticmethod
    def _listdir(directory: Path) -> list[Path]:
        try:
            return sorted(directory.iterdir())
        except OSError:
            return []

    def lookup(self, uuid: str) -> Path | None:
        entry = self.entries.get(uuid)
        if not isinstance(entry, dict):
            return None
        name = entry.get("file")
        if not name:
            return None
        for base in (self.path.parent, self.outdir):
            candidate = base / name
            if candidate.exists():
                return candidate
        return self._index().get(Path(name).name)

    def messages(self, uuid: str) -> int:
        entry = self.entries.get(uuid)
        return (entry.get("messages") or 0) if isinstance(entry, dict) else 0

    def _record_name(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.path.parent.resolve()).as_posix()
        except ValueError:
            return path.name

    def note_location(self, uuid: str, path: Path) -> None:
        entry = self.entries.get(uuid)
        if not isinstance(entry, dict):
            return
        name = self._record_name(path)
        if entry.get("file") != name:
            entry["file"] = name
            self.dirty = True

    def record(self, uuid: str, path: Path, snapshot: dict, count: int) -> None:
        self.entries[uuid] = {
            "file": self._record_name(path),
            "title": (snapshot.get("snapshot_name") or "").strip(),
            "messages": count,
            "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        self.dirty = True

    def save(self) -> None:
        if not self.dirty:
            return
        payload = {"version": 1, "exports": self.entries}
        try:
            self.path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            print(f"warning: could not write manifest: {exc}", file=sys.stderr)
        else:
            self.dirty = False


def export_one(link: str, outdir: Path, include_thinking: bool,
               manifest: Manifest, force: bool,
               firebase_collection: str | None = None) -> tuple[str, Path, int]:
    uuid = extract_uuid(link)
    existing = manifest.lookup(uuid)
    if existing is not None and not force:
        manifest.note_location(uuid, existing)
        return "skipped", existing, manifest.messages(uuid)

    snapshot = fetch_snapshot(uuid)
    markdown, count = render_markdown(snapshot, uuid, include_thinking)

    if existing is not None:
        path = existing
    else:
        slug = slugify(snapshot.get("snapshot_name") or "", uuid)
        path = unique_path(outdir, slug)
    path.write_text(markdown, encoding="utf-8")
    manifest.record(uuid, path, snapshot, count)

    if firebase_collection:
        creator = snapshot.get("creator") or {}
        author = (snapshot.get("created_by") or "").strip() or (creator.get("full_name") or "").strip()
        created = (snapshot.get("created_at") or "")[:10]
        title = (snapshot.get("snapshot_name") or "").strip() or "Untitled"
        _upload_to_firestore(
            uuid=uuid, title=title, markdown=markdown, author=author,
            created=created, message_count=count,
            source_url=SHARE_URL.format(uuid=uuid), collection=firebase_collection,
        )

    return "written", path, count


def main() -> int:
    parser = argparse.ArgumentParser(description="Save claude.ai share links as markdown transcripts.")
    parser.add_argument("inputs", nargs="*", metavar="LINK|FILE",
                        help="share URLs, bare UUIDs, or a links file")
    parser.add_argument("-f", "--file", action="append", default=[], metavar="FILE",
                        help="read links from FILE (repeatable)")
    parser.add_argument("-o", "--out", default=".", metavar="DIR",
                        help="output directory (default: current directory)")
    parser.add_argument("--include-thinking", action="store_true",
                        help="include thinking blocks")
    parser.add_argument("--force", action="store_true",
                        help="re-fetch already exported conversations")
    parser.add_argument("--firebase-upload", nargs="?", const="chats", metavar="COLLECTION",
                        default=None,
                        help="upload transcripts to Firestore (requires FIREBASE_SERVICE_ACCOUNT_KEY env var)")
    args = parser.parse_args()

    if not args.inputs and not args.file:
        parser.error("no links given")

    try:
        links = collect_links(args.inputs, args.file)
    except ExportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    seen: set[str] = set()
    ordered: list[str] = []
    for link in links:
        match = UUID_RE.search(link)
        key = match.group(0).lower() if match else link
        if key not in seen:
            seen.add(key)
            ordered.append(link)

    if not ordered:
        print("error: no links found", file=sys.stderr)
        return 1

    outdir = Path(args.out)
    try:
        outdir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"error: cannot create {outdir}: {exc}", file=sys.stderr)
        return 1

    manifest = Manifest.load(outdir)
    if manifest.entries:
        print(f"manifest: {manifest.path} ({len(manifest.entries)} already exported)")

    failures: list[tuple[str, str]] = []
    written = skipped = firebase_uploaded = 0

    for link in ordered:
        try:
            status, path, count = export_one(
                link, outdir, args.include_thinking, manifest, args.force,
                firebase_collection=args.firebase_upload,
            )
        except ExportError as exc:
            failures.append((link, str(exc)))
            print(f"failed {link}: {exc}", file=sys.stderr)
        except OSError as exc:
            failures.append((link, str(exc)))
            print(f"failed {link}: cannot write output: {exc}", file=sys.stderr)
        else:
            if status == "skipped":
                skipped += 1
                print(f"skipped {path} (already exported)")
            else:
                written += 1
                print(f"wrote {path} ({count} messages)")
                manifest.save()
                if args.firebase_upload:
                    firebase_uploaded += 1
                    print(f"  uploaded {extract_uuid(link)} to Firestore")

    manifest.save()

    summary_parts = [f"{written} written, {skipped} skipped"]
    if firebase_uploaded:
        summary_parts.append(f", {firebase_uploaded} uploaded to Firestore")
    summary = "".join(summary_parts)
    if failures:
        print(f"\n{summary}, {len(failures)} of {len(ordered)} failed", file=sys.stderr)
        return 1
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
