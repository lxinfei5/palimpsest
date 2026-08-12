"""Discover manuscript volumes and chapters."""

from __future__ import annotations

import re
from pathlib import Path

from palimpsest.books import load_yaml
from palimpsest.paths import KIND_LABEL, make_shelf_id

CHAPTER_NAME = re.compile(r"^(c|r|s)(\d+)", re.I)


def chapter_sort_key(name: str) -> tuple:
    stem = Path(name).stem
    m = CHAPTER_NAME.match(stem)
    n = int(m.group(2)) if m else 9999
    return (n, stem)


def parse_title_from_name(name: str) -> str:
    stem = Path(name).stem
    m = re.match(r"c\d+_(.+)$", stem, re.I)
    if m:
        return m.group(1)
    return stem


def list_md_chapters(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    seen: set[Path] = set()
    out: list[Path] = []
    for path in directory.glob("*.md"):
        low = path.name.lower()
        if low in {"readme.md"} or low.startswith("readme"):
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        out.append(path)
    out.sort(key=lambda p: chapter_sort_key(p.name))
    return out


def _volume_meta(vol_dir: Path, defaults: dict) -> dict:
    meta = dict(defaults)
    yml = vol_dir / "volume.yaml"
    if yml.is_file():
        loaded = load_yaml(yml)
        meta.update({k: v for k, v in loaded.items() if v is not None})
    return meta


def discover_volumes(book_path: Path, book_id: str) -> list[dict]:
    ms = book_path / "05_manuscript"
    volumes: list[dict] = []

    original = ms / "original"
    if original.is_dir():
        chapters = list_md_chapters(original)
        if chapters or (original / "volume.yaml").is_file():
            meta = _volume_meta(
                original,
                {
                    "id": "original",
                    "title": "原作",
                    "kind": "original",
                    "order": 0,
                    "parent_book": book_id,
                },
            )
            volumes.append(
                {
                    **meta,
                    "dir": original,
                    "shelf_id": make_shelf_id(book_id, None),
                    "chapters": chapters,
                }
            )

    vol_root = ms / "volumes"
    if vol_root.is_dir():
        for child in sorted(vol_root.iterdir()):
            if not child.is_dir():
                continue
            chapters = list_md_chapters(child)
            meta = _volume_meta(
                child,
                {
                    "id": child.name,
                    "title": child.name,
                    "kind": "side",
                    "order": 100,
                    "parent_book": book_id,
                },
            )
            kind = str(meta.get("kind") or "side")
            volumes.append(
                {
                    **meta,
                    "dir": child,
                    "shelf_id": make_shelf_id(book_id, str(meta.get("id") or child.name)),
                    "chapters": chapters,
                    "kind": kind,
                    "kind_label": KIND_LABEL.get(kind, kind),
                }
            )

    for legacy_kind in ("continue", "rewrite"):
        legacy = ms / legacy_kind
        if not legacy.is_dir():
            continue
        chapters = list_md_chapters(legacy)
        if not chapters:
            continue
        already = any(v.get("id") == legacy_kind and v.get("dir") != legacy for v in volumes)
        if already:
            continue
        volumes.append(
            {
                "id": legacy_kind,
                "title": KIND_LABEL.get(legacy_kind, legacy_kind),
                "kind": legacy_kind,
                "order": 50 if legacy_kind == "continue" else 60,
                "parent_book": book_id,
                "dir": legacy,
                "shelf_id": make_shelf_id(book_id, legacy_kind),
                "chapters": chapters,
                "legacy": True,
            }
        )

    for vol in volumes:
        vol.setdefault("kind_label", KIND_LABEL.get(str(vol.get("kind")), str(vol.get("kind"))))
        vol["chapter_count"] = len(vol.get("chapters") or [])

    def _order(vol: dict) -> int:
        raw = vol.get("order")
        return int(raw) if raw is not None else 100

    volumes.sort(key=lambda v: (_order(v), str(v.get("id"))))
    return volumes


def resolve_volume(book_path: Path, book_id: str, volume_id: str | None) -> dict | None:
    want = volume_id or "original"
    for vol in discover_volumes(book_path, book_id):
        if vol.get("id") == want or (want == "original" and vol.get("kind") == "original"):
            return vol
    return None


def chapter_heading(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    body = strip_front_matter(text)
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return parse_title_from_name(path.name)


def strip_front_matter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].lstrip("\n")
    return text
