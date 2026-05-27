"""parse_wenji_md.py — 将《毛泽东文集》各卷 MD 解析为结构化 JSON。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from life_of_chairman_mao.data_process.parse.parse_xuanji import (
    MAO_BIRTH,
    format_title,
    norm_fn,
    parse_chinese_date,
)

DEFAULT_BASE_DIR = Path(
    "/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/毛泽东文集"
)
DEFAULT_VOLUME = "毛泽东文集第一卷"

VOLUME_LITERATURE_ID = {
    "毛泽东文集第一卷": 17,
    "毛泽东文集第二卷": 18,
    "毛泽东文集第三卷": 19,
    "毛泽东文集第四卷": 20,
    "毛泽东文集第五卷": 21,
    "毛泽东文集第六卷": 22,
    "毛泽东文集第七卷": 23,
    "毛泽东文集第八卷": 24,
}

DATE_FIELD_RE = re.compile(r"^\*\*日期\*\*[：:]\s*[（(](.+?)[）)]\s*$")
CN_DATE_IN_PAREN_RE = re.compile(r"[（(](一九[^）)]+)[）)]")
STEM_DATE_SUFFIX_RE = re.compile(r"[（(]一九[^）)]+[）)]\s*$")
TITLE_LINE_RE = re.compile(r"^#\s+(.+)$")
ANNOTATION_HEADING_RE = re.compile(r"^###\s+\[(\d+)\]\s*$")
BODY_TITLE_TAIL_RE = re.compile(
    r"^(.{1,80}?)（一九[^）]+）\s*$"
)
SOURCE_LINE_RE = re.compile(r"^\*\*出处\*\*")


def extract_cn_dates(text: str) -> list[str]:
    """提取文本中所有「（一九…）」式日期串。"""
    return CN_DATE_IN_PAREN_RE.findall(text)


def extract_date_text(
    lines: list[str],
    stem: str,
    body_start: int | None = None,
    body_end: int | None = None,
) -> str | None:
    """从 **日期** 行、文件名或正文首段中提取中文日期串。"""
    for line in lines:
        match = DATE_FIELD_RE.match(line.strip())
        if match:
            return match.group(1)

    for candidate in reversed(extract_cn_dates(stem)):
        if parse_chinese_date(candidate):
            return candidate

    if body_start is not None:
        end = body_end if body_end is not None else len(lines)
        for line in lines[body_start + 1: end]:
            stripped = line.strip()
            if not stripped:
                continue
            for candidate in extract_cn_dates(stripped):
                if parse_chinese_date(candidate):
                    return candidate
            break

    return None


def extract_h1_title(lines: list[str]) -> str:
    """从首个 # 标题行提取题目，去掉 * 标记。"""
    for line in lines:
        match = TITLE_LINE_RE.match(line.strip())
        if match:
            return match.group(1).replace("*", "").strip()
    return ""


def extract_title(
    lines: list[str],
    stem: str,
    body_start: int | None = None,
    body_end: int | None = None,
) -> str:
    """合并 # 标题、文件名与正文首行续题，得到完整题目。"""
    stem_title = STEM_DATE_SUFFIX_RE.sub("", stem).strip()
    h1_title = extract_h1_title(lines)
    title = stem_title or h1_title

    if h1_title and stem_title and stem_title != h1_title:
        if stem_title.startswith(h1_title):
            title = stem_title
        elif h1_title.startswith(stem_title):
            title = h1_title

    if body_start is not None:
        end = body_end if body_end is not None else len(lines)
        for line in lines[body_start + 1: end]:
            stripped = line.strip()
            if not stripped:
                continue
            tail_match = BODY_TITLE_TAIL_RE.match(stripped)
            if tail_match:
                suffix = tail_match.group(1)
                if suffix and not title.endswith(suffix):
                    title = f"{title}{suffix}"
            break

    if not title:
        title = stem_title or h1_title
    return title


def find_section(lines: list[str], heading: str) -> int | None:
    target = f"## {heading}"
    for i, line in enumerate(lines):
        if line.strip() == target:
            return i
    return None


def should_skip_body_line(stripped: str, *, first_line: bool) -> bool:
    """跳过正文开头的标题续行（含日期括号）。"""
    if not first_line:
        return False
    if BODY_TITLE_TAIL_RE.match(stripped):
        return True
    if stripped.startswith("#"):
        return True
    return bool(
        first_line
        and len(stripped) <= 80
        and extract_cn_dates(stripped)
        and not re.search(r"[，。；：]", stripped)
    )


def merge_body_paragraphs(lines: list[str]) -> str:
    """合并正文段落，跳过 **出处** 与标题续行。"""
    paragraphs: list[str] = []
    buffer: list[str] = []
    seen_content = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buffer:
                paragraphs.append("".join(buffer))
                buffer = []
            continue
        if SOURCE_LINE_RE.match(stripped):
            continue
        if not seen_content and should_skip_body_line(stripped, first_line=True):
            continue
        seen_content = True
        buffer.append(stripped)

    if buffer:
        paragraphs.append("".join(buffer))
    return "\n".join(paragraphs)


def parse_annotations(lines: list[str]) -> str:
    """将 ## 注释 区块解析为 [i] xxx 格式；无编号时保留整段注释正文。"""
    has_numbered = any(
        ANNOTATION_HEADING_RE.match(line.strip())
        for line in lines
        if line.strip()
    )
    if not has_numbered:
        return merge_body_paragraphs(lines)

    entries: list[str] = []
    current_marker = ""
    current_parts: list[str] = []

    for line in lines:
        stripped = line.strip()
        match = ANNOTATION_HEADING_RE.match(stripped)
        if match:
            if current_marker:
                text = "".join(current_parts).strip()
                entries.append(f"{current_marker} {text}" if text else current_marker)
            current_marker = f"[{match.group(1)}]"
            current_parts = []
            continue
        if current_marker and stripped:
            current_parts.append(stripped)

    if current_marker:
        text = "".join(current_parts).strip()
        entries.append(f"{current_marker} {text}" if text else current_marker)

    return "\n".join(entries)


def parse_md_file(md_path: Path, literature_id: int) -> dict | None:
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    stem = md_path.stem

    body_start = find_section(lines, "正文")
    if body_start is None:
        return None

    anno_start = find_section(lines, "注释")
    body_end = anno_start if anno_start is not None else len(lines)

    date_text = extract_date_text(lines, stem, body_start, body_end)
    if not date_text:
        return None

    parsed = parse_chinese_date(date_text)
    if not parsed:
        return None
    year, month, day = parsed

    title_raw = extract_title(lines, stem, body_start, body_end)
    title = format_title(norm_fn(title_raw))
    content = merge_body_paragraphs(lines[body_start + 1: body_end])
    content = norm_fn(content)

    annotation = ""
    if anno_start is not None:
        annotation = parse_annotations(lines[anno_start + 1:])
        annotation = norm_fn(annotation)

    age = int(year) - MAO_BIRTH
    return {
        "age": age,
        "year": year,
        "month": month,
        "day": day,
        "title": title,
        "content": content,
        "annotation": annotation,
        "literature_id": literature_id,
    }


def convert_volume(
    vol_dir: Path,
    *,
    skip_existing: bool = True,
    verbose: bool = True,
) -> tuple[int, list[str]]:
    vol_name = vol_dir.name
    if vol_name not in VOLUME_LITERATURE_ID:
        raise ValueError(f"未知卷名: {vol_name}")

    md_dir = vol_dir / "md"
    json_dir = vol_dir / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    out_path = json_dir / f"{vol_name}.json"

    if skip_existing and out_path.exists():
        if verbose:
            print(f"跳过（已存在）: {out_path}")
        return 0, []

    literature_id = VOLUME_LITERATURE_ID[vol_name]
    md_files = sorted(md_dir.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"目录下没有 MD 文件: {md_dir}")

    records: list[dict] = []
    skipped: list[str] = []

    for md_path in md_files:
        record = parse_md_file(md_path, literature_id)
        if record is None:
            skipped.append(md_path.name)
            continue
        records.append(record)

    records.sort(key=lambda r: (r["year"], r["month"], r["day"], r["title"]))

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    if verbose:
        print(f"输入: {md_dir}")
        print(f"输出: {out_path}")
        print(f"共 {len(md_files)} 个 MD → {len(records)} 条记录")
        if skipped:
            print(f"跳过 {len(skipped)} 个（无法解析日期）:")
            for name in skipped:
                print(f"  {name}")

    return len(records), skipped


def convert_all_volumes(
    base_dir: Path,
    *,
    skip_existing: bool = True,
    verbose: bool = True,
) -> None:
    volumes = sorted(
        p for p in base_dir.iterdir()
        if p.is_dir() and p.name in VOLUME_LITERATURE_ID
    )
    for vol_dir in volumes:
        if verbose:
            print(f"\n========== {vol_dir.name} ==========")
        convert_volume(vol_dir, skip_existing=skip_existing, verbose=verbose)


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    force = "--force" in args
    if force:
        args = [a for a in args if a != "--force"]
    skip_existing = not force

    if not args:
        convert_volume(
            DEFAULT_BASE_DIR / DEFAULT_VOLUME,
            skip_existing=skip_existing,
        )
        return

    input_path = Path(args[0])
    if input_path.name in VOLUME_LITERATURE_ID or (input_path / "md").is_dir():
        convert_volume(input_path, skip_existing=skip_existing)
        return

    if input_path == DEFAULT_BASE_DIR or input_path.name == "毛泽东文集":
        convert_all_volumes(input_path, skip_existing=skip_existing)
        return

    raise SystemExit(f"无法识别的路径: {input_path}")


if __name__ == "__main__":
    main()
