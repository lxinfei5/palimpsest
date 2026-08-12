"""Local HTTP reader for manuscripts (127.0.0.1 by default)."""

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from palimpsest.books import iter_books, load_yaml, require_book
from palimpsest.volumes import (
    chapter_heading,
    discover_volumes,
    resolve_volume,
    strip_front_matter,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def build_handler(root: Path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            sys_stderr = __import__("sys").stderr
            sys_stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

        def _send(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, code: int, payload: object) -> None:
            self._send(code, _json_bytes(payload), "application/json; charset=utf-8")

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = unquote(parsed.path)
            if path.startswith("/api/"):
                return self._api(path, parse_qs(parsed.query))
            return self._static(path)

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

        def _api(self, path: str, _qs: dict) -> None:
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

            parts = path.strip("/").split("/")
            # /api/books/<id>/toc
            # /api/books/<id>/chapters/<volume_id>/<filename>
            if len(parts) >= 4 and parts[0] == "api" and parts[1] == "books":
                book_id = parts[2]
                try:
                    bpath = require_book(root, book_id)
                except FileNotFoundError:
                    self._send_json(404, {"error": "book not found"})
                    return
                if parts[3] == "toc" and len(parts) == 4:
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
                                        }
                                        for p in v["chapters"]
                                    ],
                                }
                                for v in vols
                            ],
                        },
                    )
                    return
                if parts[3] == "chapters" and len(parts) == 6:
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
                    self._send_json(
                        200,
                        {
                            "book_id": book_id,
                            "volume_id": vol["id"],
                            "file": filename,
                            "title": chapter_heading(chapter),
                            "markdown": strip_front_matter(raw),
                        },
                    )
                    return
            self._send_json(404, {"error": "unknown api"})

    return Handler


def serve(root: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    handler = build_handler(root)
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"Palimpsest reader  http://{host}:{port}/")
    print(f"root               {root}")
    print("ctrl-c to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        httpd.server_close()
