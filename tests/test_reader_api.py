from __future__ import annotations

from io import BytesIO
from pathlib import Path

from palimpsest.paths import find_root
from palimpsest.reader.server import build_handler


class _WFile(BytesIO):
    def write(self, b: bytes) -> int:  # type: ignore[override]
        return super().write(b)


def _request(path: str):
    root = find_root(Path(__file__).resolve().parents[1])
    handler_cls = build_handler(root)
    handler = handler_cls.__new__(handler_cls)
    handler.path = path
    handler.headers = {}
    handler.wfile = BytesIO()
    handler.command = "GET"
    handler.request_version = "HTTP/1.1"
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
    handler.do_GET()
    body = handler.wfile.getvalue()
    return sent["code"], body


def test_api_books_and_chapter():
    import json

    code, body = _request("/api/books")
    assert code == 200
    data = json.loads(body.decode("utf-8"))
    ids = {b["id"] for b in data["books"]}
    assert "harbor-bell" in ids

    code, body = _request("/api/books/harbor-bell/toc")
    assert code == 200
    toc = json.loads(body.decode("utf-8"))
    assert toc["title"] == "港铃"
    assert any(v["id"] == "continue" for v in toc["volumes"])

    code, body = _request("/api/books/harbor-bell/chapters/original/c001.md")
    assert code == 200
    ch = json.loads(body.decode("utf-8"))
    assert "雾来之前" in ch["title"] or "雾来之前" in ch["markdown"]

    code, body = _request("/api/books/harbor-bell/chapters/continue/c004.md")
    assert code == 200
    ch = json.loads(body.decode("utf-8"))
    assert "退潮" in ch["markdown"]


def test_static_index():
    code, body = _request("/")
    assert code == 200
    assert b"Palimpsest" in body
