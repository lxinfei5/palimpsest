"""Pack a manuscript volume into a stdlib EPUB (zip + xml)."""

from __future__ import annotations

import re
import uuid
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from palimpsest.books import load_yaml
from palimpsest.volumes import chapter_heading, resolve_volume, strip_front_matter


def export_epub(book_path: Path, book_id: str, volume_id: str | None = "original") -> Path:
    """Write `07_export/epub/<book-id>-<volume>.epub`."""
    want = volume_id or "original"
    vol = resolve_volume(book_path, book_id, want)
    if vol is None:
        raise FileNotFoundError(f"volume not found: {want}")
    chapters = list(vol.get("chapters") or [])
    if not chapters:
        raise FileNotFoundError(f"volume has no chapters: {vol.get('id')}")

    meta = load_yaml(book_path / "00_meta" / "book.yaml")
    book_title = str(meta.get("title") or book_id)
    language = str(meta.get("language") or "zh")
    vol_id = str(vol.get("id") or want)
    vol_title = str(vol.get("title") or vol_id)
    display_title = f"{book_title} · {vol_title}"
    book_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"urn:palimpsest:{book_id}:{vol_id}"))

    items: list[tuple[str, str, str, bytes]] = []
    for path in chapters:
        stem = _xml_id(path.stem)
        heading = chapter_heading(path)
        body = strip_front_matter(path.read_text(encoding="utf-8", errors="replace"))
        xhtml = _chapter_xhtml(heading, body, language)
        items.append((f"{stem}.xhtml", f"chap-{stem}", heading, xhtml.encode("utf-8")))

    out = book_path / "07_export" / "epub" / f"{book_id}-{vol_id}.epub"
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_epub(
        out,
        [
            ("mimetype", b"application/epub+zip", zipfile.ZIP_STORED),
            ("META-INF/container.xml", _container_xml().encode("utf-8"), zipfile.ZIP_DEFLATED),
            (
                "OEBPS/content.opf",
                _content_opf(book_uuid, display_title, language, items).encode("utf-8"),
                zipfile.ZIP_DEFLATED,
            ),
            (
                "OEBPS/toc.ncx",
                _toc_ncx(book_uuid, display_title, items).encode("utf-8"),
                zipfile.ZIP_DEFLATED,
            ),
            *[
                (f"OEBPS/{href}", data, zipfile.ZIP_DEFLATED)
                for href, _xid, _title, data in items
            ],
        ],
    )
    return out


def _xml_id(stem: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", stem)
    if not re.match(r"^[A-Za-z_]", cleaned):
        cleaned = "c_" + cleaned
    return cleaned


def _attr(text: str) -> str:
    return escape(text, {'"': "&quot;", "'": "&apos;"})


def _write_epub(path: Path, files: list[tuple[str, bytes, int]]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data, compress in files:
            info = zipfile.ZipInfo(filename=name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = compress
            info.create_system = 3
            info.extra = b""
            zf.writestr(info, data)


def _container_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
        "  <rootfiles>\n"
        '    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n'
        "  </rootfiles>\n"
        "</container>\n"
    )


def _content_opf(
    book_uuid: str,
    title: str,
    language: str,
    items: list[tuple[str, str, str, bytes]],
) -> str:
    manifest = ['<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>']
    spine: list[str] = []
    for href, xid, _title, _data in items:
        manifest.append(
            f'<item id="{_attr(xid)}" href="{_attr(href)}" media-type="application/xhtml+xml"/>'
        )
        spine.append(f'<itemref idref="{_attr(xid)}"/>')
    man_xml = "\n    ".join(manifest)
    spine_xml = "\n    ".join(spine)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">\n'
        '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">\n'
        f'    <dc:identifier id="BookId" opf:scheme="UUID">urn:uuid:{escape(book_uuid)}</dc:identifier>\n'
        f"    <dc:title>{escape(title)}</dc:title>\n"
        f"    <dc:language>{escape(language)}</dc:language>\n"
        "    <dc:creator>Palimpsest</dc:creator>\n"
        "  </metadata>\n"
        "  <manifest>\n"
        f"    {man_xml}\n"
        "  </manifest>\n"
        '  <spine toc="ncx">\n'
        f"    {spine_xml}\n"
        "  </spine>\n"
        "</package>\n"
    )


def _toc_ncx(
    book_uuid: str,
    title: str,
    items: list[tuple[str, str, str, bytes]],
) -> str:
    points: list[str] = []
    for index, (href, xid, heading, _data) in enumerate(items, start=1):
        points.append(
            f'    <navPoint id="nav-{_attr(xid)}" playOrder="{index}">\n'
            f"      <navLabel><text>{escape(heading)}</text></navLabel>\n"
            f'      <content src="{_attr(href)}"/>\n'
            "    </navPoint>"
        )
    nav = "\n".join(points)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
        "  <head>\n"
        f'    <meta name="dtb:uid" content="urn:uuid:{_attr(book_uuid)}"/>\n'
        '    <meta name="dtb:depth" content="1"/>\n'
        '    <meta name="dtb:totalPageCount" content="0"/>\n'
        '    <meta name="dtb:maxPageNumber" content="0"/>\n'
        "  </head>\n"
        f"  <docTitle><text>{escape(title)}</text></docTitle>\n"
        "  <navMap>\n"
        f"{nav}\n"
        "  </navMap>\n"
        "</ncx>\n"
    )


def _chapter_xhtml(title: str, markdown: str, language: str) -> str:
    body = _md_to_xhtml(markdown)
    if "<h1" not in body:
        body = f"<h1>{escape(title)}</h1>\n{body}"
    lang = _attr(language)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" '
        '"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n'
        f'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{lang}" lang="{lang}">\n'
        "<head>\n"
        f"<title>{escape(title)}</title>\n"
        '<meta http-equiv="Content-Type" content="application/xhtml+xml; charset=utf-8"/>\n'
        "</head>\n"
        f"<body>\n{body}\n</body>\n"
        "</html>\n"
    )


def _md_to_xhtml(text: str) -> str:
    parts: list[str] = []
    para: list[str] = []

    def flush() -> None:
        if not para:
            return
        inner = "<br/>\n".join(escape(line) for line in para)
        parts.append(f"<p>{inner}</p>")
        para.clear()

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        if line.startswith("#"):
            flush()
            hashes = len(line) - len(line.lstrip("#"))
            level = min(max(hashes, 1), 6)
            heading = line[hashes:].strip()
            parts.append(f"<h{level}>{escape(heading)}</h{level}>")
            continue
        para.append(line)
    flush()
    return "\n".join(parts)
