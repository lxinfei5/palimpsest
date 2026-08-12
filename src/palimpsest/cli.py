"""Palimpsest command line."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from palimpsest import __version__
from palimpsest.books import create_book, iter_books, require_book
from palimpsest.paths import find_root
from palimpsest.plugins import register_commands
from palimpsest.validate import validate_book


def _root(args: argparse.Namespace) -> Path:
    return find_root(getattr(args, "root", None))


def cmd_new(args: argparse.Namespace) -> int:
    dest = create_book(_root(args), args.book_id, args.title)
    print(f"created {dest}")
    print(f"next: copy source text into {dest / '01_sources' / 'raw'}")
    print(f'      then ask an agent: 解析 books/{args.book_id}，执行 ingest + parse-characters')
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    books = iter_books(_root(args))
    if not books:
        print("no books yet. try: palimpsest new my-book")
        return 0
    width = max(len(b["id"]) for b in books)
    for book in books:
        print(f"{book['id']:<{width}}  {book['title']}  [{book['status']}]")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    root = _root(args)
    targets = [args.book_id] if args.book_id else [b["id"] for b in iter_books(root)]
    if not targets:
        print("no books to validate")
        return 0
    failed = 0
    for book_id in targets:
        path = require_book(root, book_id)
        errors = validate_book(path)
        if errors:
            failed += 1
            print(f"{book_id}: FAIL")
            for err in errors:
                print(f"  - {err}")
        else:
            print(f"{book_id}: ok")
    return 1 if failed else 0


def cmd_path(args: argparse.Namespace) -> int:
    print(require_book(_root(args), args.book_id))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from palimpsest.reader.server import serve

    serve(_root(args), host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="palimpsest",
        description="Palimpsest · 叠简 — agent-native novel workshop",
    )
    parser.add_argument("--root", help="repository root (or PALIMPSEST_ROOT)")
    parser.add_argument("--version", action="version", version=f"palimpsest {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new", help="create a book sandbox from the template")
    p_new.add_argument("book_id", help="lowercase-digits-hyphens, e.g. harbor-bell")
    p_new.add_argument("--title", help="display title")
    p_new.set_defaults(func=cmd_new)

    p_list = sub.add_parser("list", help="list books")
    p_list.set_defaults(func=cmd_list)

    p_val = sub.add_parser("validate", help="check book structure")
    p_val.add_argument("book_id", nargs="?", help="omit to validate every book")
    p_val.set_defaults(func=cmd_validate)

    p_path = sub.add_parser("path", help="print a book's directory")
    p_path.add_argument("book_id")
    p_path.set_defaults(func=cmd_path)

    p_serve = sub.add_parser("serve", help="local manuscript reader")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8765)
    p_serve.set_defaults(func=cmd_serve)

    register_commands(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
