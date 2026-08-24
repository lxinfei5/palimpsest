"""Local HTTP server & API for Palimpsest Web GUI workbench."""

from __future__ import annotations

import json
import mimetypes
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from palimpsest.books import create_book, iter_books, load_yaml, require_book
from palimpsest.check import check_book, format_report as format_check_report
from palimpsest.context import DEFAULT_MAX_CHARS, assemble_context
from palimpsest.export.epub import export_epub
from palimpsest.export.st import export_st
from palimpsest.quality import check_quality, format_report as format_quality_report, parse_front_matter
from palimpsest.validate import validate_book
from palimpsest.volumes import (
    chapter_heading,
    discover_volumes,
    resolve_volume,
    strip_front_matter,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")


def _read_lore_dir(dir_path: Path) -> list[dict]:
    if not dir_path.is_dir():
        return []
    items: list[dict] = []
    for file in sorted(dir_path.glob("*.yaml")):
        if file.name.startswith("_"):
            continue
        data = load_yaml(file)
        if data:
            data.setdefault("id", file.stem)
            data.setdefault("_file", file.name)
            items.append(data)
    return items


def build_handler(root: Path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

        def _send(self, code: int, body: bytes, content_type: str, headers: dict | None = None) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if headers:
                for k, v in headers.items():
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, code: int, payload: object) -> None:
            self._send(code, _json_bytes(payload), "application/json; charset=utf-8")

        def _read_body_json(self) -> dict:
            try:
                length = int(self.headers.get("Content-Length", 0))
                if length <= 0:
                    return {}
                raw = self.rfile.read(length).decode("utf-8")
                return json.loads(raw) if raw.strip() else {}
            except Exception:
                return {}

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = unquote(parsed.path)
            qs = parse_qs(parsed.query)
            if path.startswith("/api/"):
                return self._api_get(path, qs)
            return self._static(path)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = unquote(parsed.path)
            qs = parse_qs(parsed.query)
            body = self._read_body_json()
            if path.startswith("/api/"):
                return self._api_post(path, qs, body)
            self._send_json(404, {"error": "not found"})

        def _static(self, path: str) -> None:
            rel = "index.html" if path in {"/", "/index.html"} else path.lstrip("/")
            if ".." in rel:
                self._send(400, b"bad path", "text/plain")
                return
            file_path = (STATIC_DIR / rel).resolve()
            if not str(file_path).startswith(str(STATIC_DIR.resolve())) or not file_path.is_file():
                self._send(404, b"not found", "text/plain")
                return
            ctype = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype.endswith("json") or ctype.endswith("javascript"):
                ctype = f"{ctype}; charset=utf-8"
            self._send(200, file_path.read_bytes(), ctype)

        def _api_get(self, path: str, qs: dict) -> None:
            parts = path.strip("/").split("/")

            # GET /api/books
            if path == "/api/books":
                books = []
                for book in iter_books(root):
                    bpath = Path(book["path"])
                    vols = discover_volumes(bpath, book["id"])
                    books.append(
                        {
                            **{k: book[k] for k in ("id", "title", "status", "language", "content_rating", "synopsis")},
                            "volumes": [
                                {
                                    "id": v["id"],
                                    "title": v.get("title"),
                                    "kind": v.get("kind"),
                                    "kind_label": v.get("kind_label"),
                                    "order": v.get("order"),
                                    "shelf_id": v.get("shelf_id"),
                                    "chapter_count": v.get("chapter_count"),
                                }
                                for v in vols
                            ],
                        }
                    )
                self._send_json(200, {"books": books})
                return

            # GET /api/download/<book_id>/epub/<vol>
            if len(parts) == 5 and parts[0] == "api" and parts[1] == "download" and parts[3] == "epub":
                book_id = parts[2]
                vol_id = parts[4]
                try:
                    bpath = require_book(root, book_id)
                except FileNotFoundError:
                    self._send_json(404, {"error": "book not found"})
                    return
                epub_path = bpath / "07_export" / "epub" / f"{book_id}-{vol_id}.epub"
                if not epub_path.is_file():
                    try:
                        export_epub(bpath, book_id, vol_id)
                    except Exception as e:
                        self._send_json(404, {"error": f"epub not found and export failed: {e}"})
                        return
                if epub_path.is_file():
                    headers = {"Content-Disposition": f'attachment; filename="{epub_path.name}"'}
                    self._send(200, epub_path.read_bytes(), "application/epub+zip", headers)
                    return
                self._send_json(404, {"error": "file not found"})
                return

            # GET /api/download/<book_id>/st/<type> (lore | writer)
            if len(parts) == 5 and parts[0] == "api" and parts[1] == "download" and parts[3] == "st":
                book_id = parts[2]
                st_type = parts[4]
                try:
                    bpath = require_book(root, book_id)
                except FileNotFoundError:
                    self._send_json(404, {"error": "book not found"})
                    return
                filename = f"{book_id}-{st_type}.json"
                st_path = bpath / "07_export" / "st" / filename
                if not st_path.is_file():
                    try:
                        export_st(bpath, book_id)
                    except Exception as e:
                        self._send_json(404, {"error": f"export failed: {e}"})
                        return
                if st_path.is_file():
                    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
                    self._send(200, st_path.read_bytes(), "application/json; charset=utf-8", headers)
                    return
                self._send_json(404, {"error": "file not found"})
                return

            # Book-scoped endpoints: /api/books/<id>/...
            if len(parts) >= 3 and parts[0] == "api" and parts[1] == "books":
                book_id = parts[2]
                try:
                    bpath = require_book(root, book_id)
                except FileNotFoundError:
                    self._send_json(404, {"error": f"book not found: {book_id}"})
                    return

                # GET /api/books/<id>/overview
                if len(parts) == 4 and parts[3] == "overview":
                    meta = load_yaml(bpath / "00_meta" / "book.yaml")
                    vols = discover_volumes(bpath, book_id)
                    agent_state = ""
                    state_file = bpath / "_agent" / "STATE.md"
                    if state_file.is_file():
                        agent_state = state_file.read_text(encoding="utf-8", errors="replace")

                    # canon counts
                    chars_index = load_yaml(bpath / "02_canon" / "characters" / "_index.yaml")
                    char_count = len(chars_index.get("characters") or [])
                    locs_count = len(list((bpath / "02_canon" / "locations").glob("*.yaml")))
                    rules_count = len(list((bpath / "02_canon" / "rules").glob("*.yaml")))
                    items_count = len(list((bpath / "02_canon" / "items").glob("*.yaml")))

                    # continuity counts
                    cstates = load_yaml(bpath / "03_continuity" / "character_states.yaml")
                    cstate_count = len(cstates.get("states") or [])
                    threads = load_yaml(bpath / "03_continuity" / "open_threads.yaml")
                    thread_list = threads.get("threads") or []
                    open_thread_count = sum(1 for t in thread_list if t.get("status") == "open")

                    # word / char stats across manuscript
                    total_chars = 0
                    for vol in vols:
                        for ch in vol.get("chapters") or []:
                            txt = strip_front_matter(ch.read_text(encoding="utf-8", errors="replace"))
                            total_chars += len(txt.strip())

                    self._send_json(
                        200,
                        {
                            "id": book_id,
                            "meta": meta,
                            "agent_state": agent_state,
                            "stats": {
                                "volumes": len(vols),
                                "total_chapters": sum(v.get("chapter_count", 0) for v in vols),
                                "total_chars": total_chars,
                                "characters": char_count,
                                "locations": locs_count,
                                "rules": rules_count,
                                "items": items_count,
                                "character_states": cstate_count,
                                "open_threads": open_thread_count,
                                "total_threads": len(thread_list),
                            },
                        },
                    )
                    return

                # GET /api/books/<id>/toc
                if len(parts) == 4 and parts[3] == "toc":
                    meta = load_yaml(bpath / "00_meta" / "book.yaml")
                    vols = discover_volumes(bpath, book_id)
                    self._send_json(
                        200,
                        {
                            "id": book_id,
                            "title": meta.get("title") or book_id,
                            "synopsis": meta.get("synopsis") or "",
                            "volumes": [
                                {
                                    "id": v["id"],
                                    "title": v.get("title"),
                                    "kind": v.get("kind"),
                                    "kind_label": v.get("kind_label"),
                                    "order": v.get("order"),
                                    "shelf_id": v.get("shelf_id"),
                                    "chapters": [
                                        {
                                            "file": p.name,
                                            "title": chapter_heading(p),
                                            "size": len(strip_front_matter(p.read_text(encoding="utf-8", errors="replace"))),
                                        }
                                        for p in v["chapters"]
                                    ],
                                }
                                for v in vols
                            ],
                        },
                    )
                    return

                # GET /api/books/<id>/chapters/<volume_id>/<filename>
                if len(parts) == 6 and parts[3] == "chapters":
                    volume_id = parts[4]
                    filename = parts[5]
                    if "/" in filename or filename.startswith("."):
                        self._send_json(400, {"error": "bad filename"})
                        return
                    vol = resolve_volume(bpath, book_id, volume_id)
                    if not vol:
                        self._send_json(404, {"error": "volume not found"})
                        return
                    chapter = vol["dir"] / filename
                    if not chapter.is_file() or chapter.suffix.lower() != ".md":
                        self._send_json(404, {"error": "chapter not found"})
                        return
                    raw = chapter.read_text(encoding="utf-8", errors="replace")
                    front_matter = parse_front_matter(raw)
                    markdown = strip_front_matter(raw)
                    self._send_json(
                        200,
                        {
                            "book_id": book_id,
                            "volume_id": vol["id"],
                            "volume_title": vol.get("title"),
                            "volume_kind": vol.get("kind"),
                            "file": filename,
                            "title": chapter_heading(chapter),
                            "front_matter": front_matter,
                            "markdown": markdown,
                            "chars": len(markdown.strip()),
                            "raw": raw,
                        },
                    )
                    return

                # GET /api/books/<id>/canon
                if len(parts) == 4 and parts[3] == "canon":
                    char_index = load_yaml(bpath / "02_canon" / "characters" / "_index.yaml")
                    char_files = list((bpath / "02_canon" / "characters").glob("*.yaml"))
                    characters = []
                    for cf in sorted(char_files):
                        if cf.name.startswith("_"):
                            continue
                        card = load_yaml(cf)
                        if card:
                            card.setdefault("id", cf.stem)
                            characters.append(card)

                    extras = load_yaml(bpath / "02_canon" / "characters" / "_extras.yaml")
                    relationships_file = bpath / "02_canon" / "characters" / "_relationships.md"
                    relationships = relationships_file.read_text(encoding="utf-8", errors="replace") if relationships_file.is_file() else ""

                    locations = _read_lore_dir(bpath / "02_canon" / "locations")
                    rules = _read_lore_dir(bpath / "02_canon" / "rules")
                    items = _read_lore_dir(bpath / "02_canon" / "items")
                    factions = _read_lore_dir(bpath / "02_canon" / "factions")
                    glossary = _read_lore_dir(bpath / "02_canon" / "glossary")

                    timeline_data = load_yaml(bpath / "02_canon" / "timeline" / "events.yaml")

                    self._send_json(
                        200,
                        {
                            "index": char_index,
                            "characters": characters,
                            "extras": extras.get("characters") or [],
                            "relationships": relationships,
                            "locations": locations,
                            "rules": rules,
                            "items": items,
                            "factions": factions,
                            "glossary": glossary,
                            "timeline": timeline_data.get("events") or [],
                        },
                    )
                    return

                # GET /api/books/<id>/continuity
                if len(parts) == 4 and parts[3] == "continuity":
                    cstates = load_yaml(bpath / "03_continuity" / "character_states.yaml")
                    threads = load_yaml(bpath / "03_continuity" / "open_threads.yaml")
                    conflicts_file = bpath / "03_continuity" / "conflicts.md"
                    conflicts = conflicts_file.read_text(encoding="utf-8", errors="replace") if conflicts_file.is_file() else ""

                    self._send_json(
                        200,
                        {
                            "character_states": cstates,
                            "open_threads": threads.get("threads") or [],
                            "threads_meta": {k: v for k, v in threads.items() if k != "threads"},
                            "conflicts": conflicts,
                        },
                    )
                    return

                # GET /api/books/<id>/outline
                if len(parts) == 4 and parts[3] == "outline":
                    outline_dir = bpath / "04_outline"
                    files = []
                    if outline_dir.is_dir():
                        for f in sorted(outline_dir.glob("*.md")):
                            files.append({"file": f.name, "title": f.stem, "content": f.read_text(encoding="utf-8", errors="replace")})
                    self._send_json(200, {"files": files})
                    return

                # GET /api/books/<id>/sessions
                if len(parts) == 4 and parts[3] == "sessions":
                    sessions_dir = bpath / "08_sessions"
                    sessions = []
                    if sessions_dir.is_dir():
                        for f in sorted(sessions_dir.glob("*.md"), reverse=True):
                            if f.name == "TEMPLATE.md":
                                continue
                            sessions.append({"file": f.name, "content": f.read_text(encoding="utf-8", errors="replace")})
                    self._send_json(200, {"sessions": sessions})
                    return

                # GET /api/books/<id>/validate
                if len(parts) == 4 and parts[3] == "validate":
                    errors = validate_book(bpath)
                    self._send_json(200, {"ok": len(errors) == 0, "errors": errors})
                    return

                # GET /api/books/<id>/quality
                if len(parts) == 4 and parts[3] == "quality":
                    chapter_arg = qs.get("chapter", [None])[0]
                    report = check_quality(bpath, book_id, chapter=chapter_arg)
                    self._send_json(
                        200,
                        {
                            "ok": report.ok,
                            "chapter_id": report.chapter_id,
                            "kind": report.kind,
                            "source_field": report.source_field,
                            "source": report.source,
                            "chars": report.chars,
                            "words": report.words,
                            "target_min": report.target_min,
                            "target_max": report.target_max,
                            "brief_path": str(report.brief_path.relative_to(bpath)) if report.brief_path else None,
                            "session_path": str(report.session_path.relative_to(bpath)) if report.session_path else None,
                            "errors": report.errors,
                            "warnings": report.warnings,
                            "formatted": format_quality_report(report),
                        },
                    )
                    return

                # GET /api/books/<id>/check
                if len(parts) == 4 and parts[3] == "check":
                    vol_arg = qs.get("volume", [None])[0]
                    report = check_book(bpath, book_id, volume=vol_arg)
                    self._send_json(
                        200,
                        {
                            "ok": report.ok,
                            "volume": report.volume,
                            "allowlist_size": report.allowlist_size,
                            "chapters_scanned": report.chapters_scanned,
                            "latest_chapter": report.latest_chapter,
                            "thread_chapter": report.thread_chapter,
                            "as_of_chapter": report.as_of_chapter,
                            "threads_checked": report.threads_checked,
                            "errors": report.errors,
                            "warnings": report.warnings,
                            "formatted": format_check_report(report),
                        },
                    )
                    return

                # GET /api/books/<id>/context
                if len(parts) == 4 and parts[3] == "context":
                    chapter_arg = qs.get("chapter", [None])[0]
                    max_chars_arg = int(qs.get("max_chars", [DEFAULT_MAX_CHARS])[0])
                    pack, warnings = assemble_context(bpath, book_id, chapter=chapter_arg, max_chars=max_chars_arg)
                    self._send_json(
                        200,
                        {
                            "pack": pack,
                            "warnings": warnings,
                            "chars": len(pack),
                            "lines": pack.count("\n"),
                        },
                    )
                    return

            self._send_json(404, {"error": "unknown api endpoint"})

        def _api_post(self, path: str, qs: dict, body: dict) -> None:
            parts = path.strip("/").split("/")

            # POST /api/books (create new book)
            if path == "/api/books":
                book_id = str(body.get("id") or "").strip()
                title = str(body.get("title") or "").strip()
                if not book_id:
                    self._send_json(400, {"error": "id is required"})
                    return
                try:
                    dest = create_book(root, book_id, title or book_id)
                    self._send_json(200, {"ok": True, "id": book_id, "title": title or book_id, "path": str(dest)})
                except Exception as e:
                    self._send_json(400, {"error": str(e)})
                return

            # POST /api/books/<id>/export/epub
            if len(parts) == 5 and parts[0] == "api" and parts[1] == "books" and parts[3] == "export" and parts[4] == "epub":
                book_id = parts[2]
                vol_id = body.get("volume") or qs.get("volume", ["original"])[0]
                try:
                    bpath = require_book(root, book_id)
                    out = export_epub(bpath, book_id, vol_id)
                    self._send_json(
                        200,
                        {
                            "ok": True,
                            "volume": vol_id,
                            "filename": out.name,
                            "download_url": f"/api/download/{book_id}/epub/{vol_id}",
                        },
                    )
                except Exception as e:
                    self._send_json(400, {"error": str(e)})
                return

            # POST /api/books/<id>/export/st
            if len(parts) == 5 and parts[0] == "api" and parts[1] == "books" and parts[3] == "export" and parts[4] == "st":
                book_id = parts[2]
                try:
                    bpath = require_book(root, book_id)
                    files = export_st(bpath, book_id)
                    self._send_json(
                        200,
                        {
                            "ok": True,
                            "files": [f.name for f in files],
                            "lore_url": f"/api/download/{book_id}/st/lore",
                            "writer_url": f"/api/download/{book_id}/st/writer",
                        },
                    )
                except Exception as e:
                    self._send_json(400, {"error": str(e)})
                return

            self._send_json(404, {"error": "unknown api endpoint"})

    return Handler


def serve(root: Path, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = False) -> None:
    handler = build_handler(root)
    httpd = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{port}/"
    print(f"Palimpsest Workbench  {url}")
    print(f"root                  {root}")
    print("ctrl-c to stop")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        httpd.server_close()
