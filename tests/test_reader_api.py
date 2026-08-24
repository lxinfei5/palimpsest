from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from palimpsest.paths import find_root
from palimpsest.reader.server import build_handler


class _WFile(BytesIO):
    def write(self, b: bytes) -> int:  # type: ignore[override]
        return super().write(b)


def _request(path: str, method: str = "GET", body_data: dict | None = None):
    root = find_root(Path(__file__).resolve().parents[1])
    handler_cls = build_handler(root)
    handler = handler_cls.__new__(handler_cls)
    handler.path = path
    handler.command = method
    handler.request_version = "HTTP/1.1"

    if body_data is not None:
        raw_body = json.dumps(body_data).encode("utf-8")
        handler.headers = {"Content-Length": str(len(raw_body))}
        handler.rfile = BytesIO(raw_body)
    else:
        handler.headers = {}
        handler.rfile = BytesIO()

    handler.wfile = BytesIO()
    sent = {}

    def send_response(code):
        sent["code"] = code

    def send_header(k, v):
        sent.setdefault("headers", {})[k] = v

    def end_headers():
        sent["ended"] = True

    handler.send_response = send_response  # type: ignore[method-assign]
    handler.send_header = send_header  # type: ignore[method-assign]
    handler.end_headers = end_headers  # type: ignore[method-assign]

    if method == "POST":
        handler.do_POST()
    else:
        handler.do_GET()

    body = handler.wfile.getvalue()
    return sent.get("code", 200), body, sent.get("headers", {})


def test_api_books_and_chapter():
    code, body, _ = _request("/api/books")
    assert code == 200
    data = json.loads(body.decode("utf-8"))
    ids = {b["id"] for b in data["books"]}
    assert "harbor-bell" in ids

    code, body, _ = _request("/api/books/harbor-bell/toc")
    assert code == 200
    toc = json.loads(body.decode("utf-8"))
    assert toc["title"] == "港铃"
    assert any(v["id"] == "continue" for v in toc["volumes"])

    code, body, _ = _request("/api/books/harbor-bell/chapters/original/c001.md")
    assert code == 200
    ch = json.loads(body.decode("utf-8"))
    assert "雾来之前" in ch["title"] or "雾来之前" in ch["markdown"]

    code, body, _ = _request("/api/books/harbor-bell/chapters/continue/c004.md")
    assert code == 200
    ch = json.loads(body.decode("utf-8"))
    assert "退潮" in ch["markdown"]


def test_workbench_endpoints():
    # Overview
    code, body, _ = _request("/api/books/harbor-bell/overview")
    assert code == 200
    overview = json.loads(body.decode("utf-8"))
    assert overview["id"] == "harbor-bell"
    assert overview["stats"]["characters"] >= 3

    # Canon
    code, body, _ = _request("/api/books/harbor-bell/canon")
    assert code == 200
    canon = json.loads(body.decode("utf-8"))
    assert len(canon["characters"]) >= 3
    assert len(canon["locations"]) >= 1

    # Continuity
    code, body, _ = _request("/api/books/harbor-bell/continuity")
    assert code == 200
    cont = json.loads(body.decode("utf-8"))
    assert len(cont["open_threads"]) >= 1

    # Outline
    code, body, _ = _request("/api/books/harbor-bell/outline")
    assert code == 200
    outl = json.loads(body.decode("utf-8"))
    assert any("continue_brief" in f["file"] for f in outl["files"])

    # Sessions
    code, body, _ = _request("/api/books/harbor-bell/sessions")
    assert code == 200
    sess = json.loads(body.decode("utf-8"))
    assert len(sess["sessions"]) >= 1

    # Validate
    code, body, _ = _request("/api/books/harbor-bell/validate")
    assert code == 200
    val = json.loads(body.decode("utf-8"))
    assert val["ok"] is True

    # Quality
    code, body, _ = _request("/api/books/harbor-bell/quality")
    assert code == 200
    qual = json.loads(body.decode("utf-8"))
    assert qual["ok"] is True
    assert qual["chapter_id"] == "c004"

    # Check
    code, body, _ = _request("/api/books/harbor-bell/check")
    assert code == 200
    chk = json.loads(body.decode("utf-8"))
    assert chk["ok"] is True

    # Context
    code, body, _ = _request("/api/books/harbor-bell/context?max_chars=4000")
    assert code == 200
    ctx = json.loads(body.decode("utf-8"))
    assert "pack" in ctx
    assert len(ctx["pack"]) > 0

    # ST Export & Download
    code, body, _ = _request("/api/books/harbor-bell/export/st", method="POST")
    assert code == 200
    code, body, _ = _request("/api/download/harbor-bell/st/lore")
    assert code == 200
    assert "entries" in body.decode("utf-8") or "港铃" in body.decode("utf-8")

    # EPUB Export & Download
    code, body, _ = _request("/api/books/harbor-bell/export/epub", method="POST", body_data={"volume": "original"})
    assert code == 200
    code, body, headers = _request("/api/download/harbor-bell/epub/original")
    assert code == 200
    assert len(body) > 0


def test_static_index():
    code, body, _ = _request("/")
    assert code == 200
    assert b"Palimpsest" in body
    assert b"workbench-body" in body

