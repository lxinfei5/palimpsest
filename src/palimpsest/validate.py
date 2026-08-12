"""Structural checks for a book sandbox."""

from __future__ import annotations

from pathlib import Path

from palimpsest.books import load_yaml
from palimpsest.paths import BOOK_ID_RE
from palimpsest.volumes import discover_volumes


def validate_book(book_path: Path) -> list[str]:
    errors: list[str] = []
    meta_path = book_path / "00_meta" / "book.yaml"
    if not meta_path.is_file():
        return [f"missing {meta_path}"]
    meta = load_yaml(meta_path)
    book_id = str(meta.get("id") or "")
    if book_id != book_path.name:
        errors.append(f"book.yaml id {book_id!r} != directory {book_path.name!r}")
    if book_id and not BOOK_ID_RE.match(book_id):
        errors.append(f"invalid book id: {book_id}")
    if not meta.get("title"):
        errors.append("book.yaml missing title")

    for required in (
        "01_sources",
        "02_canon/characters",
        "03_continuity",
        "04_outline",
        "05_manuscript",
        "06_prompts",
        "_agent",
    ):
        if not (book_path / required).exists():
            errors.append(f"missing path: {required}")

    index_path = book_path / "02_canon" / "characters" / "_index.yaml"
    if index_path.is_file():
        index = load_yaml(index_path)
        for row in index.get("characters") or []:
            if not isinstance(row, dict):
                continue
            fname = row.get("file") or f"{row.get('id')}.yaml"
            fpath = book_path / "02_canon" / "characters" / fname
            if not fpath.is_file():
                errors.append(f"character listed but missing file: {fname}")
            else:
                card = load_yaml(fpath)
                for field in ("id", "name", "tier", "summary"):
                    if not card.get(field):
                        errors.append(f"{fname} missing {field}")

    volumes = discover_volumes(book_path, book_id or book_path.name)
    ids = [v.get("id") for v in volumes]
    if len(ids) != len(set(ids)):
        errors.append(f"duplicate volume ids: {ids}")
    return errors
