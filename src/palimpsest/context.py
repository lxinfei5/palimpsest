"""Assemble a pasteable context pack (AGENTS.md §8 priorities 1–7)."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from palimpsest.books import load_yaml, require_book
from palimpsest.paths import find_root
from palimpsest.volumes import discover_volumes, list_md_chapters

PROTECTED_MAX_PRIORITY = 4
DEFAULT_MAX_CHARS = 8000
CHUNK_MIN = 800
CHUNK_MAX = 1200
CHUNK_OVERLAP = 80
SA_TIERS = {"S", "A"}
CHAPTER_ID_RE = re.compile(r"^([crs])?(\d+)", re.I)
LORE_DIRS = ("locations", "rules", "items")


@dataclass(frozen=True)
class Section:
    priority: int
    label: str
    relpath: str
    text: str


def register_cli(subparsers) -> None:
    parser = subparsers.add_parser(
        "context",
        help="assemble a pasteable context pack (AGENTS.md §8, priorities 1–7)",
    )
    parser.add_argument("book_id", help="book sandbox id, e.g. harbor-bell")
    parser.add_argument(
        "--chapter",
        help="focus chapter id (includes the previous chapter), e.g. c004",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_CHARS,
        help="character budget; truncate from the bottom (cut 7 then 6)",
    )
    parser.add_argument(
        "--write-chunks",
        action="store_true",
        help="write 01_sources/chunks slices from normalized chapters",
    )
    parser.set_defaults(func=cmd_context)


def cmd_context(args: argparse.Namespace) -> int:
    root = find_root(getattr(args, "root", None))
    book_id = args.book_id
    book_path = require_book(root, book_id)

    if getattr(args, "write_chunks", False):
        written = write_source_chunks(book_path)
        dest = book_path / "01_sources" / "chunks"
        print(f"wrote {len(written)} chunk file(s) under {dest}", file=sys.stderr)

    pack, warnings = assemble_context(
        book_path,
        book_id,
        chapter=getattr(args, "chapter", None),
        max_chars=int(getattr(args, "max_chars", DEFAULT_MAX_CHARS)),
    )
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    sys.stdout.write(pack)
    if pack and not pack.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def assemble_context(
    book_path: Path,
    book_id: str,
    *,
    chapter: str | None = None,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> tuple[str, list[str]]:
    """Return (pack_text, warnings). Priorities 1–4 are never dropped."""
    extra_warnings: list[str] = []
    sections = collect_sections(book_path, book_id, chapter=chapter, warnings=extra_warnings)
    header = _pack_header(book_id, chapter, max_chars)
    protected = _render_pack(header, [s for s in sections if s.priority <= PROTECTED_MAX_PRIORITY])
    full = _render_pack(header, sections)
    pack, cut_warnings = apply_budget(full, protected, max_chars)
    return pack, extra_warnings + cut_warnings


def collect_sections(
    book_path: Path,
    book_id: str,
    *,
    chapter: str | None = None,
    warnings: list[str] | None = None,
) -> list[Section]:
    warnings = warnings if warnings is not None else []
    sections: list[Section] = []
    sections.extend(_section_system(book_path))
    sections.extend(_section_briefs(book_path))
    sections.extend(_section_characters(book_path))
    sections.extend(_section_lore(book_path))
    sections.extend(_section_threads(book_path))
    sections.extend(_section_chapters(book_path, book_id, chapter, warnings))
    sections.extend(_section_chunks(book_path))
    return sections


def apply_budget(full: str, protected: str, max_chars: int) -> tuple[str, list[str]]:
    """Keep 1–4 in full; cut from the bottom (7 then 6, then 5) to fit max_chars."""
    if max_chars < 0:
        max_chars = 0
    if len(full) <= max_chars:
        return full, []
    if len(protected) > max_chars:
        return protected, [
            f"priorities 1–4 exceed --max-chars ({max_chars}); "
            f"included in full ({len(protected)} chars), later items dropped"
        ]
    cut = full[:max_chars]
    nl = cut.rfind("\n")
    if nl >= len(protected):
        cut = cut[: nl + 1]
    if not cut.endswith("\n"):
        cut += "\n"
    return cut, [
        f"truncated from the bottom (cut 7 then 6) to --max-chars {max_chars}"
    ]


def write_source_chunks(book_path: Path) -> list[Path]:
    """Slice normalized chapters into 01_sources/chunks (no LLM)."""
    sources = _normalized_chapter_paths(book_path)
    dest = book_path / "01_sources" / "chunks"
    dest.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for src in sources:
        text = src.read_text(encoding="utf-8", errors="replace")
        parts = slice_source_text(text)
        if not parts:
            continue
        stem = _chunk_stem(src)
        for index, part in enumerate(parts):
            name = f"{stem}.md" if index == 0 else f"{stem}_{index + 1:02d}.md"
            path = dest / name
            payload = part if part.endswith("\n") else part + "\n"
            path.write_text(payload, encoding="utf-8")
            written.append(path)
    return written


def slice_source_text(
    text: str,
    *,
    min_size: int = CHUNK_MIN,
    max_size: int = CHUNK_MAX,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Deterministic windows of ~800–1200 chars with ~80-char overlap."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        return []
    n = len(text)
    if n <= max_size:
        return [text]
    if max_size <= 0:
        return [text]
    overlap = max(0, min(overlap, max_size - 1))
    slices: list[str] = []
    start = 0
    while start < n:
        end = min(start + max_size, n)
        if end < n:
            window = text[start:end]
            br = window.rfind("\n", min_size)
            if br >= min_size:
                end = start + br + 1
        chunk = text[start:end]
        if chunk:
            slices.append(chunk)
        if end >= n:
            break
        nxt = end - overlap
        if nxt <= start:
            nxt = end
        start = nxt
    return slices


def normalize_chapter_id(raw: str) -> str:
    text = (raw or "").strip()
    match = CHAPTER_ID_RE.match(text)
    if not match:
        return text.lower()
    letter = (match.group(1) or "c").lower()
    return f"{letter}{int(match.group(2)):03d}"


def _pack_header(book_id: str, chapter: str | None, max_chars: int) -> str:
    lines = [
        f"# Context pack · {book_id}",
        "priorities: 1 system · 2 brief · 3 S/A + states · 4 lore · 5 threads · 6 chapters · 7 chunks",
    ]
    if chapter:
        lines.append(f"focus-chapter: {normalize_chapter_id(chapter)}")
    lines.append(f"max-chars: {max_chars}")
    return "\n".join(lines)


def _render_pack(header: str, sections: list[Section]) -> str:
    parts = [header.rstrip(), ""]
    for section in sections:
        parts.append(_render_section(section).rstrip())
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def _render_section(section: Section) -> str:
    lines = [f"## {section.priority} · {section.label}"]
    if section.relpath:
        lines.append(f"### {section.relpath}")
    lines.append("")
    lines.append(section.text.rstrip("\n"))
    return "\n".join(lines)


def _rel(book_path: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(book_path.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _add_file(book_path: Path, path: Path, priority: int, label: str) -> Section | None:
    if not path.is_file():
        return None
    text = _read(path)
    if not text.strip():
        return None
    return Section(priority=priority, label=label, relpath=_rel(book_path, path), text=text)


def _section_system(book_path: Path) -> list[Section]:
    section = _add_file(book_path, book_path / "06_prompts" / "system.md", 1, "system")
    return [section] if section else []


def _section_briefs(book_path: Path) -> list[Section]:
    outline = book_path / "04_outline"
    if not outline.is_dir():
        return []
    paths = sorted(
        p
        for p in outline.iterdir()
        if p.is_file() and "brief" in p.name.lower() and p.suffix.lower() in {".md", ".txt"}
    )
    out: list[Section] = []
    for path in paths:
        section = _add_file(book_path, path, 2, "outline brief")
        if section:
            out.append(section)
    return out


def _sa_character_paths(book_path: Path) -> list[Path]:
    char_dir = book_path / "02_canon" / "characters"
    if not char_dir.is_dir():
        return []
    index = load_yaml(char_dir / "_index.yaml")
    rows = index.get("characters") if isinstance(index, dict) else None
    found: list[Path] = []
    if rows:
        for row in rows:
            if not isinstance(row, dict):
                continue
            if str(row.get("tier") or "").upper() not in SA_TIERS:
                continue
            ident = row.get("id") or "character"
            fname = str(row.get("file") or f"{ident}.yaml")
            path = char_dir / fname
            if path.is_file():
                found.append(path)
        return found
    for path in sorted(char_dir.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        card = load_yaml(path)
        if str(card.get("tier") or "").upper() in SA_TIERS:
            found.append(path)
    return found


def _section_characters(book_path: Path) -> list[Section]:
    out: list[Section] = []
    for path in _sa_character_paths(book_path):
        section = _add_file(book_path, path, 3, "character S/A")
        if section:
            out.append(section)
    states = _add_file(
        book_path,
        book_path / "03_continuity" / "character_states.yaml",
        3,
        "character states",
    )
    if states:
        out.append(states)
    return out


def _section_lore(book_path: Path) -> list[Section]:
    out: list[Section] = []
    canon = book_path / "02_canon"
    for dirname in LORE_DIRS:
        folder = canon / dirname
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.yaml")):
            if path.name.startswith("_"):
                continue
            section = _add_file(book_path, path, 4, f"lore {dirname}")
            if section:
                out.append(section)
    return out


def _section_threads(book_path: Path) -> list[Section]:
    section = _add_file(
        book_path,
        book_path / "03_continuity" / "open_threads.yaml",
        5,
        "open threads",
    )
    return [section] if section else []


def _iter_manuscript_chapters(book_path: Path, book_id: str) -> list[Path]:
    chapters: list[Path] = []
    for volume in discover_volumes(book_path, book_id):
        chapters.extend(volume.get("chapters") or [])
    return chapters


def _chapter_stem(path: Path | str) -> str:
    name = Path(path).stem
    match = CHAPTER_ID_RE.match(name)
    if not match or not match.group(2):
        return name.lower()
    letter = (match.group(1) or "c").lower()
    return f"{letter}{int(match.group(2)):03d}"


def _select_nearby_chapters(
    paths: list[Path],
    chapter: str | None,
    warnings: list[str],
) -> list[Path]:
    if not paths:
        return []
    if not chapter:
        return paths[-3:]
    want = normalize_chapter_id(chapter)
    index = next((i for i, path in enumerate(paths) if _chapter_stem(path) == want), None)
    if index is None:
        warnings.append(f"chapter {want} not found in manuscript; using nearest 1–3 chapters")
        return paths[-3:]
    start = max(0, index - 1)
    return paths[start : index + 1]


def _section_chapters(
    book_path: Path,
    book_id: str,
    chapter: str | None,
    warnings: list[str],
) -> list[Section]:
    selected = _select_nearby_chapters(
        _iter_manuscript_chapters(book_path, book_id),
        chapter,
        warnings,
    )
    out: list[Section] = []
    for path in selected:
        section = _add_file(book_path, path, 6, "manuscript chapter")
        if section:
            out.append(section)
    return out


def _section_chunks(book_path: Path) -> list[Section]:
    folder = book_path / "01_sources" / "chunks"
    out: list[Section] = []
    for path in list_md_chapters(folder):
        section = _add_file(book_path, path, 7, "source chunk")
        if section:
            out.append(section)
    return out


def _normalized_chapter_paths(book_path: Path) -> list[Path]:
    chapters = book_path / "01_sources" / "normalized" / "chapters"
    found = list_md_chapters(chapters)
    if found:
        return found
    full = book_path / "01_sources" / "normalized" / "full.md"
    return [full] if full.is_file() else []


def _chunk_stem(path: Path) -> str:
    low = path.name.lower()
    if low.startswith("full"):
        return "full"
    return _chapter_stem(path)
