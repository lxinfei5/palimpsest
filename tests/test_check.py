from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from palimpsest.check import (
    check_book,
    collect_allowlist,
    find_unknown_person_names,
    is_person_like_name,
)
from palimpsest.cli import main
from palimpsest.paths import find_root


def repo_root() -> Path:
    return find_root(Path(__file__).resolve().parents[1])


def _cli_root(tmp_path: Path) -> Path:
    src = repo_root()
    shutil.copytree(src / "templates", tmp_path / "templates")
    shutil.copytree(src / "schemas", tmp_path / "schemas")
    (tmp_path / "books").mkdir()
    return tmp_path


def _copy_harbor(tmp_path: Path) -> Path:
    root = _cli_root(tmp_path)
    dest = root / "books" / "harbor-bell"
    shutil.copytree(repo_root() / "books" / "harbor-bell", dest)
    return dest


def test_harbor_bell_check_exits_0(capsys: pytest.CaptureFixture[str]):
    rc = main(["--root", str(repo_root()), "check", "harbor-bell"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "check harbor-bell all" in out
    assert "name-drift: ok" in out
    assert "open-threads: ok" in out
    assert "stale-states: ok" in out
    assert "check: ok" in out
    assert "赵铁柱" not in out


def test_harbor_bell_check_continue_volume(capsys: pytest.CaptureFixture[str]):
    rc = main(["--root", str(repo_root()), "check", "harbor-bell", "--volume", "continue"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "check harbor-bell continue" in out
    assert "check: ok" in out


def test_unknown_name_zhao_tiezhu_is_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    book = _copy_harbor(tmp_path)
    chapter = book / "05_manuscript" / "volumes" / "continue" / "c005.md"
    chapter.write_text(
        "---\nid: c005\nkind: continue\n---\n\n"
        "码头货箱侧面用炭笔写着三个字：「赵铁柱」。\n",
        encoding="utf-8",
    )
    rc = main(["--root", str(tmp_path), "check", "harbor-bell", "--volume", "continue"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "赵铁柱" in out
    assert "name-drift" in out
    assert "check: FAIL" in out


def test_unknown_name_in_sentence_is_error():
    allow = {"顾青桐", "沈晚潮", "阿麦", "灰屿", "灯塔", "鹿回头"}
    found = find_unknown_person_names("赵铁柱走在码头上。", allow)
    assert "赵铁柱" in found


def test_locations_and_canon_names_not_flagged():
    root = repo_root()
    book = root / "books" / "harbor-bell"
    allow = collect_allowlist(book)
    for name in ("顾青桐", "沈晚潮", "沈叔", "阿麦", "灰屿", "灯塔", "鹿回头", "铜铃", "港铃"):
        assert name in allow
    text = "顾青桐站在灰屿灯塔下看鹿回头，阿麦说沈叔在敲铜铃。"
    assert find_unknown_person_names(text, allow) == []
    assert is_person_like_name("赵铁柱")
    assert is_person_like_name("欧阳铁柱")
    assert not is_person_like_name("灰屿")
    assert not is_person_like_name("灯塔")
    assert not is_person_like_name("朱砂")
    assert not is_person_like_name("边角磨圆")
    assert find_unknown_person_names("青花，边角磨圆。", allow) == []


def test_stale_states_are_warning_only(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    book = _copy_harbor(tmp_path)
    states = book / "03_continuity" / "character_states.yaml"
    text = states.read_text(encoding="utf-8")
    states.write_text(text.replace("as_of_chapter: c004", "as_of_chapter: c001"), encoding="utf-8")
    rc = main(["--root", str(tmp_path), "check", "harbor-bell"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "stale-states" in out
    assert "behind latest c004" in out
    assert "check: ok" in out


def test_open_thread_missing_keyword_is_warning(tmp_path: Path):
    book = tmp_path / "books" / "drift-demo"
    (book / "00_meta").mkdir(parents=True)
    (book / "00_meta" / "book.yaml").write_text(
        "id: drift-demo\ntitle: Drift\n", encoding="utf-8"
    )
    (book / "02_canon" / "characters").mkdir(parents=True)
    (book / "02_canon" / "characters" / "_index.yaml").write_text(
        "characters: []\n", encoding="utf-8"
    )
    (book / "03_continuity").mkdir(parents=True)
    (book / "03_continuity" / "open_threads.yaml").write_text(
        "threads:\n"
        "  - id: th-x\n"
        "    title: 独角兽密室\n"
        "    status: open\n"
        "    summary: 密室里藏着独角兽的角。\n"
        "    must_keep_on_continue: true\n",
        encoding="utf-8",
    )
    (book / "03_continuity" / "character_states.yaml").write_text(
        "as_of_chapter: c001\nstates: []\n", encoding="utf-8"
    )
    vol = book / "05_manuscript" / "volumes" / "continue"
    vol.mkdir(parents=True)
    (vol / "volume.yaml").write_text("id: continue\nkind: continue\n", encoding="utf-8")
    (vol / "c001.md").write_text(
        "---\nid: c001\nkind: continue\n---\n\n今天天气很好，海边没有异常。\n",
        encoding="utf-8",
    )
    report = check_book(book, "drift-demo", volume="continue")
    assert report.ok
    assert any("独角兽密室" in w and "open-threads" in w for w in report.warnings)


def test_unknown_volume_exits_2(capsys: pytest.CaptureFixture[str]):
    rc = main(["--root", str(repo_root()), "check", "harbor-bell", "--volume", "side-99"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "volume not found" in err
