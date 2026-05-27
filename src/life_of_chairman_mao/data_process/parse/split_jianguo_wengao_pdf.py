#!/usr/bin/env python3
"""
切分《建国以来毛泽东文稿》PDF，按章节保存。

只切分「目录」与结束标记之间的章节（不含这两节）。
结束标记优先使用「附表一、二」；若无则使用「版权页」或「封底」。
文件名使用章节标题，不含页码；通过 PyMuPDF 直接复制页面，不改变分辨率。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import fitz

DEFAULT_INPUT_DIR = Path(
    '/Users/zhangpeng/Data/studies/datas/chairManMao/Selected-Works-of-MaoTseTung-master/建国以来毛泽东文稿'
)
DEFAULT_OUTPUT_BASE = Path(
    '/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/建国以来毛泽东文稿'
)

START_AFTER = '目录'
END_BEFORE_CANDIDATES = ('附表一、二', '版权页', '封底')

INVALID_FILENAME_CHARS = re.compile(r'[/\\:*?"<>|]')


def sanitize_filename(title: str) -> str:
    name = INVALID_FILENAME_CHARS.sub('_', title.strip())
    name = re.sub(r'\s+', ' ', name)
    return name.rstrip('. ')


def find_chapter_range(toc: list[list]) -> tuple[int, int, str]:
    start_idx = None
    end_idx = None
    end_marker = ''

    for i, (_level, title, _page) in enumerate(toc):
        if title == START_AFTER:
            start_idx = i
            continue
        if start_idx is not None and end_idx is None and title in END_BEFORE_CANDIDATES:
            end_idx = i
            end_marker = title
            break

    if start_idx is None:
        raise ValueError(f'未找到章节「{START_AFTER}」')
    if end_idx is None:
        raise ValueError(f'未找到结束标记 {END_BEFORE_CANDIDATES}')
    if end_idx <= start_idx + 1:
        raise ValueError(f'「{START_AFTER}」与「{end_marker}」之间没有可切分的章节')
    return start_idx + 1, end_idx, end_marker


def split_pdf(input_path: Path, output_dir: Path, verbose: bool = True) -> int:
    if not input_path.exists():
        raise FileNotFoundError(f'PDF 文件不存在: {input_path}')

    output_dir.mkdir(parents=True, exist_ok=True)

    src = fitz.open(str(input_path))
    toc = src.get_toc()
    chapter_start, chapter_end, end_marker = find_chapter_range(toc)
    total_pages = len(src)
    chapter_count = chapter_end - chapter_start

    if verbose:
        print(f'处理: {input_path.name}  (共 {total_pages} 页)')
        print(f'切分范围: 「{START_AFTER}」与「{end_marker}」之间，共 {chapter_count} 个章节')

    used_names: dict[str, int] = {}
    written = 0

    for i in range(chapter_start, chapter_end):
        _level, title, start_page = toc[i]
        page_from = start_page - 1

        if i + 1 < len(toc):
            page_to = toc[i + 1][2] - 2
        else:
            page_to = total_pages - 1

        if page_from < 0 or page_to >= total_pages or page_from > page_to:
            print(f'  [错误] {title}: 页码越界 {page_from + 1}-{page_to + 1} (PDF 共 {total_pages} 页)')
            continue

        base_name = sanitize_filename(title)
        if base_name in used_names:
            used_names[base_name] += 1
            out_name = f'{base_name}_{used_names[base_name]}.pdf'
        else:
            used_names[base_name] = 0
            out_name = f'{base_name}.pdf'

        out_doc = fitz.open()
        out_doc.insert_pdf(src, from_page=page_from, to_page=page_to)
        out_path = output_dir / out_name
        out_doc.save(str(out_path))
        out_doc.close()
        written += 1

        if verbose:
            page_count = page_to - page_from + 1
            print(f'  [{written}/{chapter_count}] {out_name} ({page_count} 页)')

    src.close()

    if verbose:
        print(f'完成: 输出 {written} 个文件 -> {output_dir}\n')
    return written


def split_all(input_dir: Path, output_base: Path) -> None:
    pdfs = sorted(input_dir.glob('*.pdf'))
    if not pdfs:
        raise FileNotFoundError(f'目录下没有 PDF 文件: {input_dir}')

    print(f'输入目录: {input_dir}')
    print(f'输出根目录: {output_base}\n')

    total_written = 0
    for pdf_path in pdfs:
        output_dir = output_base / pdf_path.stem / 'pdf'
        try:
            count = split_pdf(pdf_path, output_dir, verbose=True)
            total_written += count
        except (ValueError, FileNotFoundError) as exc:
            print(f'[失败] {pdf_path.name}: {exc}\n')

    print(f'全部完成！共处理 {len(pdfs)} 个 PDF，输出 {total_written} 个章节文件')


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]

    if not args:
        split_all(DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_BASE)
        return

    input_path = Path(args[0])
    if input_path.is_dir():
        output_base = Path(args[1]) if len(args) > 1 else DEFAULT_OUTPUT_BASE
        split_all(input_path, output_base)
        return

    output_dir = Path(args[1]) if len(args) > 1 else DEFAULT_OUTPUT_BASE / input_path.stem / 'pdf'
    split_pdf(input_path, output_dir)


if __name__ == '__main__':
    main()
