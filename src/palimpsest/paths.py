"""Repository and book path helpers."""

from __future__ import annotations

import os
import re
from pathlib import Path

BOOK_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
VOLUME_SEP = "::"

KIND_LABEL = {
    "original": "原作",
    "continue": "续写",
    "side": "番外",
    "rewrite": "改写",
}


def find_root(explicit: str | Path | None = None) -> Path:
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if not (root / "templates" / "book").is_dir():
            raise FileNotFoundError(f"not a Palimpsest root (missing templates/book): {root}")
        return root
    env = os.environ.get("PALIMPSEST_ROOT")
    if env:
        return find_root(env)
    here = Path.cwd().resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "templates" / "book").is_dir() and (candidate / "schemas").is_dir():
            return candidate
    pkg_repo = Path(__file__).resolve().parents[2]
    if (pkg_repo / "templates" / "book").is_dir():
        return pkg_repo
    raise FileNotFoundError(
        "cannot find Palimpsest root. Run inside the repo, or pass --root, or set PALIMPSEST_ROOT."
    )


def books_dir(root: Path) -> Path:
    return root / "books"


def book_dir(root: Path, book_id: str) -> Path:
    return books_dir(root) / book_id


def template_dir(root: Path) -> Path:
    return root / "templates" / "book"


def validate_book_id(book_id: str) -> str:
    if not BOOK_ID_RE.match(book_id):
        raise ValueError("book-id must be lowercase letters, digits, and hyphens (e.g. harbor-bell)")
    return book_id


def split_shelf_id(shelf_id: str) -> tuple[str, str | None]:
    if not shelf_id:
        return "", None
    if VOLUME_SEP in shelf_id:
        parent, vol = shelf_id.split(VOLUME_SEP, 1)
        return parent, vol or None
    return shelf_id, None


def make_shelf_id(book_id: str, volume_id: str | None = None) -> str:
    if not volume_id or volume_id == "original":
        return book_id
    return f"{book_id}{VOLUME_SEP}{volume_id}"
