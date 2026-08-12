from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from palimpsest.cli import main
from palimpsest.export import register_cli
from palimpsest.paths import find_root


def repo_root() -> Path:
    return find_root(Path(__file__).resolve().parents[1])


def harbor() -> Path:
    return repo_root() / "books" / "harbor-bell"


def test_register_cli_exported():
    assert callable(register_cli)


def test_export_help_lists_subcommands(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit) as exc:
        main(["export", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "st" in out
    assert "epub" in out


def test_export_st_harbor_bell():
    rc = main(["--root", str(repo_root()), "export", "st", "harbor-bell"])
    assert rc == 0

    lore_path = harbor() / "07_export" / "st" / "harbor-bell-lore.json"
    writer_path = harbor() / "07_export" / "st" / "harbor-bell-writer.json"
    lore = json.loads(lore_path.read_text(encoding="utf-8"))
    writer = json.loads(writer_path.read_text(encoding="utf-8"))

    entries = lore["entries"]
    assert isinstance(entries, dict) and entries

    found_shen = []
    for entry in entries.values():
        keys = [str(k) for k in (entry.get("key") or [])]
        if "沈晚潮" in keys or "shen-wanchao" in keys:
            found_shen.append(entry)
    assert found_shen, "lore must key 沈晚潮 or shen-wanchao"
    assert found_shen[0]["constant"] is True
    assert found_shen[0]["order"] >= 100

    a_mai = [
        e
        for e in entries.values()
        if "阿麦" in [str(k) for k in (e.get("key") or [])] or "a-mai" in [str(k) for k in (e.get("key") or [])]
    ]
    assert a_mai
    assert a_mai[0]["constant"] is False
    assert a_mai[0]["selective"] is True

    style = [e for e in entries.values() if e.get("comment") == "style"]
    assert style and style[0]["constant"] is True

    assert writer["spec"] == "chara_card_v2"
    assert writer["spec_version"] == "2.0"
    data = writer["data"]
    assert data["extensions"]["world"] == "harbor-bell-lore"
    assert "客房没有" in data["mes_example"]

    dumped = lore_path.read_text(encoding="utf-8") + writer_path.read_text(encoding="utf-8")
    assert "鞋底踩到湿木头，发出细而空的响" not in dumped
    assert "干净得像被刀刮过" not in dumped
    assert "01_sources" not in dumped
    assert "harbor-bell.txt" not in dumped


def test_export_epub_original():
    rc = main(
        [
            "--root",
            str(repo_root()),
            "export",
            "epub",
            "harbor-bell",
            "--volume",
            "original",
        ]
    )
    assert rc == 0

    path = harbor() / "07_export" / "epub" / "harbor-bell-original.epub"
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        assert names[0] == "mimetype"
        assert zf.read("mimetype") == b"application/epub+zip"
        assert zf.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
        assert "META-INF/container.xml" in names
        blob = "\n".join(
            zf.read(name).decode("utf-8")
            for name in names
            if name.endswith((".xhtml", ".html", ".ncx", ".opf", ".xml"))
        )
        assert "雾来之前" in blob
        assert "kind: original" not in blob
        assert "---" not in blob.split("雾来之前", 1)[0][-80:]


def test_export_unknown_volume():
    rc = main(
        [
            "--root",
            str(repo_root()),
            "export",
            "epub",
            "harbor-bell",
            "--volume",
            "does-not-exist",
        ]
    )
    assert rc == 2
