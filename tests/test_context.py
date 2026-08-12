from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from palimpsest.cli import main
from palimpsest.context import (
    CHUNK_MAX,
    CHUNK_MIN,
    CHUNK_OVERLAP,
    assemble_context,
    slice_source_text,
    write_source_chunks,
)
from palimpsest.paths import find_root


def repo_root() -> Path:
    return find_root(Path(__file__).resolve().parents[1])


def harbor_bell() -> Path:
    return repo_root() / "books" / "harbor-bell"


def test_harbor_bell_pack_contains_name_and_system():
    pack, warnings = assemble_context(harbor_bell(), "harbor-bell")
    assert "顾青桐" in pack
    assert "本书系统提示" in pack
    assert "你是小说《港铃》的续写/改写作者。" in pack
    assert not any("priorities 1–4 exceed" in w for w in warnings)


def test_small_max_chars_keeps_system():
    pack, warnings = assemble_context(harbor_bell(), "harbor-bell", max_chars=80)
    assert "本书系统提示" in pack
    assert "你是小说《港铃》的续写/改写作者。" in pack
    assert "顾青桐" in pack
    assert warnings
    assert any("priorities 1–4 exceed" in w for w in warnings)
    assert "靴筒很快灌进凉泥" not in pack


def test_truncate_from_bottom_cuts_chapter_before_system():
    needle = "靴筒很快灌进凉泥"
    full, _ = assemble_context(
        harbor_bell(), "harbor-bell", chapter="c004", max_chars=200_000
    )
    assert needle in full
    tight, warnings = assemble_context(
        harbor_bell(), "harbor-bell", chapter="c004", max_chars=80
    )
    assert "本书系统提示" in tight
    assert needle not in tight
    assert any("1–4" in w for w in warnings)


def test_chapter_flag_includes_previous():
    pack, _ = assemble_context(harbor_bell(), "harbor-bell", chapter="c004")
    assert "05_manuscript/volumes/continue/c004.md" in pack
    assert "05_manuscript/original/c003.md" in pack
    assert "退潮的路" in pack
    assert "铜铃的裂纹" in pack


def test_chunk_writer_creates_files_under_tmp_copy(tmp_path: Path):
    dest = tmp_path / "harbor-bell"
    shutil.copytree(harbor_bell(), dest)
    chunks = dest / "01_sources" / "chunks"
    if chunks.exists():
        shutil.rmtree(chunks)

    written = write_source_chunks(dest)
    assert written
    assert all(path.is_file() for path in written)
    assert (chunks / "c001.md").is_file()
    assert (chunks / "c002.md").is_file()
    assert (chunks / "c003.md").is_file()
    text = (chunks / "c001.md").read_text(encoding="utf-8")
    source = (dest / "01_sources" / "normalized" / "chapters" / "c001.md").read_text(
        encoding="utf-8"
    )
    assert text == source or text == source.rstrip("\n") + "\n"
    assert "顾青桐" in text
    assert "雾来之前" in text


def test_chunk_writer_splits_long_chapter(tmp_path: Path):
    book = tmp_path / "long-book"
    chapters = book / "01_sources" / "normalized" / "chapters"
    chapters.mkdir(parents=True)
    body = "乙" * 2500
    (chapters / "c001.md").write_text(body, encoding="utf-8")

    written = write_source_chunks(book)
    names = [path.name for path in written]
    assert names[0] == "c001.md"
    assert any(name.startswith("c001_") for name in names)
    first = (book / "01_sources" / "chunks" / "c001.md").read_text(encoding="utf-8")
    assert first.startswith("乙")
    assert CHUNK_MIN <= len(first.rstrip("\n")) <= CHUNK_MAX


def test_slice_source_text_windows_and_overlap():
    body = "甲" * 2500
    parts = slice_source_text(body)
    assert len(parts) >= 2
    assert all(len(part) <= CHUNK_MAX for part in parts)
    assert all(len(part) >= CHUNK_MIN for part in parts[:-1])
    for left, right in zip(parts, parts[1:]):
        assert left[-CHUNK_OVERLAP:] == right[:CHUNK_OVERLAP]


def test_cli_context_stdout(capsys: pytest.CaptureFixture[str]):
    rc = main(["--root", str(repo_root()), "context", "harbor-bell", "--chapter", "c004"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "顾青桐" in out
    assert "本书系统提示" in out
    assert "focus-chapter: c004" in out


def test_cli_small_max_chars_keeps_system(capsys: pytest.CaptureFixture[str]):
    rc = main(["--root", str(repo_root()), "context", "harbor-bell", "--max-chars", "100"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "本书系统提示" in captured.out
    assert "顾青桐" in captured.out
    assert "warning:" in captured.err
    assert "1–4" in captured.err


def test_cli_write_chunks_tmp_root(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    src = repo_root()
    shutil.copytree(src / "templates" / "book", tmp_path / "templates" / "book")
    (tmp_path / "schemas").mkdir()
    book = tmp_path / "books" / "harbor-bell"
    shutil.copytree(src / "books" / "harbor-bell", book)
    chunks = book / "01_sources" / "chunks"
    if chunks.exists():
        shutil.rmtree(chunks)

    rc = main(
        [
            "--root",
            str(tmp_path),
            "context",
            "harbor-bell",
            "--write-chunks",
            "--max-chars",
            "200",
        ]
    )
    assert rc == 0
    assert (chunks / "c001.md").is_file()
    captured = capsys.readouterr()
    assert "本书系统提示" in captured.out
    assert "顾青桐" in captured.out
    assert "wrote" in captured.err


def test_help_lists_context_flags(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit) as exc:
        main(["context", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--chapter" in out
    assert "--max-chars" in out
    assert "--write-chunks" in out
