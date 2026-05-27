#!/usr/bin/env python3
"""
从《毛泽东文集》章节 PDF 提取文本，保存为 Markdown。

区分标题、日期、正文、出处、注释；过滤页码、页眉、页脚。
正文与标题中的注释标记统一为 [i]；标题内联显示，不单独列出。
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import fitz

DEFAULT_BASE_DIR = Path(
    "/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/毛泽东文集"
)
DEFAULT_VOLUME = "毛泽东文集第一卷"

TITLE_MIN_SIZE = 14.0
HEADER_Y_MAX = 0.35
PAGE_NUM_RE = re.compile(r"^[\d\s]{1,8}$")
DATE_RE = re.compile(r"^[（(].*(?:年|月|日|○|〇|O|0).*?[）)]\s*$")
SOURCE_RE = re.compile(r"^根据.*(?:刊印|发表|出版).*?[。.]?\s*$")
ANNOTATION_HEADER_RE = re.compile(r"^注\s*释\s*$")
HEADER_LINE_RE = re.compile(r"^\d+[\u4e00-\u9fff（(].*")
VOLUME_RUNNING_HEADER_RE = re.compile(r"毛泽东文集第[一二三四五六七八\d]+卷\d+")
TITLE_PAGE_TAIL_RE = re.compile(r"[\u4e00-\u9fff）)」』》]\d{1,4}$")
TITLE_FOOTNOTE_RE = re.compile(r"^(.+?)(?:\(\s*(\d+)\s*\)|\[(\d+)\])\s*$")
ANNOTATION_MARKER_RE = re.compile(
    r"^[\[(（C［【]?\s*(\d+)\s*[\]\)J\]]?\s*"
)
FOOTNOTE_INLINE_RE = re.compile(
    r"[\[(（C［【]\s*(\d+)\s*(?:[\]\)J\]|])\s*"
)
BRACKET_FOOTNOTE_RE = re.compile(r"〔\s*(\d+)\s*〕")
PAREN_FOOTNOTE_RE = re.compile(r"\(\s*(\d+)\s*\)")
GARBAGE_RE = re.compile(r"^[．。、，,\s'`｀匾矿/＇\.\-\_\{\}lL]+$")
WATERMARK_RE = re.compile(r"www\.mzdbl\.cn", re.IGNORECASE)

class BlockKind(Enum):
    TITLE = "title"
    DATE = "date"
    BODY = "body"
    SOURCE = "source"
    ANNOTATION_HEADER = "annotation_header"
    ANNOTATION = "annotation"
    SKIP = "skip"


@dataclass
class TextBlock:
    page: int
    y: float
    y_ratio: float
    x: float
    size: float
    text: str
    kind: BlockKind = BlockKind.BODY


@dataclass
class ExtractedDoc:
    title: str = ""
    date: str = ""
    body_paragraphs: list[str] = field(default_factory=list)
    source: str = ""
    annotations: list[tuple[str, str]] = field(default_factory=list)


def collapse_spaced_cjk(text: str) -> str:
    """去掉 PDF 逐字空格（如「来 信」→「来信」）。"""
    prev = None
    while prev != text:
        prev = text
        text = re.sub(
            r"([\u4e00-\u9fff（(〔【「『《、。，；：？！\u201c\u201d\u2018\u2019"
            r"—…〇○O0-9）)〕】」』》])\s+"
            r"(?=[\u4e00-\u9fff（(〔【「『《、。，；：？！\u201c\u201d\u2018\u2019"
            r"—…〇○O0-9）)〕】」』》])",
            r"\1",
            text,
        )
    text = re.sub(r"〔\s*(\d+)\s*〕", r"〔\1〕", text)
    text = re.sub(r"\[\s*(\d+)\s*\]", r"[\1]", text)
    return text


def normalize_footnote_marker(text: str) -> str:
    def repl(match: re.Match) -> str:
        return f"[{match.group(1)}]"

    text = BRACKET_FOOTNOTE_RE.sub(repl, text, count=1)
    return ANNOTATION_MARKER_RE.sub(repl, text, count=1)


def normalize_inline_footnotes(text: str) -> str:
    def repl(match: re.Match) -> str:
        return f"[{match.group(1)}]"

    text = BRACKET_FOOTNOTE_RE.sub(repl, text)
    text = FOOTNOTE_INLINE_RE.sub(repl, text)
    return PAREN_FOOTNOTE_RE.sub(repl, text)


def is_page_number(text: str, y_ratio: float) -> bool:
    stripped = text.strip()
    if y_ratio > 0.12 and y_ratio < 0.88:
        return False
    if PAGE_NUM_RE.match(stripped):
        return True
    if y_ratio <= 0.12 or y_ratio >= 0.88:
        if re.fullmatch(r"\d{1,4}", stripped):
            return True
    return False


def clean_block_text(text: str) -> str:
    text = collapse_spaced_cjk(text)
    return WATERMARK_RE.sub("", text).strip()


def is_header_footer(text: str, y_ratio: float, size: float) -> bool:
    stripped = text.strip()
    if y_ratio > 0.85 and (stripped.startswith("根据") or "刊印" in stripped):
        return False
    if WATERMARK_RE.fullmatch(stripped):
        return True
    if size >= 25:
        return True
    if VOLUME_RUNNING_HEADER_RE.search(stripped):
        return True
    if y_ratio <= 0.12 and HEADER_LINE_RE.match(stripped):
        return True
    if y_ratio <= 0.12 and re.match(r"^《毛泽东文集》", stripped):
        return True
    if y_ratio <= 0.12 and len(stripped) < 50 and TITLE_PAGE_TAIL_RE.search(stripped):
        return True
    if y_ratio >= 0.88 and re.search(r"《毛泽东文集》", stripped) and len(stripped) < 40:
        return True
    return False


def is_header_zone(block: TextBlock) -> bool:
    return block.page == 0 and block.y_ratio < HEADER_Y_MAX


def is_title_continuation(block: TextBlock) -> bool:
    text = block.text.strip()
    if not is_header_zone(block) or DATE_RE.match(text):
        return False
    if text.startswith(("——", "—", "－－")):
        return True
    return 12.0 <= block.size < TITLE_MIN_SIZE


def is_garbage(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if len(stripped) <= 4 and GARBAGE_RE.match(stripped):
        return True
    if len(stripped) <= 6 and not re.search(r"[\u4e00-\u9fff\d（(]", stripped):
        return True
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", stripped))
    if cjk_count < 2 and len(stripped) <= 12:
        return True
    return False


def extract_blocks(pdf_path: Path) -> list[TextBlock]:
    doc = fitz.open(str(pdf_path))
    blocks: list[TextBlock] = []

    for page_idx, page in enumerate(doc):
        page_height = page.rect.height
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue

            texts: list[str] = []
            max_size = 0.0
            for line in block["lines"]:
                for span in line["spans"]:
                    texts.append(span["text"])
                    max_size = max(max_size, span["size"])

            text = clean_block_text("".join(texts))
            if not text:
                continue

            bbox = block["bbox"]
            y_ratio = bbox[1] / page_height
            if (
                is_page_number(text, y_ratio)
                or is_garbage(text)
                or is_header_footer(text, y_ratio, max_size)
            ):
                continue

            blocks.append(TextBlock(
                page=page_idx,
                y=bbox[1],
                y_ratio=y_ratio,
                x=bbox[0],
                size=max_size,
                text=text,
            ))

    doc.close()
    blocks.sort(key=lambda b: (b.page, b.y, b.x))
    return blocks


def classify_blocks(blocks: list[TextBlock]) -> list[TextBlock]:
    if not blocks:
        return blocks

    title_candidates = [
        i for i, block in enumerate(blocks)
        if block.page == 0
        and 0.08 < block.y_ratio < 0.35
        and 12.0 <= block.size <= 22.0
        and "刊印" not in block.text
        and not block.text.startswith("根据")
        and not WATERMARK_RE.search(block.text)
    ]
    if title_candidates:
        title_idx = max(title_candidates, key=lambda i: blocks[i].size)
    else:
        first_page_indices = [
            i for i, block in enumerate(blocks)
            if block.page == 0 and not is_garbage(block.text)
        ]
        title_idx = max(first_page_indices, key=lambda i: blocks[i].size)
    blocks[title_idx].kind = BlockKind.TITLE

    header_idx = title_idx + 1
    while header_idx < len(blocks) and is_header_zone(blocks[header_idx]):
        header_text = blocks[header_idx].text.strip()
        if DATE_RE.match(header_text):
            blocks[header_idx].kind = BlockKind.DATE
            break
        if is_title_continuation(blocks[header_idx]):
            blocks[header_idx].kind = BlockKind.TITLE
            header_idx += 1
            continue
        break

    past_annotation_header = False
    seen_body = False

    for i, block in enumerate(blocks):
        if block.kind in (BlockKind.TITLE, BlockKind.DATE):
            continue

        text = block.text.strip()

        if ANNOTATION_HEADER_RE.match(text):
            block.kind = BlockKind.ANNOTATION_HEADER
            past_annotation_header = True
            continue

        if block.y_ratio > 0.85 and (
            SOURCE_RE.match(text)
            or (text.startswith("根据") and ("刊印" in text or "出版" in text))
            or (text.startswith("《") and "刊印" in text)
        ):
            block.kind = BlockKind.SOURCE
            continue

        if is_header_zone(block) and DATE_RE.match(text):
            block.kind = BlockKind.DATE
            continue

        if not seen_body and i < title_idx + 6 and DATE_RE.match(text):
            block.kind = BlockKind.DATE
            continue

        if past_annotation_header:
            block.kind = BlockKind.ANNOTATION
            continue

        if ANNOTATION_MARKER_RE.match(text):
            block.kind = BlockKind.ANNOTATION
            continue

        if block.size >= TITLE_MIN_SIZE and block.page > 0:
            block.kind = BlockKind.SKIP
            continue

        block.kind = BlockKind.BODY
        seen_body = True

    return blocks


def format_title(text: str) -> str:
    match = TITLE_FOOTNOTE_RE.match(text.strip())
    if match:
        marker_num = match.group(2) or match.group(3)
        return f"{match.group(1).strip()}[{marker_num}]"
    return normalize_inline_footnotes(text.strip())


def merge_body_lines(lines: list[str]) -> list[str]:
    if not lines:
        return []

    paragraphs: list[str] = []
    current = lines[0]

    for line in lines[1:]:
        if current.endswith(("：", "。", "！", "？", "；", "”", "』", "）", "】")):
            paragraphs.append(current)
            current = line
        elif line.startswith(("问：", "答：", "一、", "二、", "三、", "四、", "五、", "六、")):
            paragraphs.append(current)
            current = line
        else:
            current += line

    if current:
        paragraphs.append(current)

    return paragraphs


def group_annotations(lines: list[str]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    current_marker = ""
    current_parts: list[str] = []

    for line in lines:
        match = ANNOTATION_MARKER_RE.match(line)
        if match:
            if current_marker or current_parts:
                entries.append((current_marker, "".join(current_parts).strip()))
            current_marker = f"[{match.group(1)}]"
            rest = ANNOTATION_MARKER_RE.sub("", line, count=1).strip()
            current_parts = [rest] if rest else []
        else:
            current_parts.append(line)

    if current_marker or current_parts:
        entries.append((current_marker, "".join(current_parts).strip()))

    return entries


def parse_pdf(pdf_path: Path) -> ExtractedDoc:
    blocks = classify_blocks(extract_blocks(pdf_path))
    doc = ExtractedDoc()

    title_parts: list[str] = []
    body_lines: list[str] = []
    source_lines: list[str] = []
    annotation_lines: list[str] = []

    for block in blocks:
        raw_text = block.text.strip()
        if block.kind == BlockKind.TITLE:
            title_parts.append(format_title(raw_text))
            continue

        text = normalize_inline_footnotes(raw_text)
        if block.kind == BlockKind.DATE:
            doc.date = text
        elif block.kind == BlockKind.SOURCE:
            source_lines.append(text)
        elif block.kind == BlockKind.ANNOTATION:
            annotation_lines.append(normalize_footnote_marker(text))
        elif block.kind == BlockKind.BODY:
            body_lines.append(text)

    doc.title = "".join(title_parts)
    doc.body_paragraphs = merge_body_lines(body_lines)
    doc.source = "".join(source_lines)
    doc.annotations = group_annotations(annotation_lines)
    return doc


def to_markdown(doc: ExtractedDoc) -> str:
    parts: list[str] = []

    parts.append(f"# {doc.title}\n")

    if doc.date:
        parts.append(f"**日期**：{doc.date}\n")

    if doc.body_paragraphs:
        parts.append("## 正文\n")
        for para in doc.body_paragraphs:
            parts.append(f"{para}\n")

    if doc.source:
        parts.append(f"**出处**：{doc.source}\n")

    if doc.annotations:
        parts.append("## 注释\n")
        for marker, content in doc.annotations:
            if marker:
                parts.append(f"### {marker}\n")
            if content:
                parts.append(f"{content}\n")

    return "\n".join(parts).rstrip() + "\n"


def pdf_to_md(pdf_path: Path, output_dir: Path, *, skip_existing: bool = True) -> Path | None:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{pdf_path.stem}.md"
    if skip_existing and output_path.exists():
        return None
    md_content = to_markdown(parse_pdf(pdf_path))
    output_path.write_text(md_content, encoding="utf-8")
    return output_path


def convert_all(
    pdf_dir: Path,
    output_dir: Path,
    *,
    skip_existing: bool = True,
    verbose: bool = True,
) -> tuple[int, int, list[tuple[str, str]]]:
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"目录下没有 PDF 文件: {pdf_dir}")

    if verbose:
        print(f"输入目录: {pdf_dir}")
        print(f"输出目录: {output_dir}")
        print(f"共 {len(pdfs)} 个文件\n")

    success = 0
    skipped = 0
    failed: list[tuple[str, str]] = []

    for pdf_path in pdfs:
        try:
            output_path = pdf_to_md(pdf_path, output_dir, skip_existing=skip_existing)
            if output_path is None:
                skipped += 1
                if verbose:
                    print(f"[跳过] {pdf_path.stem}.md")
                continue
            success += 1
            if verbose:
                print(f"[{success}/{len(pdfs)}] {output_path.name}")
        except Exception as exc:  # pylint: disable=broad-except
            failed.append((pdf_path.name, str(exc)))
            if verbose:
                print(f"[失败] {pdf_path.name}: {exc}")

    if verbose:
        print(f"\n完成: 新写入 {success} 个, 跳过 {skipped} 个, 失败 {len(failed)} 个")
        if failed:
            for name, err in failed:
                print(f"  {name}: {err}")

    return success, skipped, failed


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    force = "--force" in args
    if force:
        args = [a for a in args if a != "--force"]

    skip_existing = not force

    if not args:
        vol_dir = DEFAULT_BASE_DIR / DEFAULT_VOLUME
        convert_all(vol_dir / "pdf", vol_dir / "md", skip_existing=skip_existing)
        return

    input_path = Path(args[0])
    if input_path.is_dir() and (input_path / "pdf").is_dir() and len(args) == 1:
        convert_all(input_path / "pdf", input_path / "md", skip_existing=skip_existing)
        return

    if input_path.is_dir():
        output_dir = Path(args[1]) if len(args) > 1 else input_path
        convert_all(input_path, output_dir, skip_existing=skip_existing)
        return

    output_dir = Path(args[1]) if len(args) > 1 else DEFAULT_BASE_DIR / DEFAULT_VOLUME / "md"
    result = pdf_to_md(input_path, output_dir, skip_existing=skip_existing)
    if result:
        print(f"已保存: {result}")
    else:
        print("已存在，跳过（使用 --force 覆盖）")


if __name__ == "__main__":
    main()
