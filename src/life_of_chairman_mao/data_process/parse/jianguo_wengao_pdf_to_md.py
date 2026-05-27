#!/usr/bin/env python3
"""
从《建国以来毛泽东文稿》章节 PDF 提取文本，保存为 Markdown。

区分标题、注释标记、正文、出处、注释内容；过滤页码。
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import fitz

DEFAULT_BASE_DIR = Path(
    '/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/建国以来毛泽东文稿'
)
VOLUME1_DIR_NAME = '建国以来毛泽东文稿_第1册（1949年9月-1950年2月）'
DEFAULT_PDF_DIR = DEFAULT_BASE_DIR / VOLUME1_DIR_NAME / 'pdf'
DEFAULT_OUTPUT_DIR = DEFAULT_BASE_DIR / VOLUME1_DIR_NAME / 'md'

TITLE_MIN_SIZE = 40.0
PAGE_NUM_RE = re.compile(r'^[\d\s]{1,8}$')
DATE_RE = re.compile(r'^[（(].*(?:年|月|日|O|0).*?[）)]\s*$')
SOURCE_RE = re.compile(r'^根据.*(?:刊印|发表).*?[。.]?\s*$')
TITLE_FOOTNOTE_RE = re.compile(r'^(.+?)(?:\(\s*(\d+)\s*\)|\[(\d+)\])\s*$')
ANNOTATION_MARKER_RE = re.compile(
    r'^[\[(（C［【]?\s*(\d+)\s*[\]\)J\]]?\s*'
)
FOOTNOTE_INLINE_RE = re.compile(
    r'[\[(（C［【]\s*(\d+)\s*(?:[\]\)J\]|])\s*'
)
PAREN_FOOTNOTE_RE = re.compile(r'\(\s*(\d+)\s*\)')
GARBAGE_RE = re.compile(r'^[．。、，,\s\'`｀｀匾矿/＇\.\-\_\{\}lL]+$')


class BlockKind(Enum):
    TITLE = 'title'
    DATE = 'date'
    BODY = 'body'
    SOURCE = 'source'
    ANNOTATION_HEADER = 'annotation_header'
    ANNOTATION = 'annotation'
    SKIP = 'skip'


@dataclass
class TextBlock:
    page: int
    y: float
    x: float
    size: float
    text: str
    kind: BlockKind = BlockKind.BODY


@dataclass
class ExtractedDoc:
    title: str = ''
    date: str = ''
    body_paragraphs: list[str] = field(default_factory=list)
    source: str = ''
    annotations: list[tuple[str, str]] = field(default_factory=list)  # (marker, content)


def normalize_footnote_marker(text: str) -> str:
    """将 OCR 误识别的注释标记统一为 [n] 格式。"""

    def repl(match: re.Match) -> str:
        return f'[{match.group(1)}]'

    return ANNOTATION_MARKER_RE.sub(repl, text, count=1)


def normalize_inline_footnotes(text: str) -> str:
    def repl(match: re.Match) -> str:
        return f'[{match.group(1)}]'

    text = FOOTNOTE_INLINE_RE.sub(repl, text)
    return PAREN_FOOTNOTE_RE.sub(repl, text)


def is_page_number(text: str, y_ratio: float, page_height: float) -> bool:
    stripped = text.strip()
    if y_ratio < 0.88:
        return False
    if PAGE_NUM_RE.match(stripped):
        return True
    if y_ratio >= 0.9 and re.fullmatch(r'\d{1,4}', stripped):
        return True
    return False


def is_garbage(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if len(stripped) <= 4 and GARBAGE_RE.match(stripped):
        return True
    if len(stripped) <= 6 and not re.search(r'[\u4e00-\u9fff\d（(]', stripped):
        return True
    cjk_count = len(re.findall(r'[\u4e00-\u9fff]', stripped))
    if cjk_count < 2 and len(stripped) <= 12:
        return True
    return False


def extract_blocks(pdf_path: Path) -> list[TextBlock]:
    doc = fitz.open(str(pdf_path))
    blocks: list[TextBlock] = []

    for page_idx, page in enumerate(doc):
        page_height = page.rect.height
        for block in page.get_text('dict')['blocks']:
            if block.get('type') != 0:
                continue

            texts: list[str] = []
            max_size = 0.0
            for line in block['lines']:
                for span in line['spans']:
                    texts.append(span['text'])
                    max_size = max(max_size, span['size'])

            text = ''.join(texts).strip()
            if not text:
                continue

            bbox = block['bbox']
            y_ratio = bbox[1] / page_height
            if is_page_number(text, y_ratio, page_height) or is_garbage(text):
                continue

            blocks.append(TextBlock(
                page=page_idx,
                y=bbox[1],
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

    first_page_indices = [
        i for i, block in enumerate(blocks)
        if block.page == 0 and not is_garbage(block.text)
    ]
    if not first_page_indices:
        first_page_indices = [i for i, block in enumerate(blocks) if block.page == 0]
    title_idx = max(first_page_indices, key=lambda i: blocks[i].size)
    blocks[title_idx].kind = BlockKind.TITLE

    past_annotation_header = False
    seen_body = False

    for i, block in enumerate(blocks):
        if i == title_idx:
            continue

        text = block.text.strip()

        if text == '注释':
            block.kind = BlockKind.ANNOTATION_HEADER
            past_annotation_header = True
            continue

        if SOURCE_RE.match(text) or (text.startswith('根据') and '刊印' in text):
            block.kind = BlockKind.SOURCE
            continue

        if text.startswith('根据') or (text.startswith('《') and '刊印' in text):
            block.kind = BlockKind.SOURCE
            continue

        if not seen_body and i < title_idx + 4 and DATE_RE.match(text):
            block.kind = BlockKind.DATE
            continue

        if past_annotation_header:
            block.kind = BlockKind.ANNOTATION
            continue

        if ANNOTATION_MARKER_RE.match(text):
            block.kind = BlockKind.ANNOTATION
            continue

        if block.size >= TITLE_MIN_SIZE:
            block.kind = BlockKind.SKIP
            continue

        block.kind = BlockKind.BODY
        seen_body = True

    return blocks


def format_title(text: str) -> str:
    match = TITLE_FOOTNOTE_RE.match(text.strip())
    if match:
        marker_num = match.group(2) or match.group(3)
        return f'{match.group(1).strip()}[{marker_num}]'
    return normalize_inline_footnotes(text.strip())


def merge_body_lines(lines: list[str]) -> list[str]:
    if not lines:
        return []

    paragraphs: list[str] = []
    current = lines[0]

    for line in lines[1:]:
        if current.endswith(('：', '。', '！', '？', '；', '”', '』', '）', '】')):
            paragraphs.append(current)
            current = line
        elif line.startswith(('问：', '答：', '中央', '军委', '少奇', '林彪', '各中央')):
            paragraphs.append(current)
            current = line
        else:
            current += line

    if current:
        paragraphs.append(current)

    return paragraphs


def group_annotations(lines: list[str]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    current_marker = ''
    current_parts: list[str] = []

    for line in lines:
        match = ANNOTATION_MARKER_RE.match(line)
        if match:
            if current_marker or current_parts:
                entries.append((current_marker, ''.join(current_parts).strip()))
            current_marker = f'[{match.group(1)}]'
            rest = ANNOTATION_MARKER_RE.sub('', line, count=1).strip()
            current_parts = [rest] if rest else []
        else:
            current_parts.append(line)

    if current_marker or current_parts:
        entries.append((current_marker, ''.join(current_parts).strip()))

    return entries


def parse_pdf(pdf_path: Path) -> ExtractedDoc:
    blocks = classify_blocks(extract_blocks(pdf_path))
    doc = ExtractedDoc()

    body_lines: list[str] = []
    source_lines: list[str] = []
    annotation_lines: list[str] = []

    for block in blocks:
        raw_text = block.text.strip()
        if block.kind == BlockKind.TITLE:
            doc.title = format_title(raw_text)
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

    doc.body_paragraphs = merge_body_lines(body_lines)
    doc.source = ''.join(source_lines)
    doc.annotations = group_annotations(annotation_lines)
    return doc


def to_markdown(doc: ExtractedDoc) -> str:
    parts: list[str] = []

    parts.append(f'# {doc.title}\n')

    if doc.date:
        parts.append(f'**日期**：{doc.date}\n')

    if doc.body_paragraphs:
        parts.append('## 正文\n')
        for para in doc.body_paragraphs:
            parts.append(f'{para}\n')

    if doc.source:
        parts.append(f'**出处**：{doc.source}\n')

    if doc.annotations:
        parts.append('## 注释\n')
        for marker, content in doc.annotations:
            if marker:
                parts.append(f'### {marker}\n')
            if content:
                parts.append(f'{content}\n')

    return '\n'.join(parts).rstrip() + '\n'


def pdf_to_md(pdf_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f'{pdf_path.stem}.md'
    md_content = to_markdown(parse_pdf(pdf_path))
    output_path.write_text(md_content, encoding='utf-8')
    return output_path


def convert_all(pdf_dir: Path, output_dir: Path, verbose: bool = True) -> tuple[int, list[tuple[str, str]]]:
    pdfs = sorted(pdf_dir.glob('*.pdf'))
    if not pdfs:
        raise FileNotFoundError(f'目录下没有 PDF 文件: {pdf_dir}')

    if verbose:
        print(f'输入目录: {pdf_dir}')
        print(f'输出目录: {output_dir}')
        print(f'共 {len(pdfs)} 个文件\n')

    success = 0
    failed: list[tuple[str, str]] = []

    for pdf_path in pdfs:
        try:
            output_path = pdf_to_md(pdf_path, output_dir)
            success += 1
            if verbose:
                print(f'[{success}/{len(pdfs)}] {output_path.name}')
        except Exception as exc:  # pylint: disable=broad-except
            failed.append((pdf_path.name, str(exc)))
            if verbose:
                print(f'[失败] {pdf_path.name}: {exc}')

    if verbose:
        print(f'\n完成: 成功 {success} 个, 失败 {len(failed)} 个')
        if failed:
            print('失败列表:')
            for name, err in failed:
                print(f'  {name}: {err}')

    return success, failed


def convert_all_volumes(base_dir: Path, exclude: set[str] | None = None) -> None:
    exclude = exclude or set()
    volume_dirs = sorted(
        d for d in base_dir.iterdir()
        if d.is_dir() and d.name not in exclude and (d / 'pdf').is_dir()
    )
    if not volume_dirs:
        raise FileNotFoundError(f'未找到可处理的册目录: {base_dir}')

    print(f'根目录: {base_dir}')
    print(f'待处理 {len(volume_dirs)} 册\n')

    total_success = 0
    all_failed: list[tuple[str, str, str]] = []

    for vol_dir in volume_dirs:
        print('=' * 60)
        print(f'【{vol_dir.name}】')
        success, failed = convert_all(vol_dir / 'pdf', vol_dir / 'md', verbose=False)
        total_success += success
        print(f'完成: 成功 {success} 个, 失败 {len(failed)} 个')
        for name, err in failed:
            all_failed.append((vol_dir.name, name, err))

    print('\n' + '=' * 60)
    print(f'全部完成: {len(volume_dirs)} 册, 共输出 {total_success} 个 MD 文件, 失败 {len(all_failed)} 个')
    if all_failed:
        print('失败列表:')
        for vol, name, err in all_failed:
            print(f'  [{vol}] {name}: {err}')


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]

    if not args:
        convert_all(DEFAULT_PDF_DIR, DEFAULT_OUTPUT_DIR)
        return

    if args[0] in ('--all-volumes', '--remaining-volumes'):
        exclude = {VOLUME1_DIR_NAME} if args[0] == '--remaining-volumes' else set()
        convert_all_volumes(DEFAULT_BASE_DIR, exclude=exclude)
        return

    input_path = Path(args[0])
    output_dir = Path(args[1]) if len(args) > 1 else DEFAULT_OUTPUT_DIR

    if input_path.is_dir() and (input_path / 'pdf').is_dir() and len(args) == 1:
        convert_all(input_path / 'pdf', input_path / 'md')
        return

    if input_path.is_dir():
        convert_all(input_path, output_dir)
        return

    output_path = pdf_to_md(input_path, output_dir)
    print(f'已保存: {output_path}')


if __name__ == '__main__':
    main()
