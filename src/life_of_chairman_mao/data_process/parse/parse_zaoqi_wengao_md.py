"""parse_zaoqi_wengao_md.py — 将《毛泽东早期文稿》MD 解析为结构化 JSON。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from life_of_chairman_mao.data_process.parse.parse_xuanji import (
    MAO_BIRTH,
    ANNOTATION_MARKER_RE,
    STAR_NOTE_RE,
    format_title,
    norm_fn,
    parse_chinese_date,
)

DEFAULT_INPUT_DIR = Path(
    "/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/毛泽东早期文稿/md"
)
DEFAULT_OUTPUT_DIR = Path(
    "/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/毛泽东早期文稿/json"
)
DEFAULT_OUTPUT_FILE = "毛泽东早期文稿.json"

LITERATURE_ID = 45

DATE_LINE_RE = re.compile(r"^[（(](.+?)[）)]\s*$")
TITLE_LINE_RE = re.compile(r"^#\s+(.+)$")
ANNOTATION_HEADING_RE = re.compile(r"^#\s*注释\s*$")
TOC_PAGE_SUFFIX_RE = re.compile(r"(?:……|…|\.{2,})\s*\d+\s*$")
IMAGE_LINE_RE = re.compile(r"^!\[")
LATEX_FN_RE = re.compile(r"\$\^\{([^}]+)\}\$")

# 非正编篇目或版面标题
EXCLUDED_TITLE_KEYWORDS = (
    "《伦理学原理》批注",
    "目录",
    "副编",
    "出版说明",
    "毛泽东早期文稿",
)

# 正编最后一篇（此后为副编，如讲堂录等）
LAST_ZHENGBIAN_TITLE = "《新民学会会员通信集》第二集序"


def norm_early_footnotes(text: str) -> str:
    """将早期文稿中的 LaTeX 角标及混用括号统一为 [i]。"""
    def _latex_repl(match: re.Match[str]) -> str:
        inner = match.group(1).strip()
        inner = re.sub(r"^[\[(（]+|[\])）]+$", "", inner)
        if inner.isdigit():
            return f"[{inner}]"
        return norm_fn(match.group(0))

    text = LATEX_FN_RE.sub(_latex_repl, text)
    return norm_fn(text)


def clean_raw_title(line: str) -> str:
    """去掉标题行中的序号、页码、角标与 *。"""
    match = TITLE_LINE_RE.match(line.strip())
    if not match:
        return ""
    title = match.group(1).replace("*", "")
    title = LATEX_FN_RE.sub("", title)
    title = re.sub(r"\s*\[\d+\]\s*$", "", title)
    title = TOC_PAGE_SUFFIX_RE.sub("", title)
    title = re.sub(r"\s+\d+\s*$", "", title)
    return title.strip()


def is_toc_title_line(line: str) -> bool:
    """目录条目标题末尾常带页码。"""
    raw = line.strip()
    if not raw.startswith("# "):
        return False
    body = raw[2:].strip()
    if LATEX_FN_RE.search(body) or re.search(r"\[\d+\]\s*$", body):
        return False
    if TOC_PAGE_SUFFIX_RE.search(body):
        return True
    if re.search(r"\s+\d+\s*$", body) and "《" not in body:
        return True
    return False


def _is_title_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("# ") and not ANNOTATION_HEADING_RE.match(stripped)


def _is_date_line(line: str) -> bool:
    match = DATE_LINE_RE.match(line.strip())
    return bool(match and re.match(r"一九", match.group(1)))


def find_title_date_block(
    lines: list[str], title_idx: int,
) -> tuple[int, list[int], int] | None:
    """定位文章标题块：首行索引、标题行列表（含副标题）、日期行索引。"""
    if not _is_title_line(lines[title_idx]):
        return None

    start = title_idx
    while start > 0:
        prev = start - 1
        while prev >= 0 and not lines[prev].strip():
            prev -= 1
        if prev < 0 or not _is_title_line(lines[prev]):
            break
        between_has_date = any(
            _is_date_line(lines[k])
            for k in range(prev + 1, start)
            if lines[k].strip()
        )
        if between_has_date:
            break
        start = prev

    title_idxs: list[int] = []
    i = start
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue
        if _is_date_line(stripped):
            if not title_idxs:
                return None
            return start, title_idxs, i
        if _is_title_line(lines[i]):
            if is_toc_title_line(lines[i]):
                return None
            title_idxs.append(i)
            i += 1
            continue
        return None
    return None


def has_body_after_date(lines: list[str], date_idx: int) -> bool:
    """正文区：日期行之后应有非下一篇文章标题的内容。"""
    i = date_idx + 1
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue
        if ANNOTATION_HEADING_RE.match(stripped):
            return False
        if _is_date_line(stripped):
            i += 1
            continue
        if stripped.startswith("# "):
            block = find_title_date_block(lines, i)
            if block and block[0] == i and not is_toc_title_line(lines[i]):
                return False
            i += 1
            continue
        if IMAGE_LINE_RE.match(stripped):
            i += 1
            continue
        return True
    return False


def is_article_start(lines: list[str], title_idx: int) -> bool:
    block = find_title_date_block(lines, title_idx)
    if block is None:
        return False

    first_idx, _title_idxs, date_idx = block
    if first_idx != title_idx:
        return False

    title = clean_raw_title(lines[first_idx])
    if not title:
        return False
    if any(kw in title for kw in EXCLUDED_TITLE_KEYWORDS):
        return False
    if is_toc_title_line(lines[first_idx]):
        return False

    return has_body_after_date(lines, date_idx)


def find_content_start(lines: list[str]) -> int:
    """跳过封面、出版说明与目录，定位正编正文首篇。"""
    for i, line in enumerate(lines):
        if "商鞅徙木立信论" not in line or not line.strip().startswith("# "):
            continue
        if is_article_start(lines, i):
            return i
    return 0


def find_article_starts(lines: list[str]) -> list[int]:
    starts: list[int] = []
    content_start = find_content_start(lines)
    for i in range(content_start, len(lines)):
        if not is_article_start(lines, i):
            continue
        starts.append(i)
        title = clean_raw_title(lines[i])
        if LAST_ZHENGBIAN_TITLE in title:
            break
    return starts


def find_annotation_start(lines: list[str], body_start: int, body_end: int) -> int | None:
    for i in range(body_start, body_end):
        if ANNOTATION_HEADING_RE.match(lines[i].strip()):
            return i
    return None


def should_skip_body_line(stripped: str) -> bool:
    if IMAGE_LINE_RE.match(stripped):
        return True
    return False


def merge_body_lines(lines: list[str]) -> str:
    paragraphs: list[str] = []
    buffer: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buffer:
                paragraphs.append("".join(buffer))
                buffer = []
            continue
        if should_skip_body_line(stripped):
            continue
        if ANNOTATION_HEADING_RE.match(stripped):
            break
        if stripped.startswith("# "):
            stripped = stripped[2:].strip()
            if not stripped:
                continue
        buffer.append(stripped)

    if buffer:
        paragraphs.append("".join(buffer))
    return "\n".join(paragraphs)


def parse_annotations(lines: list[str]) -> str:
    """将 # 注释 区块解析为 [i] xxx，多条以换行分隔。"""
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
        if not stripped or ANNOTATION_HEADING_RE.match(stripped):
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


def parse_article(lines: list[str], title_idx: int, next_title_idx: int) -> dict | None:
    block = find_title_date_block(lines, title_idx)
    if block is None:
        return None

    first_idx, title_idxs, date_idx = block
    date_inner = DATE_LINE_RE.match(lines[date_idx].strip())
    if not date_inner:
        return None
    parsed = parse_chinese_date(date_inner.group(1))
    if not parsed:
        return None
    year, month, day = parsed

    section_end = next_title_idx
    anno_idx = find_annotation_start(lines, date_idx + 1, section_end)
    body_end = anno_idx if anno_idx is not None else section_end

    title_raw = clean_raw_title(lines[first_idx])
    title = format_title(norm_early_footnotes(title_raw))

    subtitle_parts = [
        clean_raw_title(lines[j])
        for j in title_idxs[1:]
    ]
    subtitle_parts = [s for s in subtitle_parts if s]

    content = merge_body_lines(lines[date_idx + 1: body_end])
    if subtitle_parts:
        prefix = "\n".join(subtitle_parts)
        content = f"{prefix}\n{content}" if content else prefix
    content = norm_early_footnotes(content)

    annotation = ""
    if anno_idx is not None:
        annotation = parse_annotations(lines[anno_idx + 1: section_end])
        annotation = norm_early_footnotes(annotation)

    age = int(year) - MAO_BIRTH
    return {
        "age": age,
        "year": year,
        "month": month,
        "day": day,
        "title": title,
        "content": content,
        "annotation": annotation,
        "literature_id": LITERATURE_ID,
    }


def load_all_lines(md_dir: Path) -> list[str]:
    md_files = sorted(md_dir.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"目录下没有 MD 文件: {md_dir}")
    lines: list[str] = []
    for md_path in md_files:
        lines.extend(md_path.read_text(encoding="utf-8").splitlines())
    return lines


def parse_all_articles(md_dir: Path) -> list[dict]:
    lines = load_all_lines(md_dir)
    starts = find_article_starts(lines)

    records: list[dict] = []
    for idx, title_idx in enumerate(starts):
        next_title_idx = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
        record = parse_article(lines, title_idx, next_title_idx)
        if record is not None:
            records.append(record)

    return records


def convert(
    md_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    output_name: str = DEFAULT_OUTPUT_FILE,
    skip_existing: bool = True,
    verbose: bool = True,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / output_name

    if skip_existing and out_path.exists():
        if verbose:
            print(f"跳过（已存在）: {out_path}")
        return 0

    records = parse_all_articles(md_dir)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    if verbose:
        print(f"输入: {md_dir}")
        print(f"输出: {out_path}")
        print(f"literature_id: {LITERATURE_ID}")
        print(f"共 {len(records)} 篇文章")

    return len(records)


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    force = "--force" in args
    if force:
        args = [a for a in args if a != "--force"]
    skip_existing = not force

    md_dir = Path(args[0]) if args else DEFAULT_INPUT_DIR
    output_dir = Path(args[1]) if len(args) > 1 else DEFAULT_OUTPUT_DIR

    convert(md_dir, output_dir, skip_existing=skip_existing)


if __name__ == "__main__":
    main()
