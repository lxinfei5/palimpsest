"""Export adapters: SillyTavern world/writer cards and EPUB."""

from __future__ import annotations

import argparse
from pathlib import Path

from palimpsest.books import require_book
from palimpsest.export.epub import export_epub
from palimpsest.export.st import export_st
from palimpsest.paths import find_root


def _root(args: argparse.Namespace) -> Path:
    return find_root(getattr(args, "root", None))


def cmd_export_st(args: argparse.Namespace) -> int:
    book = require_book(_root(args), args.book_id)
    for path in export_st(book, args.book_id):
        print(f"wrote {path}")
    return 0


def cmd_export_epub(args: argparse.Namespace) -> int:
    book = require_book(_root(args), args.book_id)
    path = export_epub(book, args.book_id, args.volume)
    print(f"wrote {path}")
    return 0


def register_cli(subparsers) -> None:
    parser = subparsers.add_parser("export", help="export SillyTavern assets and EPUB")
    dest = parser.add_subparsers(dest="export_cmd", required=True)

    p_st = dest.add_parser("st", help="export SillyTavern world info and writer card")
    p_st.add_argument("book_id", help="book id, e.g. harbor-bell")
    p_st.set_defaults(func=cmd_export_st)

    p_epub = dest.add_parser("epub", help="pack a manuscript volume as EPUB")
    p_epub.add_argument("book_id", help="book id, e.g. harbor-bell")
    p_epub.add_argument(
        "--volume",
        default="original",
        help="volume id: original, continue, …",
    )
    p_epub.set_defaults(func=cmd_export_epub)
