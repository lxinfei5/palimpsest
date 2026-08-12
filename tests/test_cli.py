from __future__ import annotations

from pathlib import Path

import pytest

from palimpsest.books import create_book, iter_books
from palimpsest.cli import main
from palimpsest.paths import find_root
from palimpsest.validate import validate_book
from palimpsest.volumes import discover_volumes


def repo_root() -> Path:
    return find_root(Path(__file__).resolve().parents[1])


def test_find_root():
    root = repo_root()
    assert (root / "templates" / "book").is_dir()
    assert (root / "schemas").is_dir()


def test_demo_book_validates():
    root = repo_root()
    book = root / "books" / "harbor-bell"
    errors = validate_book(book)
    assert errors == []
    vols = discover_volumes(book, "harbor-bell")
    kinds = {v["kind"] for v in vols}
    assert "original" in kinds
    assert "continue" in kinds
    original = next(v for v in vols if v["kind"] == "original")
    assert original["chapter_count"] == 3
    cont = next(v for v in vols if v["id"] == "continue")
    assert cont["chapter_count"] == 1
    assert [v["id"] for v in vols] == ["original", "continue"]


def test_list_includes_demo():
    books = iter_books(repo_root())
    ids = {b["id"] for b in books}
    assert "harbor-bell" in ids


def test_new_book_in_temp_root(tmp_path: Path):
    src = repo_root()
    # mini root
    (tmp_path / "templates").mkdir()
    import shutil

    shutil.copytree(src / "templates" / "book", tmp_path / "templates" / "book")
    (tmp_path / "schemas").mkdir()
    (tmp_path / "books").mkdir()
    dest = create_book(tmp_path, "frost-moon", "霜月")
    assert dest.name == "frost-moon"
    yaml_text = (dest / "00_meta" / "book.yaml").read_text(encoding="utf-8")
    assert "frost-moon" in yaml_text
    assert "霜月" in yaml_text
    assert "{{" not in yaml_text
    assert validate_book(dest) == []
    # isolation: demo book is not inside tmp root
    ids = {b["id"] for b in iter_books(tmp_path)}
    assert ids == {"frost-moon"}


def test_cli_list(capsys: pytest.CaptureFixture[str]):
    rc = main(["--root", str(repo_root()), "list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "harbor-bell" in out
    assert "港铃" in out


def test_cli_validate_demo():
    rc = main(["--root", str(repo_root()), "validate", "harbor-bell"])
    assert rc == 0


def test_help_lists_core_commands(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "new" in out and "serve" in out


def test_invalid_book_id(tmp_path: Path):
    src = repo_root()
    import shutil

    shutil.copytree(src / "templates" / "book", tmp_path / "templates" / "book")
    (tmp_path / "schemas").mkdir()
    rc = main(["--root", str(tmp_path), "new", "Bad_ID"])
    assert rc == 2
