"""Continue/rewrite quality gates."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from palimpsest.books import load_yaml, require_book
from palimpsest.paths import find_root
from palimpsest.volumes import chapter_sort_key, discover_volumes, strip_front_matter

ALLOWED_KINDS = frozenset({"continue", "rewrite"})
SOURCE_FIELDS = ("source_after", "source", "source_chapter")
SESSION_HEADINGS = ("Input", "Actions", "Open questions")

CHAPTER_ID_RE = re.compile(r"^((?:c|r|s)\d+)", re.I)
LENGTH_RANGE_RE = re.compile(
    r"(?:目标字数|字数)\s*[：:]\s*(\d+)\s*[-–—~～至到]\s*(\d+)",
)
LENGTH_SINGLE_RE = re.compile(r"(?:目标字数|字数)\s*[：:]\s*(\d+)")
WORD_RE = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]")
HEADING_RES = {
    name: re.compile(rf"^#{{1,6}}\s+{re.escape(name)}\s*$", re.I | re.M)
    for name in SESSION_HEADINGS
}
TASK_LINE_RE = re.compile(r"^[-*]\s*task:\s*(\S+)", re.I | re.M)


@dataclass
class QualityReport:
    book_id: str
    chapter_id: str | None = None
    path: Path | None = None
    kind: str | None = None
    source_field: str | None = None
    source: str | None = None
    chars: int | None = None
    words: int | None = None
    target_min: int | None = None
    target_max: int | None = None
    brief_path: Path | None = None
    session_path: Path | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def register_cli(subparsers) -> None:
    p = subparsers.add_parser("quality", help="continue/rewrite quality gates")
    p.add_argument("book_id")
    p.add_argument("--chapter")
    p.set_defaults(func=cmd_quality)


def cmd_quality(args: argparse.Namespace) -> int:
    root = find_root(getattr(args, "root", None))
    book_id = args.book_id
    book = require_book(root, book_id)
    report = check_quality(book, book_id, chapter=getattr(args, "chapter", None))
    print(format_report(report))
    return 0 if report.ok else 1


def check_quality(book: Path, book_id: str, chapter: str | None = None) -> QualityReport:
    report = QualityReport(book_id=book_id)
    load_yaml(book / "00_meta" / "book.yaml")
    entries = _iter_chapters(book, book_id)

    if chapter:
        want = normalize_chapter_id(chapter)
        report.chapter_id = want
        matches = [e for e in entries if e["id"] == want]
        if not matches:
            report.errors.append(f"missing chapter: {want}")
            return report
        matches.sort(
            key=lambda e: (
                0 if e["volume_kind"] in ALLOWED_KINDS else 1,
                str(e["path"]),
            )
        )
        entry = matches[0]
    else:
        entry = _latest_continue_rewrite(entries)
        if entry is None:
            report.errors.append("missing chapter: no continue/rewrite chapter found")
            return report
        report.chapter_id = entry["id"]

    report.path = entry["path"]
    text = entry["path"].read_text(encoding="utf-8", errors="replace")
    meta = parse_front_matter(text)

    chap_id = str(meta.get("id") or "").strip()
    kind = str(meta.get("kind") or "").strip().lower()
    source_field, source = source_from_meta(meta)

    if not chap_id:
        report.errors.append("missing required front matter: id")
    elif report.chapter_id and chap_id.lower() != report.chapter_id.lower():
        report.warnings.append(
            f"front matter id {chap_id!r} != chapter {report.chapter_id!r}"
        )

    if not kind:
        report.errors.append("missing required front matter: kind")
    elif kind not in ALLOWED_KINDS:
        report.errors.append(f"bad kind: {kind}")
    else:
        report.kind = kind

    if not source:
        report.errors.append("missing required front matter: source_after or source chapter")
    else:
        report.source_field = source_field
        report.source = source

    report.chars, report.words = count_chars_words(text)
    _apply_brief(book, report, report.kind or str(entry["volume_kind"]))
    _apply_session(book, report, report.kind or str(entry["volume_kind"]))
    return report


def format_report(report: QualityReport) -> str:
    label = report.chapter_id or "?"
    lines = [f"quality {report.book_id} {label}"]
    if report.path is not None:
        lines.append(f"  file: {_display_path(report.path, report.book_id)}")
    if report.kind:
        lines.append(f"  kind: {report.kind}")
    if report.source:
        field = report.source_field or "source"
        lines.append(f"  {field}: {report.source}")
    if report.chars is not None:
        length = f"  length: {report.chars} chars / {report.words} words"
        if report.target_min is not None and report.target_max is not None:
            if report.target_min == report.target_max:
                length += f"  (brief {report.target_min})"
            else:
                length += f"  (brief {report.target_min}–{report.target_max})"
        lines.append(length)
    if report.session_path is not None:
        lines.append(f"  session: {_display_path(report.session_path, report.book_id)}")
    for item in report.errors:
        lines.append(f"  error: {item}")
    for item in report.warnings:
        lines.append(f"  warning: {item}")
    lines.append("quality: ok" if report.ok else "quality: FAIL")
    return "\n".join(lines)


def parse_front_matter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    data = yaml.safe_load(parts[1])
    return data if isinstance(data, dict) else {}


def source_from_meta(meta: dict) -> tuple[str | None, str | None]:
    for key in SOURCE_FIELDS:
        raw = meta.get(key)
        if raw is None:
            continue
        value = str(raw).strip()
        if value:
            return key, value
    return None, None


def count_chars_words(text: str) -> tuple[int, int]:
    body = strip_front_matter(text)
    chars = sum(1 for ch in body if not ch.isspace())
    words = len(WORD_RE.findall(body))
    return chars, words


def parse_length_target(text: str) -> tuple[int, int] | None:
    ranged = LENGTH_RANGE_RE.search(text)
    if ranged:
        return int(ranged.group(1)), int(ranged.group(2))
    single = LENGTH_SINGLE_RE.search(text)
    if single:
        n = int(single.group(1))
        return n, n
    return None


def normalize_chapter_id(value: str) -> str:
    raw = value.strip()
    if raw.lower().endswith(".md"):
        raw = Path(raw).name[:-3]
    match = CHAPTER_ID_RE.match(raw)
    return match.group(1).lower() if match else raw.lower()


def find_session_log(book: Path, chapter_id: str, kind: str | None = None) -> Path | None:
    sess_dir = book / "08_sessions"
    if not sess_dir.is_dir():
        return None
    by_chapter: list[Path] = []
    by_task: list[Path] = []
    chap = (chapter_id or "").lower()
    kind_l = (kind or "").lower()
    for path in sorted(p for p in sess_dir.glob("*.md") if p.name != "TEMPLATE.md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        blob = f"{path.name}\n{text}".lower()
        if chap and chap in blob:
            by_chapter.append(path)
            continue
        if _session_mentions_task(path, text, kind_l):
            by_task.append(path)
    if by_chapter:
        return by_chapter[-1]
    if by_task:
        return by_task[-1]
    return None


def session_missing_headings(text: str) -> list[str]:
    return [name for name, rx in HEADING_RES.items() if not rx.search(text)]


def _iter_chapters(book: Path, book_id: str) -> list[dict]:
    out: list[dict] = []
    for vol in discover_volumes(book, book_id):
        kind = str(vol.get("kind") or "")
        for path in vol.get("chapters") or []:
            out.append(
                {
                    "id": normalize_chapter_id(path.name),
                    "path": path,
                    "volume_id": vol.get("id"),
                    "volume_kind": kind,
                }
            )
    return out


def _latest_continue_rewrite(entries: list[dict]) -> dict | None:
    candidates = [e for e in entries if e["volume_kind"] in ALLOWED_KINDS]
    if not candidates:
        return None
    candidates.sort(key=lambda e: chapter_sort_key(e["path"].name))
    return candidates[-1]


def _brief_path(book: Path, kind: str) -> Path:
    name = "rewrite_brief.md" if kind == "rewrite" else "continue_brief.md"
    return book / "04_outline" / name


def _apply_brief(book: Path, report: QualityReport, kind: str) -> None:
    brief = _brief_path(book, kind)
    if not brief.is_file():
        report.warnings.append(f"missing brief: 04_outline/{brief.name}")
        return
    report.brief_path = brief
    target = parse_length_target(brief.read_text(encoding="utf-8", errors="replace"))
    if not target:
        report.warnings.append(f"brief has no length target: {brief.name}")
        return
    report.target_min, report.target_max = target
    if report.chars is None:
        return
    lo, hi = target
    if report.chars < lo or report.chars > hi:
        if lo == hi:
            report.warnings.append(f"char count {report.chars} outside brief target {lo}")
        else:
            report.warnings.append(f"char count {report.chars} outside brief target {lo}–{hi}")


def _apply_session(book: Path, report: QualityReport, kind: str) -> None:
    chapter_id = report.chapter_id or ""
    session = find_session_log(book, chapter_id, kind)
    if session is None:
        task = kind if kind in ALLOWED_KINDS else "continue/rewrite"
        report.warnings.append(f"no session log mentioning {chapter_id or 'chapter'} or task {task}")
        return
    report.session_path = session
    text = session.read_text(encoding="utf-8", errors="replace")
    missing = session_missing_headings(text)
    if missing:
        report.warnings.append(f"session {session.name} missing headings: {', '.join(missing)}")


def _session_mentions_task(path: Path, text: str, kind: str) -> bool:
    if not kind:
        return False
    if kind in path.name.lower():
        return True
    for match in TASK_LINE_RE.finditer(text):
        if match.group(1).split("|", 1)[0].strip().lower() == kind:
            return True
    return bool(re.search(rf"\btask:\s*{re.escape(kind)}\b", text, re.I))


def _display_path(path: Path, book_id: str) -> str:
    parts = path.parts
    if book_id in parts:
        idx = parts.index(book_id)
        return "/".join(parts[idx + 1 :])
    return str(path)
