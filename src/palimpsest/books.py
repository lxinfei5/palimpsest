"""Create, list, and inspect books."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml

from palimpsest.paths import book_dir, books_dir, template_dir, validate_book_id


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def create_book(root: Path, book_id: str, title: str | None = None) -> Path:
    book_id = validate_book_id(book_id)
    dest = book_dir(root, book_id)
    if dest.exists():
        raise FileExistsError(f"already exists: {dest}")
    src = template_dir(root)
    if not src.is_dir():
        raise FileNotFoundError(f"missing template: {src}")
    shutil.copytree(src, dest)
    created = utc_now()
    display = title or book_id
    for path in dest.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".yaml", ".yml", ".txt", ""}:
            continue
        text = path.read_text(encoding="utf-8")
        if "{{" not in text:
            continue
        path.write_text(
            text.replace("{{BOOK_ID}}", book_id)
            .replace("{{BOOK_TITLE}}", display)
            .replace("{{CREATED_AT}}", created),
            encoding="utf-8",
        )
    return dest


def iter_books(root: Path) -> list[dict]:
    out: list[dict] = []
    base = books_dir(root)
    if not base.is_dir():
        return out
    for child in sorted(base.iterdir()):
        meta_path = child / "00_meta" / "book.yaml"
        if not meta_path.is_file():
            continue
        meta = load_yaml(meta_path)
        out.append(
            {
                "id": meta.get("id") or child.name,
                "title": meta.get("title") or child.name,
                "status": meta.get("status") or "unknown",
                "language": meta.get("language") or "",
                "content_rating": meta.get("content_rating") or "unrated",
                "synopsis": meta.get("synopsis") or "",
                "path": str(child),
            }
        )
    return out


def require_book(root: Path, book_id: str) -> Path:
    dest = book_dir(root, book_id)
    if not (dest / "00_meta" / "book.yaml").is_file():
        raise FileNotFoundError(f"book not found: {book_id}")
    return dest
