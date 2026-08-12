"""Compile L2 canon into SillyTavern World Info and a chara_card_v2 writer card."""

from __future__ import annotations

import json
import re
from pathlib import Path

from palimpsest.books import load_yaml

CANON_KINDS = ("characters", "locations", "factions", "items", "rules", "glossary")
_TIER_RANK = {"S": 0, "A": 1, "B": 2, "C": 3}


def export_st(book_path: Path, book_id: str) -> list[Path]:
    """Write `07_export/st/<book-id>-lore.json` and `<book-id>-writer.json`."""
    meta = load_yaml(book_path / "00_meta" / "book.yaml")
    system_prompt = _load_system_prompt(book_path)
    characters = _load_characters(book_path)
    world = _load_world(book_path)

    entries: dict[str, dict] = {}
    uid = 0

    if system_prompt:
        entries[str(uid)] = _wi_entry(
            uid,
            keys=["style", "文风", str(meta.get("title") or book_id), "system"],
            comment="style",
            content=system_prompt,
            constant=True,
            selective=False,
            order=0,
        )
        uid += 1

    s_order = 100
    other_order = 50
    for card in characters:
        tier = str(card.get("tier") or "C").upper()
        if tier == "S":
            constant, selective, order = True, False, s_order
            s_order += 1
        else:
            constant, selective, order = False, True, other_order
            other_order += 1
        keys = _keys(card.get("name"), card.get("id"), card.get("aliases"))
        entries[str(uid)] = _wi_entry(
            uid,
            keys=keys,
            comment=str(card.get("id") or card.get("name") or uid),
            content=_summarize_character(card),
            constant=constant,
            selective=selective,
            order=order,
        )
        uid += 1

    lore_order = 40
    for card in world:
        keys = _keys(card.get("name"), card.get("id"), card.get("aliases"))
        entries[str(uid)] = _wi_entry(
            uid,
            keys=keys,
            comment=str(card.get("id") or card.get("name") or uid),
            content=_summarize_lore(card),
            constant=False,
            selective=True,
            order=lore_order,
        )
        lore_order += 1
        uid += 1

    extra = _continuity_entries(book_path, uid)
    entries.update(extra)

    out_dir = book_path / "07_export" / "st"
    lore_path = out_dir / f"{book_id}-lore.json"
    writer_path = out_dir / f"{book_id}-writer.json"
    _write_json(lore_path, {"entries": entries})
    _write_json(writer_path, _writer_card(book_id, meta, characters, system_prompt))
    return [lore_path, writer_path]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_system_prompt(book_path: Path) -> str:
    path = book_path / "06_prompts" / "system.md"
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    return re.sub(r"^# [^\n]*\n+", "", text).strip()


def _iter_canon_yaml(directory: Path) -> list[dict]:
    if not directory.is_dir():
        return []
    cards: list[dict] = []
    for path in sorted(directory.glob("*.y*ml")):
        if path.suffix.lower() not in {".yaml", ".yml"}:
            continue
        if path.name.startswith("_"):
            continue
        data = load_yaml(path)
        if not data:
            continue
        data.setdefault("id", path.stem)
        cards.append(data)
    return cards


def _load_characters(book_path: Path) -> list[dict]:
    cards = _iter_canon_yaml(book_path / "02_canon" / "characters")
    cards.sort(
        key=lambda c: (
            _TIER_RANK.get(str(c.get("tier") or "C").upper(), 9),
            str(c.get("id") or ""),
        )
    )
    return cards


def _load_world(book_path: Path) -> list[dict]:
    cards: list[dict] = []
    for kind in CANON_KINDS:
        if kind == "characters":
            continue
        cards.extend(_iter_canon_yaml(book_path / "02_canon" / kind))
    events_path = book_path / "02_canon" / "timeline" / "events.yaml"
    events = load_yaml(events_path)
    for ev in events.get("events") or []:
        if not isinstance(ev, dict):
            continue
        cards.append(
            {
                "id": ev.get("id") or "",
                "name": ev.get("id") or "event",
                "aliases": [ev.get("when")] if ev.get("when") else [],
                "kind": "event",
                "summary": ev.get("summary") or "",
                "details": ev.get("when") or "",
            }
        )
    return cards


def _continuity_entries(book_path: Path, start_uid: int) -> dict[str, dict]:
    out: dict[str, dict] = {}
    uid = start_uid

    states_doc = load_yaml(book_path / "03_continuity" / "character_states.yaml")
    states = [s for s in (states_doc.get("states") or []) if isinstance(s, dict)]
    if states:
        lines = [f"角色状态 as_of {states_doc.get('as_of_chapter') or '?'}"]
        keys = ["character_states", "状态"]
        for st in states:
            cid = st.get("id") or ""
            loc = st.get("location") or ""
            emo = st.get("emotional") or ""
            know = _join(st.get("knowledge"))
            inv = _join(st.get("inventory"))
            lines.append(f"- {cid}：地点 {loc}；情绪 {emo}；已知 {know}；随身 {inv}")
            if cid:
                keys.append(str(cid))
        out[str(uid)] = _wi_entry(
            uid,
            keys=keys,
            comment="character_states",
            content="\n".join(lines),
            constant=False,
            selective=True,
            order=20,
        )
        uid += 1

    threads_doc = load_yaml(book_path / "03_continuity" / "open_threads.yaml")
    threads = [t for t in (threads_doc.get("threads") or []) if isinstance(t, dict)]
    if threads:
        lines = ["未收束线索"]
        keys = ["open_threads", "线索"]
        for th in threads:
            title = th.get("title") or th.get("id") or ""
            summary = th.get("summary") or ""
            status = th.get("status") or ""
            lines.append(f"- {title} [{status}]：{summary}")
            if th.get("id"):
                keys.append(str(th["id"]))
            if title:
                keys.append(str(title))
        out[str(uid)] = _wi_entry(
            uid,
            keys=keys,
            comment="open_threads",
            content="\n".join(lines),
            constant=False,
            selective=True,
            order=21,
        )
    return out


def _wi_entry(
    uid: int,
    keys: list[str],
    comment: str,
    content: str,
    *,
    constant: bool,
    selective: bool,
    order: int,
) -> dict:
    return {
        "uid": uid,
        "key": keys,
        "keysecondary": [],
        "comment": comment,
        "content": content.strip(),
        "constant": constant,
        "selective": selective,
        "order": order,
        "position": 0,
        "disable": False,
        "depth": 4,
        "probability": 100,
        "useProbability": True,
        "group": "",
        "sticky": 0,
        "cooldown": 0,
        "delay": 0,
    }


def _keys(*parts) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if part is None:
            continue
        items = part if isinstance(part, list) else [part]
        for item in items:
            text = str(item).strip()
            if text and text not in seen:
                seen.add(text)
                out.append(text)
    return out


def _join(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "、".join(str(x).strip() for x in value if x not in (None, ""))
    return str(value).strip()


def _personality_text(pers) -> str:
    if not isinstance(pers, dict):
        return str(pers or "").strip()
    bits: list[str] = []
    traits = _join(pers.get("traits"))
    if traits:
        bits.append(f"特质：{traits}")
    if pers.get("speech_style"):
        bits.append(f"说话语气：{pers['speech_style']}")
    values = _join(pers.get("values"))
    if values:
        bits.append(f"看重：{values}")
    flaws = _join(pers.get("flaws"))
    if flaws:
        bits.append(f"缺陷：{flaws}")
    taboo = _join(pers.get("taboo"))
    if taboo:
        bits.append(f"禁忌：{taboo}")
    return "；".join(bits)


def _goals_text(goals) -> str:
    if not isinstance(goals, dict):
        return str(goals or "").strip()
    bits: list[str] = []
    short = _join(goals.get("short_term"))
    long_term = _join(goals.get("long_term"))
    if short:
        bits.append(f"近期：{short}")
    if long_term:
        bits.append(f"长远：{long_term}")
    return "；".join(bits)


def _rels_text(rels) -> str:
    if not isinstance(rels, list):
        return ""
    bits: list[str] = []
    for rel in rels:
        if not isinstance(rel, dict):
            continue
        chunk = " ".join(
            str(x).strip()
            for x in (rel.get("target"), rel.get("type"), rel.get("note"))
            if x
        )
        if chunk:
            bits.append(chunk)
    return "；".join(bits)


def _summarize_character(card: dict) -> str:
    lines = [f"{card.get('name') or card.get('id')}（{card.get('id')}）"]
    if card.get("summary"):
        lines.append(f"摘要：{card['summary']}")
    if card.get("appearance"):
        lines.append(f"外貌：{card['appearance']}")
    pers = _personality_text(card.get("personality"))
    if pers:
        lines.append(f"性格：{pers}")
    goals = _goals_text(card.get("goals"))
    if goals:
        lines.append(f"目标：{goals}")
    rels = _rels_text(card.get("relationships"))
    if rels:
        lines.append(f"关系：{rels}")
    return "\n".join(lines)


def _summarize_lore(card: dict) -> str:
    lines = [str(card.get("name") or card.get("id") or "")]
    if card.get("kind"):
        lines.append(f"类型：{card['kind']}")
    if card.get("summary"):
        lines.append(f"摘要：{card['summary']}")
    if card.get("details"):
        lines.append(f"细节：{card['details']}")
    related = _join(card.get("related"))
    if related:
        lines.append(f"相关：{related}")
    return "\n".join(line for line in lines if line)


def _writer_card(
    book_id: str,
    meta: dict,
    characters: list[dict],
    system_prompt: str,
) -> dict:
    title = str(meta.get("title") or book_id)
    synopsis = str(meta.get("synopsis") or "")
    defaults = meta.get("defaults") if isinstance(meta.get("defaults"), dict) else {}
    personality = "；".join(
        str(x)
        for x in (
            defaults.get("style_notes"),
            defaults.get("pov"),
            defaults.get("tense"),
        )
        if x
    )

    examples: list[str] = []
    for card in characters:
        name = card.get("name") or card.get("id")
        for sample in card.get("voice_samples") or []:
            if not isinstance(sample, dict):
                continue
            quote = str(sample.get("quote") or "").strip()
            if quote:
                examples.append(f"{name}: {quote}")
    mes_example = "<START>\n" + "\n".join(examples) if examples else ""

    tags: list[str] = []
    for field in ("tags", "genre"):
        val = meta.get(field) or []
        if isinstance(val, list):
            tags.extend(str(x) for x in val if x)

    return {
        "spec": "chara_card_v2",
        "spec_version": "2.0",
        "data": {
            "name": f"{title}·写作卡",
            "description": synopsis,
            "personality": personality,
            "scenario": synopsis,
            "first_mes": (
                f"准备续写《{title}》。只使用本书正典与任务书；"
                "对话短，少解释，以物件与规矩推动。"
            ),
            "mes_example": mes_example,
            "post_history_instructions": system_prompt,
            "tags": tags,
            "creator": "Palimpsest",
            "extensions": {"world": f"{book_id}-lore"},
        },
    }
