"""parse_xuanji.py — 解析《毛泽东选集》txt 为结构化 JSON。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MAO_BIRTH = 1893

INPUT_DIR = Path(
    "/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/毛泽东选集/txt"
)
OUTPUT_DIR = Path(
    "/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/毛泽东选集/json"
)

VOLUME_LITERATURE_ID = {
    "第一卷": 10,
    "第二卷": 11,
    "第三卷": 12,
    "第四卷": 13,
    "第五卷": 14,
    "第六卷（静火版）": 15,
    "第七卷（静火版）": 16,
}

CN_DIGIT = {
    "○": 0, "〇": 0, "O": 0, "零": 0,
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9,
}

MONTH_CN = {
    "正月": 1, "一月": 1, "二月": 2, "三月": 3, "四月": 4,
    "五月": 5, "六月": 6, "七月": 7, "八月": 8, "九月": 9,
    "十月": 10, "十一月": 11, "十二月": 12,
}

SEASON_MAP = {"春": (3, 1), "夏": (6, 1), "秋": (9, 1), "冬": (12, 1)}

DATE_LINE_RE = re.compile(r"^（(.+?)）\s*$")
ANNOTATION_RE = re.compile(r"^[　\s]*注[　\s]*释[　\s]*$")
VOLUME_PREFIX_RE = re.compile(r"^(.+?)-(.+)\.txt$")
ANNOTATION_MARKER_RE = re.compile(
    r"^[\s　]*(?:"
    r"〔\s*(\d+)\s*〕"
    r"|\[\s*(\d+)\s*\]"
    r"|\(\s*(\d+)\s*\)"
    r")\s*(.*)",
    re.DOTALL,
)
STAR_NOTE_RE = re.compile(r"^[\s　]*[*＊][\s　]*(.*)$")


def norm_fn(text: str) -> str:
    """将 〔N〕/（N） 及 OCR 混用括号转为 [N]。"""
    text = re.sub(r"[〔（](\d+)[〕）]", r"[\1]", text)
    text = re.sub(r"〔(\d+)[）)]", r"[\1]", text)
    text = re.sub(r"[（(](\d+)〕", r"[\1]", text)
    return text


def cn_to_int(s: str) -> int | None:
    """解析中文数字（1–99，用于日期）。"""
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    if s == "十":
        return 10
    if s.startswith("十"):
        rest = s[1:]
        return 10 + (CN_DIGIT.get(rest, 0) if rest else 0)
    if "十" in s:
        parts = s.split("十", 1)
        tens = CN_DIGIT.get(parts[0], 0) if parts[0] else 1
        ones = CN_DIGIT.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
        return tens * 10 + ones
    if s in CN_DIGIT:
        return CN_DIGIT[s]
    return None


def parse_cn_year(text: str) -> str | None:
    """从日期串中提取第一个公历年份。"""
    m = re.search(r"([○〇O零一二三四五六七八九]+|\d{4})", text)
    if not m:
        return None
    token = m.group(1)
    if token.isdigit() and len(token) == 4:
        return token
    digits = []
    for ch in token:
        if ch in CN_DIGIT:
            digits.append(str(CN_DIGIT[ch]))
        elif ch.isdigit():
            digits.append(ch)
    if len(digits) == 4:
        return "".join(digits)
    return None


def parse_month_day(text: str) -> tuple[str, str]:
    """从年份之后的日期部分解析 month/day。"""
    for season, (mo, d) in SEASON_MAP.items():
        if season in text:
            return f"{mo:02d}", f"{d:02d}"

    for name, num in sorted(MONTH_CN.items(), key=lambda x: -len(x[0])):
        if name in text:
            month = f"{num:02d}"
            after = text.split(name, 1)[1]
            if "初" in after and "日" not in after[:3]:
                return month, "01"
            if "月初" in after or after.strip().startswith("初"):
                return month, "01"
            day_m = re.search(r"([○〇O零一二三四五六七八九十]+|\d{1,2})日", after)
            if day_m:
                day = cn_to_int(day_m.group(1).replace("日", ""))
                if day:
                    return month, f"{day:02d}"
            return month, "01"

    return "01", "01"


def parse_chinese_date(date_text: str) -> tuple[str, str, str] | None:
    """解析括号内中文日期，返回 (year, month, day)。"""
    text = date_text.strip()
    if not text:
        return None

    # 跨期范围：取起始部分
    if "——" in text:
        text = text.split("——", 1)[0]
    if "—" in text and "——" not in date_text:
        text = text.split("—", 1)[0]
    # 多个日期：取第一个片段
    if "、" in text:
        text = text.split("、", 1)[0]

    year = parse_cn_year(text)
    if not year:
        return None

    month, day = parse_month_day(text)
    return year, month, day


def join_body_lines(lines: list[str]) -> str:
    """合并正文行，去掉排版换行。"""
    parts: list[str] = []
    buf: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buf:
                parts.append("".join(buf))
                buf = []
            continue
        buf.append(stripped)
    if buf:
        parts.append("".join(buf))
    return "\n".join(parts)


def find_date_line_idx(lines: list[str]) -> int | None:
    """定位标题下方、正文上方的日期行。"""
    for i, line in enumerate(lines):
        if DATE_LINE_RE.match(line.strip()):
            inner = DATE_LINE_RE.match(line.strip()).group(1)
            if re.match(r"一九", inner):
                return i
    return None


def extract_title(lines: list[str], date_idx: int) -> str:
    """提取日期行上方的题目（可多行），去掉 *。"""
    parts: list[str] = []
    for line in lines[:date_idx]:
        stripped = line.strip().replace("*", "")
        if stripped:
            parts.append(stripped)
    return "".join(parts)


def format_title(title: str) -> str:
    """题目无书名号时整体加《》；已有书名号则原样保留。"""
    title = title.strip()
    if not title:
        return title
    if "《" in title:
        return title
    return f"《{title}》"


def find_annotation_idx(lines: list[str], start: int) -> int | None:
    for i in range(start, len(lines)):
        if ANNOTATION_RE.match(lines[i].strip()):
            return i
    return None


def parse_annotations(lines: list[str]) -> str:
    """将「注释」区块解析为多条 [i] xxx，以换行分隔。"""
    entries: list[str] = []
    current_marker = ""
    current_parts: list[str] = []
    star_parts: list[str] = []

    def flush_numbered() -> None:
        nonlocal current_marker, current_parts
        if not current_marker:
            return
        text = "".join(current_parts).strip()
        entries.append(f"{current_marker} {text}" if text else current_marker)
        current_marker = ""
        current_parts = []

    def flush_star() -> None:
        nonlocal star_parts
        if star_parts:
            entries.append("".join(star_parts).strip())
            star_parts = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        marker_match = ANNOTATION_MARKER_RE.match(stripped)
        if marker_match:
            flush_star()
            flush_numbered()
            num = marker_match.group(1) or marker_match.group(2) or marker_match.group(3)
            current_marker = f"[{num}]"
            rest = marker_match.group(4).strip()
            current_parts = [rest] if rest else []
            continue

        star_match = STAR_NOTE_RE.match(stripped)
        if star_match and not current_marker:
            flush_star()
            star_parts.append(star_match.group(1).strip())
            continue

        if current_marker:
            current_parts.append(stripped)
        elif star_parts:
            star_parts.append(stripped)

    flush_star()
    flush_numbered()
    return "\n".join(entries)


def parse_txt_file(path: Path, literature_id: int) -> dict | None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    date_idx = find_date_line_idx(lines)
    if date_idx is None:
        return None

    date_inner = DATE_LINE_RE.match(lines[date_idx].strip()).group(1)
    parsed = parse_chinese_date(date_inner)
    if not parsed:
        return None
    year, month, day = parsed

    title = extract_title(lines, date_idx)

    anno_idx = find_annotation_idx(lines, date_idx + 1)
    body_end = anno_idx if anno_idx is not None else len(lines)
    body = join_body_lines(lines[date_idx + 1: body_end])
    body = norm_fn(body)

    annotation = ""
    if anno_idx is not None:
        annotation = parse_annotations(lines[anno_idx + 1:])
        annotation = norm_fn(annotation)

    age = int(year) - MAO_BIRTH
    return {
        "age": age,
        "year": year,
        "month": month,
        "day": day,
        "title": format_title(title),
        "content": body,
        "annotation": annotation,
        "literature_id": literature_id,
    }


def group_files_by_volume() -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {v: [] for v in VOLUME_LITERATURE_ID}
    for path in sorted(INPUT_DIR.glob("*.txt")):
        m = VOLUME_PREFIX_RE.match(path.name)
        if not m:
            continue
        volume = m.group(1)
        if volume in groups:
            groups[volume].append(path)
    return groups


def process_volume(volume: str, files: list[Path], literature_id: int) -> list[dict]:
    records: list[dict] = []
    skipped: list[str] = []
    for path in files:
        record = parse_txt_file(path, literature_id)
        if record is None:
            skipped.append(path.name)
            continue
        records.append(record)
    records.sort(key=lambda r: (r["year"], r["month"], r["day"]))
    if skipped:
        print(f"  跳过 {len(skipped)} 个文件（无有效日期）: {', '.join(skipped)}")
    return records


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    force = "--force" in args
    if force:
        args = [a for a in args if a != "--force"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    groups = group_files_by_volume()

    for volume, files in groups.items():
        out_path = OUTPUT_DIR / f"{volume}.json"
        if out_path.exists() and not force:
            print(f"跳过（已存在）: {out_path.name}")
            continue

        literature_id = VOLUME_LITERATURE_ID[volume]
        print(f"处理 {volume}（{len(files)} 个 txt）…")
        records = process_volume(volume, files, literature_id)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        print(f"  → {out_path.name}: {len(records)} 条记录")


if __name__ == "__main__":
    main()
