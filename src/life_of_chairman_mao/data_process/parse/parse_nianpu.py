"""parse_nianpu.py — Batch parser for 毛泽东年谱 annual MD files.

Reads all *.md from INPUT_DIR, extracts structured events, writes JSON to OUTPUT_DIR.
Skips files where the output JSON already exists.
"""

import json
import re
from pathlib import Path

MAO_BIRTH = 1893

INPUT_DIR = Path("/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/毛泽东年谱/textin/md")
OUTPUT_DIR = Path("/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/毛泽东年谱/textin/json")

# ── Helpers ───────────────────────────────────────────────────────────────────

def norm_fn(s):
    """Normalize footnote markers 〔N〕/（N）→[N]."""
    return re.sub(r"[〔（](\d+)[〕）]", r"[\1]", s)

def strip_bold(s):
    return re.sub(r"\*\*", "", s)

# Footnote definition: normalized line that starts with [N]
FNDEF_RE = re.compile(r"^\[(\d+)\]\s*(.+)", re.DOTALL)

QUALIFIER_MAP = {
    "初": "01", "上旬": "01",
    "中旬": "11",
    "下旬": "21",
    "末": "28",
}
SEASON_MAP = {
    "春": ("03", "01"), "夏": ("06", "01"),
    "秋": ("09", "01"), "冬": ("12", "01"),
}
MAX_DAYS = {1:31, 2:28, 3:31, 4:30, 5:31, 6:30,
            7:31, 8:31, 9:30, 10:31, 11:30, 12:31}


def parse_date(text):
    """Parse date prefix from paragraph text (bold already stripped).

    Returns (month, day, rest, is_same_day, is_same_month) or None.
    """
    text = text.strip()

    # 同日
    if text.startswith("同日"):
        return "SAME", "SAME", text[2:].lstrip(), True, False

    # 同月
    if text.startswith("同月"):
        return "SAME_MONTH", None, text[2:].lstrip(), False, True

    # Seasons (春/夏/秋/冬)
    for s, (mo, d) in SEASON_MAP.items():
        if text.startswith(s):
            return mo, d, text[1:].lstrip(), False, False

    # M月D日[range/连续]
    pat = re.match(
        r"^(\d{1,2})月(\d{1,2})日(?:[-—至、，,]\d{1,2}日)?\s*(.*)",
        text, re.DOTALL)
    if pat:
        return (f"{int(pat.group(1)):02d}",
                f"{int(pat.group(2)):02d}",
                pat.group(3), False, False)

    # M月[qualifier]
    pat = re.match(
        r"^(\d{1,2})月(初|上旬|中旬|下旬|末)?\s*(.*)",
        text, re.DOTALL)
    if pat:
        return (f"{int(pat.group(1)):02d}",
                QUALIFIER_MAP.get(pat.group(2)),  # None if no qualifier
                pat.group(3), False, False)

    return None


def next_day_str(month_str, day_str):
    """Return day + 1, capped at month max."""
    m, d = int(month_str), int(day_str) + 1
    return f"{min(d, MAX_DAYS.get(m, 30)):02d}"


def renumber_body(body):
    """Replace [N] markers sequentially [1],[2],... in order of appearance."""
    counter = [0]
    def r(m):
        counter[0] += 1
        return f"[{counter[0]}]"
    return re.sub(r"\[\d+\]", r, body)


def extract_year_from_stem(stem):
    """Extract the primary (first) year from a filename stem.

    '1904年'          -> 1904
    '1907年、1908年'   -> 1907
    '1937年（1月—6月）' -> 1937
    """
    m = re.match(r"(\d{4})年", stem)
    if m:
        return int(m.group(1))
    raise ValueError(f"Cannot extract year from stem: {stem!r}")


def get_literature_id(year: int) -> int:
    """根据年份返回对应的 literature_id (v2卷册编号)。

    映射关系基于 PDF 目录结构：
    v1: 1893-1903
    v2: 1904-1926
    v3: 1927-1937
    v4: 1949.10-1952
    v5: 1953-1956.9
    v6: 1956.10-1959.3
    v7: 1959.4-1961.6
    v8: 1961.7-1966.9
    v9: 1966.10-1976.9
    """
    if 1893 <= year <= 1903:
        return 1
    elif 1904 <= year <= 1926:
        return 2
    elif 1927 <= year <= 1937:
        return 3
    elif 1938 <= year <= 1948:
        return 3  # 1938-1948 也在 v3
    elif year == 1949:
        return 4  # 1949 跨 v3(1-9月) 和 v4(10-12月)，这里简化为 v4
    elif 1950 <= year <= 1952:
        return 4
    elif 1953 <= year <= 1955:
        return 5
    elif year == 1956:
        return 5  # 1956 跨 v5(1-9月) 和 v6(10-12月)，简化为 v5
    elif 1957 <= year <= 1958:
        return 6
    elif year == 1959:
        return 6  # 1959 跨 v6(1-3月) 和 v7(4-12月)，简化为 v6
    elif 1960 <= year <= 1961:
        return 7  # 1961 跨 v7(1-6月) 和 v8(7-12月)，简化为 v7
    elif 1962 <= year <= 1965:
        return 8
    elif year == 1966:
        return 8  # 1966 跨 v8(1-9月) 和 v9(10-12月)，简化为 v8
    elif 1967 <= year <= 1976:
        return 9
    else:
        return 1  # 默认返回 1


# ── Core parser ───────────────────────────────────────────────────────────────

class Entry:
    def __init__(self, month, day, body):
        self.month = month
        self.day = day
        self.body = body
        self.footnotes = []


def parse_md(md_path: Path, year: int) -> list:
    age = year - MAO_BIRTH
    year_str = str(year)
    literature_id = get_literature_id(year)

    with open(md_path, encoding="utf-8") as f:
        raw = f.read()

    # ── Tokenize ──────────────────────────────────────────────────────────────
    tokens = []
    for line in raw.split("\n"):
        ls = line.strip()
        if not ls:
            continue
        # Page separator <!-- N -->
        if re.match(r"^<!--\s*\d+\s*-->$", ls):
            tokens.append(("PAGE_SEP",))
            continue
        # Other HTML comments (month labels etc.) — skip
        if re.match(r"^<!--.*-->$", ls):
            continue
        # Markdown headers — skip
        if ls.startswith("#"):
            continue

        normed = norm_fn(ls)

        # Footnote definition: line whose normalized form starts with [N]
        fn_m = FNDEF_RE.match(normed)
        if fn_m:
            tokens.append(("FNDEF", fn_m.group(2).strip()))
            continue

        # Date entry
        plain = strip_bold(normed)
        date_result = parse_date(plain)
        if date_result:
            month, day, rest, is_same, is_same_month = date_result
            tokens.append(("ENTRY", month, day, norm_fn(rest), is_same, is_same_month))
            continue

        # Continuation paragraph
        tokens.append(("CONT", normed))

    # ── Build entries ─────────────────────────────────────────────────────────
    entries = []
    # FIFO: for each [N] reference in body order, which entry owns it
    body_marker_owners = []
    # Footnote definition texts in document order
    footnote_defs = []

    prev_month = None
    prev_day = None
    current_idx = None

    for tok in tokens:
        if tok[0] == "PAGE_SEP":
            # Don't clear current_idx — cross-page continuations still attach
            continue

        elif tok[0] == "ENTRY":
            _, month, day, rest, is_same, is_same_month = tok

            if is_same:
                # 同日 — inherit both month and day from previous entry
                month = prev_month or "01"
                day = prev_day or "01"

            elif is_same_month:
                # 同月 — inherit month; day = prev_day+1 (Rule 2)
                month = prev_month or "01"
                if prev_day is not None:
                    day = next_day_str(month, prev_day)
                else:
                    day = "01"
                prev_month, prev_day = month, day

            else:
                if day is None:
                    # Rule 2: no explicit day
                    if prev_month == month and prev_day is not None:
                        day = next_day_str(month, prev_day)
                    else:
                        day = "01"
                prev_month, prev_day = month, day

            e = Entry(month, day, rest)
            entries.append(e)
            current_idx = len(entries) - 1
            for _ in re.findall(r"\[\d+\]", rest):
                body_marker_owners.append(current_idx)

        elif tok[0] == "CONT":
            if current_idx is not None:
                cont = tok[1]
                entries[current_idx].body += " " + cont
                for _ in re.findall(r"\[\d+\]", cont):
                    body_marker_owners.append(current_idx)

        elif tok[0] == "FNDEF":
            footnote_defs.append(tok[1])

    # Fallback: files with no dated entries (e.g. 1907年、1908年.md)
    if not entries:
        body_parts = []
        fndefs_orphan = []
        for tok in tokens:
            if tok[0] == "CONT":
                body_parts.append(tok[1])
            elif tok[0] == "FNDEF":
                fndefs_orphan.append(tok[1])
        if body_parts:
            e = Entry("01", "01", " ".join(body_parts))
            e.footnotes = fndefs_orphan
            entries.append(e)

    else:
        # FIFO footnote assignment (works across pages by document order)
        for entry_idx, fn_text in zip(body_marker_owners, footnote_defs):
            entries[entry_idx].footnotes.append(fn_text)

    # ── Build JSON output ─────────────────────────────────────────────────────
    result = []
    for e in entries:
        body = renumber_body(e.body.strip())
        if e.footnotes:
            ann = " ".join(f"[{i+1}] {fn}" for i, fn in enumerate(e.footnotes))
        else:
            ann = ""
        result.append({
            "age": age,
            "year": year_str,
            "month": e.month,
            "day": e.day,
            "do": body,
            "annotation": ann,
            "literature_id": literature_id,
        })

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    md_files = sorted(INPUT_DIR.glob("*.md"))
    print(f"找到 {len(md_files)} 个 MD 文件\n")

    for md_path in md_files:
        stem = md_path.stem
        json_path = OUTPUT_DIR / f"{stem}.json"

        if json_path.exists():
            print(f"跳过（已存在）: {stem}")
            continue

        try:
            year = extract_year_from_stem(stem)
        except ValueError as e:
            print(f"[ERROR] {e}")
            continue

        print(f"处理: {stem}  (year={year})", end="  ", flush=True)

        try:
            result = parse_md(md_path, year)
        except Exception as e:
            print(f"\n[ERROR] 解析失败: {e}")
            continue

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"-> {len(result)} 条记录")

    print("\n全部完成！")


if __name__ == "__main__":
    main()
