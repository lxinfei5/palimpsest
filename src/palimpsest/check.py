"""Continuity and name-drift checks (P2-D)."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path

from palimpsest.books import load_yaml, require_book
from palimpsest.paths import find_root
from palimpsest.volumes import chapter_sort_key, discover_volumes, strip_front_matter

# Classic 百家姓 (simplified) plus a few novel-common compounds.
_SURNAMES_TEXT = (
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
    "戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳酆鲍史唐"
    "费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄"
    "和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝董梁"
    "杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍"
    "虞万支柯昝管卢莫经房裘缪干解应宗丁宣贲邓郁单杭洪包诸左石崔吉钮龚"
    "程嵇邢滑裴陆荣翁荀羊於惠甄曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓"
    "牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘钭厉戎祖武符刘景詹束龙"
    "叶幸司韶郜黎蓟薄印宿白怀蒲邰从鄂索咸籍赖卓蔺屠蒙池乔阴胥能苍双"
    "闻莘党翟谭贡劳逄姬申扶堵冉宰郦雍郤璩桑桂濮牛寿通边扈燕冀郏浦尚农"
    "温别庄晏柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖庾终暨居衡步都耿满弘"
    "匡国文寇广禄阙东欧殳沃利蔚越夔隆师巩厍聂晁勾敖融冷訾辛阚那简饶空"
    "曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖益桓公晋楚闫法汝鄢涂钦"
    "岳帅缑亢况郈有琴商牟佘佴伯赏墨哈谯笪年爱阳佟第五言福鹿"
)
SINGLE_SURNAMES = frozenset(_SURNAMES_TEXT)
COMPOUND_SURNAMES = frozenset(
    {
        "万俟",
        "司马",
        "上官",
        "欧阳",
        "夏侯",
        "诸葛",
        "闻人",
        "东方",
        "赫连",
        "皇甫",
        "尉迟",
        "公羊",
        "澹台",
        "公冶",
        "宗政",
        "濮阳",
        "淳于",
        "单于",
        "太叔",
        "申屠",
        "公孙",
        "仲孙",
        "轩辕",
        "令狐",
        "钟离",
        "宇文",
        "长孙",
        "慕容",
        "司徒",
        "司空",
        "司寇",
        "子车",
        "颛孙",
        "端木",
        "巫马",
        "公西",
        "漆雕",
        "乐正",
        "壤驷",
        "公良",
        "拓跋",
        "夹谷",
        "宰父",
        "谷梁",
        "段干",
        "百里",
        "东郭",
        "南门",
        "呼延",
        "羊舌",
        "微生",
        "梁丘",
        "左丘",
        "东门",
        "西门",
        "南宫",
        "独孤",
        "太史",
        "南荣",
        "亓官",
        "第五",
    }
)

# Given-name characters that almost never appear in a real personal name.
# Motion/speech verbs keep 「赵铁柱走」 from being read as one given name.
_FORBIDDEN_GIVEN = frozenset(
    "的了着过在是有和与把被从到也就都还又很不没得地而或及等"
    "这那什么么上下里外中前后边间处内"
    "出发入开关来去起回"
    "走跑站坐看望听想说问道答喊叫笑哭跪"
    "吗呢吧啊呀哇"
    "才并却既"
)

# Two-character common nouns that start with a surname (avoid 朱砂 etc.).
_NOUN_PREFIXES = frozenset(
    {
        "朱砂",
        "白线",
        "白天",
        "白日",
        "白盐",
        "石头",
        "石阶",
        "石级",
        "石桥",
        "门口",
        "门前",
        "门外",
        "门槛",
        "门开",
        "门关",
        "黄金",
        "青山",
        "青石",
        "清水",
        "长江",
        "江南",
        "风雨",
        "风声",
        "山水",
        "水流",
        "马车",
        "马匹",
        "金光",
        "金线",
        "木头",
        "木门",
        "客房",
        "堆房",
        "海水",
        "海图",
    }
)

_NAME_NEXT = frozenset(
    "说问道答喊叫笑哭走跑站坐看望听想拿举伸收回点摇跪跟把将被给对向往从在"
    "和与同的了着过叔伯爷姐哥妹婆奶公"
)
_NAME_PREV = frozenset("叫姓是见与和跟同对把被给为有")

_THREAD_STOP = frozenset(
    {
        "是否",
        "存在",
        "稳定",
        "那个",
        "某个",
        "一次",
        "上次",
        "那次",
        "不愿",
        "说出",
        "拒绝",
        "说明",
        "证实",
        "可见",
        "结尾",
        "强调",
        "暂时",
        "透露",
        "记得",
        "笔记",
        "以及",
        "或者",
        "但是",
        "如果",
        "因为",
        "所以",
        "这个",
        "我们",
        "他们",
        "什么",
        "没有",
        "不是",
        "还是",
        "已经",
        "可以",
        "一个",
        "一种",
        "关于",
        "之后",
        "之前",
        "时候",
        "地方",
        "东西",
        "问题",
        "情况",
        "只是",
        "先走",
        "哪一次",
        "守灯人",
        "不愿说",
    }
)

_RE_CJK = re.compile(r"[\u4e00-\u9fff]")
_RE_CJK_RUN = re.compile(r"[\u4e00-\u9fff]+")
_RE_CJK_TOKEN = re.compile(r"[\u4e00-\u9fff]{2,4}")
_RE_LATIN_NAME = re.compile(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})+\b")
_RE_QUOTED = re.compile(r"「([^」]{2,24})」|“([^”]{2,24})”|\"([^\"]{2,24})\"")
_RE_CHAPTER_ID = re.compile(r"^((?:c|r|s)\d+)", re.I)
_LORE_DIRS = ("locations", "items", "factions", "glossary", "rules")


@dataclass
class CheckReport:
    book_id: str
    volume: str | None = None
    allowlist_size: int = 0
    chapters_scanned: int = 0
    latest_chapter: str | None = None
    thread_chapter: str | None = None
    as_of_chapter: str | None = None
    threads_checked: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def register_cli(subparsers) -> None:
    parser = subparsers.add_parser("check", help="continuity and name-drift checks")
    parser.add_argument("book_id", help="book sandbox id, e.g. harbor-bell")
    parser.add_argument(
        "--volume",
        help="limit scan to a volume id (e.g. continue); default: all volumes",
    )
    parser.set_defaults(func=cmd_check)


def cmd_check(args: argparse.Namespace) -> int:
    root = find_root(getattr(args, "root", None))
    book = require_book(root, args.book_id)
    report = check_book(book, args.book_id, volume=getattr(args, "volume", None))
    print(format_report(report))
    return 1 if report.errors else 0


def check_book(book: Path, book_id: str, volume: str | None = None) -> CheckReport:
    report = CheckReport(book_id=book_id, volume=volume)
    volumes = discover_volumes(book, book_id)
    scoped = _volumes_for_scan(volumes, volume)
    allow = collect_allowlist(book)
    report.allowlist_size = len(allow)

    _check_name_drift(report, scoped, allow)
    _check_open_threads(report, book, volumes, volume, allow)
    _check_stale_states(report, book, scoped)
    return report


def format_report(report: CheckReport) -> str:
    scope = report.volume or "all"
    lines = [f"check {report.book_id} {scope}"]
    name_errs = [e for e in report.errors if e.startswith("name-drift")]
    thread_warns = [w for w in report.warnings if w.startswith("open-threads")]
    stale_warns = [w for w in report.warnings if w.startswith("stale-states")]
    other_err = [e for e in report.errors if not e.startswith("name-drift")]
    other_warn = [
        w
        for w in report.warnings
        if not w.startswith("open-threads") and not w.startswith("stale-states")
    ]

    if name_errs:
        lines.append("  name-drift: FAIL")
        for item in name_errs:
            lines.append(f"    error: {item}")
    else:
        lines.append(
            f"  name-drift: ok ({report.chapters_scanned} chapter(s), "
            f"{report.allowlist_size} allowlisted names)"
        )

    if thread_warns:
        lines.append("  open-threads: warning")
        for item in thread_warns:
            lines.append(f"    warning: {item}")
    else:
        where = report.thread_chapter or "n/a"
        lines.append(f"  open-threads: ok ({report.threads_checked} must-keep, latest {where})")

    if stale_warns:
        lines.append("  stale-states: warning")
        for item in stale_warns:
            lines.append(f"    warning: {item}")
    elif report.as_of_chapter:
        latest = report.latest_chapter or "n/a"
        lines.append(f"  stale-states: ok (as_of_chapter={report.as_of_chapter}, latest {latest})")
    else:
        lines.append("  stale-states: ok (no as_of_chapter)")

    for item in other_err:
        lines.append(f"  error: {item}")
    for item in other_warn:
        lines.append(f"  warning: {item}")

    lines.append("check: ok" if report.ok else "check: FAIL")
    return "\n".join(lines)


def collect_allowlist(book: Path) -> set[str]:
    names: set[str] = set()
    chars_dir = book / "02_canon" / "characters"
    index = load_yaml(chars_dir / "_index.yaml")
    for row in index.get("characters") or []:
        if isinstance(row, dict):
            _add_name(names, row.get("name"))
            _add_name(names, row.get("aliases"))

    if chars_dir.is_dir():
        for path in sorted(chars_dir.glob("*.yaml")):
            data = load_yaml(path)
            if path.name == "_extras.yaml":
                for row in data.get("extras") or []:
                    if isinstance(row, dict):
                        _add_name(names, row.get("name"))
                continue
            if path.name.startswith("_"):
                continue
            _add_name(names, data.get("name"))
            _add_name(names, data.get("aliases"))

    for folder in _LORE_DIRS:
        lore_dir = book / "02_canon" / folder
        if not lore_dir.is_dir():
            continue
        for path in sorted(lore_dir.glob("*.yaml")):
            data = load_yaml(path)
            _add_name(names, data.get("name"))
            _add_name(names, data.get("aliases"))
            _add_name(names, data.get("title"))

    expanded = set(names)
    for name in names:
        if not re.fullmatch(r"[\u4e00-\u9fff]{3,4}", name):
            continue
        if name[:2] in COMPOUND_SURNAMES and len(name) > 2:
            _add_name(expanded, name[2:])
        elif name[0] in SINGLE_SURNAMES:
            _add_name(expanded, name[1:])
    return {n for n in expanded if n}


def is_person_like_name(token: str) -> bool:
    """True for a conservative person-name candidate (CJK 3–4 or Latin First Last)."""
    text = token.strip()
    if not text:
        return False
    if _RE_LATIN_NAME.fullmatch(text):
        return True
    if not re.fullmatch(r"[\u4e00-\u9fff]{2,4}", text):
        return False
    if text[:2] in _NOUN_PREFIXES:
        return False
    if text.startswith("阿") and 2 <= len(text) <= 3:
        return not _has_forbidden_given(text[1:])
    # 4-char Han names are almost always compound-surname + given (欧阳修文).
    if len(text) == 4 and text[:2] in COMPOUND_SURNAMES:
        return not _has_forbidden_given(text[2:])
    if len(text) == 3 and text[:2] in COMPOUND_SURNAMES:
        return not _has_forbidden_given(text[2:])
    if len(text) == 3 and text[0] in SINGLE_SURNAMES:
        return not _has_forbidden_given(text[1:])
    return False


def find_unknown_person_names(text: str, allow: set[str]) -> list[str]:
    """Return unknown person-like tokens (full CJK names and Latin First Last)."""
    masked = _mask_allowlist(text, allow)
    found: list[str] = []
    seen: set[str] = set()

    def remember(token: str) -> None:
        if token in seen or token in allow:
            return
        seen.add(token)
        found.append(token)

    for match in _RE_CJK_RUN.finditer(masked):
        run = match.group()
        start = match.start()
        if 3 <= len(run) <= 4 and _is_flaggable_cjk_name(run):
            remember(run)
            continue
        index = 0
        while index < len(run):
            hit = False
            for length in (4, 3):
                if index + length > len(run):
                    continue
                token = run[index : index + length]
                if not _is_flaggable_cjk_name(token):
                    continue
                prev = masked[start + index - 1] if start + index else ""
                nxt = masked[start + index + length] if start + index + length < len(masked) else ""
                if _has_name_context(prev, nxt):
                    remember(token)
                    index += length
                    hit = True
                    break
            if not hit:
                index += 1

    allow_l = {item.lower() for item in allow}
    for match in _RE_LATIN_NAME.finditer(masked):
        token = match.group()
        if token.lower() not in allow_l:
            remember(token)
    return found


def thread_keywords(title: str, summary: str, allow: set[str]) -> list[str]:
    blob = f"{title or ''} {summary or ''}".strip()
    if not blob:
        return []
    keys: list[str] = []

    for match in _RE_QUOTED.finditer(blob):
        quoted = next((g for g in match.groups() if g), "")
        if quoted and quoted not in _THREAD_STOP:
            keys.append(quoted.strip())

    for name in sorted(allow, key=len, reverse=True):
        if len(name) >= 2 and name in blob:
            keys.append(name)

    for match in _RE_CJK_TOKEN.finditer(blob):
        token = match.group()
        if token in _THREAD_STOP or token[:2] in _THREAD_STOP:
            continue
        if _has_forbidden_given(token) and token not in allow:
            continue
        keys.append(token)

    uniq: list[str] = []
    seen: set[str] = set()
    for key in sorted(keys, key=len, reverse=True):
        if key in seen:
            continue
        seen.add(key)
        uniq.append(key)
    return uniq


def _check_name_drift(
    report: CheckReport,
    volumes: list[dict],
    allow: set[str],
) -> None:
    for vol in volumes:
        for path in vol.get("chapters") or []:
            report.chapters_scanned += 1
            body = strip_front_matter(path.read_text(encoding="utf-8", errors="replace"))
            for name in find_unknown_person_names(body, allow):
                rel = _display_path(path, report.book_id)
                report.errors.append(f"name-drift: unknown person-like name 「{name}」 in {rel}")


def _check_open_threads(
    report: CheckReport,
    book: Path,
    all_volumes: list[dict],
    volume: str | None,
    allow: set[str],
) -> None:
    data = load_yaml(book / "03_continuity" / "open_threads.yaml")
    threads = [row for row in (data.get("threads") or []) if isinstance(row, dict)]
    must = [
        row
        for row in threads
        if _truthy(row.get("must_keep_on_continue")) and str(row.get("status") or "").lower() == "open"
    ]
    report.threads_checked = len(must)
    if not must:
        return

    scope = _thread_volumes(all_volumes, volume)
    latest = _latest_chapter(scope)
    if latest is None:
        report.warnings.append("open-threads: no chapter available to scan for must-keep threads")
        return
    _vol, path = latest
    report.thread_chapter = _chapter_id(path)
    text = strip_front_matter(path.read_text(encoding="utf-8", errors="replace"))
    rel = _display_path(path, report.book_id)

    for row in must:
        tid = str(row.get("id") or "?").strip() or "?"
        title = str(row.get("title") or tid).strip()
        summary = str(row.get("summary") or "")
        keywords = thread_keywords(title, summary, allow)
        if keywords and any(key in text for key in keywords):
            continue
        report.warnings.append(
            f"open-threads: {tid} 「{title}」 not mentioned in latest {rel}"
        )


def _check_stale_states(report: CheckReport, book: Path, volumes: list[dict]) -> None:
    data = load_yaml(book / "03_continuity" / "character_states.yaml")
    as_of = data.get("as_of_chapter")
    if as_of:
        report.as_of_chapter = str(as_of).strip()
    latest = _latest_chapter(volumes)
    if latest is None:
        return
    _vol, path = latest
    latest_id = _chapter_id(path)
    report.latest_chapter = latest_id
    if not report.as_of_chapter:
        return
    if chapter_sort_key(report.as_of_chapter) < chapter_sort_key(latest_id):
        report.warnings.append(
            f"stale-states: as_of_chapter={report.as_of_chapter} is behind latest {latest_id}"
        )


def _volumes_for_scan(volumes: list[dict], volume_id: str | None) -> list[dict]:
    if not volume_id:
        return list(volumes)
    picked = [vol for vol in volumes if str(vol.get("id")) == volume_id]
    if not picked:
        raise ValueError(f"volume not found: {volume_id}")
    return picked


def _thread_volumes(volumes: list[dict], volume_id: str | None) -> list[dict]:
    if volume_id:
        return _volumes_for_scan(volumes, volume_id)
    cont = [vol for vol in volumes if vol.get("kind") == "continue" or vol.get("id") == "continue"]
    return cont or list(volumes)


def _latest_chapter(volumes: list[dict]) -> tuple[dict, Path] | None:
    best: tuple[dict, Path] | None = None
    best_key: tuple | None = None
    for vol in volumes:
        for path in vol.get("chapters") or []:
            key = chapter_sort_key(path.name)
            if best_key is None or key > best_key:
                best_key = key
                best = (vol, path)
    return best


def _chapter_id(path: Path) -> str:
    stem = path.stem
    match = _RE_CHAPTER_ID.match(stem)
    return match.group(1).lower() if match else stem


def _display_path(path: Path, book_id: str) -> str:
    parts = path.parts
    if book_id in parts:
        return "/".join(parts[parts.index(book_id) + 1 :])
    return str(path)


def _add_name(names: set[str], value: object) -> None:
    if value is None:
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            _add_name(names, item)
        return
    text = str(value).strip()
    if text:
        names.add(text)


def _has_forbidden_given(given: str) -> bool:
    return any(ch in _FORBIDDEN_GIVEN for ch in given)


def _is_flaggable_cjk_name(token: str) -> bool:
    if len(token) < 3 or len(token) > 4:
        return False
    if token[:2] in _NOUN_PREFIXES:
        return False
    return is_person_like_name(token)


def _has_name_context(prev: str, nxt: str) -> bool:
    if not prev or not _RE_CJK.match(prev) or prev in _NAME_PREV:
        if not nxt or not _RE_CJK.match(nxt) or nxt in _NAME_NEXT:
            return True
    return False


def _mask_allowlist(text: str, allow: set[str]) -> str:
    masked = text
    for name in sorted(allow, key=len, reverse=True):
        if name:
            masked = masked.replace(name, " " * len(name))
    return masked


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
