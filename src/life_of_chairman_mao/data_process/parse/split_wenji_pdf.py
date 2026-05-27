#!/usr/bin/env python3
"""
切分《毛泽东文集》PDF，按三级目录（含文章日期）保存章节。

只切分书签层级为 3、且标题含中文日期括号「（一九…）」的章节；
子节（四级目录，如决议案分条、调查分章）并入所属三级章节。
文件名使用章节标题，不含页码。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import fitz

DEFAULT_INPUT_DIR = Path(
    "/Users/zhangpeng/Data/studies/datas/chairManMao/文集"
)
DEFAULT_OUTPUT_BASE = Path(
    "/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/毛泽东文集"
)

DATE_IN_TITLE_RE = re.compile(r"（一九[^）]+）")
INVALID_FILENAME_CHARS = re.compile(r'[/\\:*?"<>|]')


def sanitize_filename(title: str) -> str:
    """章节标题转安全文件名，去掉末尾页码类后缀。"""
    name = INVALID_FILENAME_CHARS.sub("_", title.strip())
    name = re.sub(r"\s+", " ", name)
    # 去掉常见「 第N页」「 P.N」等页码后缀
    name = re.sub(r"\s+第?\s*\d+\s*页\s*$", "", name)
    name = re.sub(r"\s+P\.?\s*\d+\s*$", "", name, flags=re.IGNORECASE)
    return name.rstrip(". ")


def is_article_chapter(level: int, title: str) -> bool:
    """三级目录且标题含文章日期。"""
    return level == 3 and bool(DATE_IN_TITLE_RE.search(title))


def find_page_end(toc: list[list], toc_idx: int, total_pages: int) -> int:
    """当前章节最后一页（0-based）。"""
    for j in range(toc_idx + 1, len(toc)):
        level, _title, page = toc[j]
        if level <= 3 and page > 0:
            return page - 2
    return total_pages - 1


def collect_chapters(toc: list[list]) -> list[tuple[int, str, int]]:
    """返回 (toc_index, title, start_page_1based)。"""
    chapters: list[tuple[int, str, int]] = []
    for i, (level, title, page) in enumerate(toc):
        if is_article_chapter(level, title) and page > 0:
            chapters.append((i, title, page))
    return chapters


def split_pdf(
    input_path: Path,
    output_dir: Path,
    *,
    skip_existing: bool = True,
    verbose: bool = True,
) -> int:
    if not input_path.exists():
        raise FileNotFoundError(f"PDF 文件不存在: {input_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    src = fitz.open(str(input_path))
    toc = src.get_toc()
    total_pages = len(src)
    chapters = collect_chapters(toc)

    if not chapters:
        src.close()
        raise ValueError(f"未找到含日期的三级章节: {input_path.name}")

    if verbose:
        print(f"处理: {input_path.name}  (共 {total_pages} 页, {len(chapters)} 个章节)")

    used_names: dict[str, int] = {}
    written = 0
    skipped = 0

    for seq, (toc_idx, title, start_page) in enumerate(chapters, start=1):
        page_from = start_page - 1
        page_to = find_page_end(toc, toc_idx, total_pages)

        if page_from < 0 or page_to >= total_pages or page_from > page_to:
            print(f"  [错误] {title}: 页码越界 {page_from + 1}-{page_to + 1}")
            continue

        base_name = sanitize_filename(title)
        if base_name in used_names:
            used_names[base_name] += 1
            out_name = f"{base_name}_{used_names[base_name]}.pdf"
        else:
            used_names[base_name] = 0
            out_name = f"{base_name}.pdf"

        out_path = output_dir / out_name
        if skip_existing and out_path.exists():
            skipped += 1
            if verbose:
                print(f"  [{seq}/{len(chapters)}] 跳过（已存在）: {out_name}")
            continue

        out_doc = fitz.open()
        out_doc.insert_pdf(src, from_page=page_from, to_page=page_to)
        out_doc.save(str(out_path))
        out_doc.close()
        written += 1

        if verbose:
            page_count = page_to - page_from + 1
            print(f"  [{seq}/{len(chapters)}] {out_name} ({page_count} 页)")

    src.close()

    if verbose:
        msg = f"完成: 新写入 {written} 个"
        if skipped:
            msg += f"，跳过 {skipped} 个"
        print(f"{msg} -> {output_dir}\n")
    return written


def split_all(
    input_dir: Path,
    output_base: Path,
    *,
    skip_existing: bool = True,
) -> None:
    pdfs = sorted(input_dir.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"目录下没有 PDF 文件: {input_dir}")

    print(f"输入目录: {input_dir}")
    print(f"输出根目录: {output_base}\n")

    total_written = 0
    for pdf_path in pdfs:
        output_dir = output_base / pdf_path.stem / "pdf"
        try:
            count = split_pdf(pdf_path, output_dir, skip_existing=skip_existing)
            total_written += count
        except (ValueError, FileNotFoundError) as exc:
            print(f"[失败] {pdf_path.name}: {exc}\n")

    print(f"全部完成！共处理 {len(pdfs)} 个 PDF，新写入 {total_written} 个章节文件")


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    force = "--force" in args
    if force:
        args = [a for a in args if a != "--force"]

    skip_existing = not force

    if not args:
        split_all(DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_BASE, skip_existing=skip_existing)
        return

    input_path = Path(args[0])
    if input_path.is_dir():
        output_base = Path(args[1]) if len(args) > 1 else DEFAULT_OUTPUT_BASE
        split_all(input_path, output_base, skip_existing=skip_existing)
        return

    output_dir = (
        Path(args[1])
        if len(args) > 1
        else DEFAULT_OUTPUT_BASE / input_path.stem / "pdf"
    )
    split_pdf(input_path, output_dir, skip_existing=skip_existing)


if __name__ == "__main__":
    main()
