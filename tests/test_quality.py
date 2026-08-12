from __future__ import annotations

from pathlib import Path

import pytest

from palimpsest.cli import main
from palimpsest.paths import find_root
from palimpsest.quality import (
    check_quality,
    count_chars_words,
    parse_front_matter,
    parse_length_target,
)


def repo_root() -> Path:
    return find_root(Path(__file__).resolve().parents[1])


def _continue_chapter(
    *,
    ident: str = "c010",
    kind: str = "continue",
    source_line: str = "source_after: c009",
    extra: str = "正文若干字。",
) -> str:
    return (
        "---\n"
        f"id: {ident}\n"
        f"kind: {kind}\n"
        f"{source_line}\n"
        "---\n\n"
        f"# {ident}\n\n"
        f"{extra}\n"
    )


def _session_log(chapter: str = "c010", *, headings: bool = True) -> str:
    blocks = ["# Session\n", f"- book: gate-demo\n- task: continue\n- chapter: {chapter}\n"]
    if headings:
        blocks.append(
            "\n## Input\n- brief\n\n## Actions\n- wrote chapter\n\n## Open questions\n- none\n"
        )
    return "".join(blocks)


def _mini_book(
    tmp_path: Path,
    *,
    chapter_md: str,
    chapter_name: str = "c010.md",
    session_md: str | None = _session_log(),
    brief: str | None = "- 目标字数：10–80\n",
) -> Path:
    book = tmp_path / "books" / "gate-demo"
    (book / "00_meta").mkdir(parents=True)
    (book / "00_meta" / "book.yaml").write_text(
        "id: gate-demo\ntitle: Gate\n", encoding="utf-8"
    )
    vol = book / "05_manuscript" / "volumes" / "continue"
    vol.mkdir(parents=True)
    (vol / chapter_name).write_text(chapter_md, encoding="utf-8")
    (vol / "volume.yaml").write_text("id: continue\nkind: continue\n", encoding="utf-8")
    if session_md is not None:
        sess = book / "08_sessions"
        sess.mkdir(parents=True)
        (sess / "20260813-1200-continue.md").write_text(session_md, encoding="utf-8")
    if brief is not None:
        outline = book / "04_outline"
        outline.mkdir(parents=True)
        (outline / "continue_brief.md").write_text(brief, encoding="utf-8")
    return book


def test_quality_harbor_bell_c004(capsys: pytest.CaptureFixture[str]):
    rc = main(["--root", str(repo_root()), "quality", "harbor-bell", "--chapter", "c004"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "c004" in out
    assert "quality: ok" in out
    assert "kind: continue" in out
    assert "source_after: c003" in out


def test_quality_harbor_bell_default_latest(capsys: pytest.CaptureFixture[str]):
    rc = main(["--root", str(repo_root()), "quality", "harbor-bell"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "c004" in out
    assert "quality: ok" in out


def test_quality_missing_chapter(capsys: pytest.CaptureFixture[str]):
    rc = main(["--root", str(repo_root()), "quality", "harbor-bell", "--chapter", "c999"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "missing chapter: c999" in out
    assert "quality: FAIL" in out


def test_quality_original_chapter_fails_kind(capsys: pytest.CaptureFixture[str]):
    rc = main(["--root", str(repo_root()), "quality", "harbor-bell", "--chapter", "c001"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "bad kind: original" in out


def test_quality_report_c004_fields():
    book = repo_root() / "books" / "harbor-bell"
    report = check_quality(book, "harbor-bell", chapter="c004")
    assert report.ok
    assert report.chapter_id == "c004"
    assert report.kind == "continue"
    assert report.source_field == "source_after"
    assert report.source == "c003"
    assert report.path is not None
    assert report.path.name == "c004.md"
    assert report.session_path is not None
    assert "demo-continue" in report.session_path.name
    assert report.chars == 380
    assert report.target_min == 700
    assert report.target_max == 1000
    assert any("outside brief target" in w for w in report.warnings)
    assert report.errors == []


def test_missing_front_matter_fails(tmp_path: Path):
    book = _mini_book(tmp_path, chapter_md="# c010\n\nno front matter\n")
    report = check_quality(book, "gate-demo", chapter="c010")
    assert not report.ok
    joined = " ".join(report.errors)
    assert "missing required front matter: id" in joined
    assert "missing required front matter: kind" in joined
    assert "source_after or source chapter" in joined


def test_bad_kind_fails(tmp_path: Path):
    book = _mini_book(tmp_path, chapter_md=_continue_chapter(kind="side"))
    report = check_quality(book, "gate-demo", chapter="c010")
    assert not report.ok
    assert "bad kind: side" in report.errors


def test_missing_session_is_warning(tmp_path: Path):
    book = _mini_book(tmp_path, chapter_md=_continue_chapter(), session_md=None)
    report = check_quality(book, "gate-demo")
    assert report.ok
    assert any("no session log" in w for w in report.warnings)


def test_missing_session_headings_is_warning(tmp_path: Path):
    book = _mini_book(
        tmp_path,
        chapter_md=_continue_chapter(),
        session_md=_session_log(headings=False),
    )
    report = check_quality(book, "gate-demo", chapter="c010")
    assert report.ok
    assert any("missing headings" in w for w in report.warnings)


def test_missing_brief_is_warning(tmp_path: Path):
    book = _mini_book(tmp_path, chapter_md=_continue_chapter(), brief=None)
    report = check_quality(book, "gate-demo")
    assert report.ok
    assert any("missing brief" in w for w in report.warnings)


def test_rewrite_accepts_source_chapter(tmp_path: Path):
    book = _mini_book(
        tmp_path,
        chapter_md=_continue_chapter(kind="rewrite", source_line="source: c002"),
        session_md="# Session\n- task: rewrite\n\n## Input\n## Actions\n## Open questions\n",
        brief=None,
    )
    rewrite_dir = book / "05_manuscript" / "volumes" / "rewrite"
    rewrite_dir.mkdir(parents=True)
    src = book / "05_manuscript" / "volumes" / "continue" / "c010.md"
    dest = rewrite_dir / "c010.md"
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    (rewrite_dir / "volume.yaml").write_text("id: rewrite\nkind: rewrite\n", encoding="utf-8")
    report = check_quality(book, "gate-demo", chapter="c010")
    assert report.ok
    assert report.kind == "rewrite"
    assert report.source == "c002"


def test_parse_front_matter_and_length():
    meta = parse_front_matter(_continue_chapter())
    assert meta["id"] == "c010"
    assert meta["kind"] == "continue"
    assert parse_length_target("- 目标字数：700–1000\n") == (700, 1000)
    assert parse_length_target("字数：800\n") == (800, 800)
    assert parse_length_target("no target") is None
    chars, words = count_chars_words(_continue_chapter(extra="甲乙丙 hello"))
    assert chars > 0
    assert words >= 4


def test_quality_registered_in_help(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "quality" in capsys.readouterr().out
