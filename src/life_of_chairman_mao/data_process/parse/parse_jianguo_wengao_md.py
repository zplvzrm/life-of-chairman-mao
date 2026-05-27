"""parse_jianguo_wengao_md.py — 将《建国以来毛泽东文稿》各册 MD 解析为结构化 JSON。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from life_of_chairman_mao.data_process.parse.parse_wenji_md import (
    DATE_FIELD_RE,
    extract_cn_dates,
    extract_title,
    find_section,
    merge_body_paragraphs,
    parse_annotations,
)
from life_of_chairman_mao.data_process.parse.parse_xuanji import (
    CN_DIGIT,
    MAO_BIRTH,
    cn_to_int,
    format_title,
    norm_fn,
    parse_chinese_date,
)

DEFAULT_BASE_DIR = Path(
    "/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/建国以来毛泽东文稿"
)
DEFAULT_VOLUME = "建国以来毛泽东文稿_第1册（1949年9月-1950年2月）"

VOLUME_NUM_RE = re.compile(r"第\s*0*(\d+)\s*册")

# 册号 1–20 对应 literature_id 25–44
VOLUME_LITERATURE_ID = {vol: 24 + vol for vol in range(1, 21)}

# 《中国农村的社会主义高潮》按语：十九篇写于 1955 年 9 月，其余为 12 月（见第 10 册注释）
CHAONAO_ANWEI_SEPTEMBER_SERIALS = frozenset({
    7, 24, 31, 40, 44, 45, 53, 70, 72, 76, 82, 85, 90, 93, 94, 96, 98, 99, 102,
})

ANWEI_STEM_PREFIX_RE = re.compile(r"^([一二三四五六七八九十〇零○O百]+)")
AMBIGUOUS_MONTH_RE = re.compile(r"九月.*十二月|十二月.*九月|、")

# OCR 将注释角标 [n] 误识为 C 1 ]、( l J、叩1 志 等
_OCR_DIGIT = r"[0-9lI|]"
_OCR_NUM = rf"(?:{_OCR_DIGIT}(?:\s*{_OCR_DIGIT})*)"
_FN_OPEN = r"[\[(（C［【]"
_FN_CLOSE = r"[\]\)J\]】]"
_FN_AFTER = r"(?:同志|兄|先生|：|:|阅)"


def ocr_footnote_num_to_str(raw: str) -> str:
    """将 OCR 数字串（含 l/I 作 1、空格分位）转为阿拉伯数字字符串。"""
    digits = re.findall(_OCR_DIGIT, raw)
    return "".join("1" if ch in "lI|" else ch for ch in digits)


def norm_jianguo_footnotes(text: str) -> str:
    """建国文稿专用：将正文/注释中的 OCR 角标统一为 [i] 格式。"""
    text = norm_fn(text)

    def marker(raw: str) -> str:
        return f"[{ocr_footnote_num_to_str(raw)}]"

    def marker_tongzhi(raw: str) -> str:
        return f"{marker(raw)}同志"

    # 「同志」OCR：侗志、伺志、叩1志、叩寸志、沛寸志 等
    _tongzhi_ocr = r"(?:侗|伺|沛\s*寸|叩\s*(?:寸|[01lI|]))\s*志"
    for prefix in (
        rf"C\s*({_OCR_NUM})\s*",
        rf"\[\s*({_OCR_NUM})\s*",
        rf"\(\s*({_OCR_NUM})\s*",
        rf"（\s*({_OCR_NUM})\s*",
    ):
        text = re.sub(
            prefix + _tongzhi_ocr,
            lambda m: marker_tongzhi(m.group(1)),
            text,
        )

    # C 1 叩1 志（志前无「同」字变体）
    text = re.sub(
        rf"C\s*({_OCR_NUM})\s*(?:叩\s*[01lI|]\s*)?志",
        lambda m: marker_tongzhi(m.group(1)),
        text,
    )
    # ( 1 侗志、( l 唯1 志、( l 伺志、( 2 叩1 志
    for suffix in (
        r"侗\s*志",
        r"唯\s*[01lI|]\s*志",
        r"伺\s*志",
        r"叩\s*[01lI|]\s*志",
    ):
        text = re.sub(
            rf"\(\s*({_OCR_NUM})\s*{suffix}",
            lambda m: marker_tongzhi(m.group(1)),
            text,
        )

    # C 1 』（角标右括号误识）
    text = re.sub(
        rf"C\s*({_OCR_NUM})\s*』",
        lambda m: marker(m.group(1)),
        text,
    )

    # [(（C… n …] / J / )，如 C 1 ]、( l J、[ l ]
    text = re.sub(
        rf"{_FN_OPEN}\s*({_OCR_NUM})\s*{_FN_CLOSE}",
        lambda m: marker(m.group(1)),
        text,
    )

    # 彭C l J 阅、李克农C l J 同志
    text = re.sub(
        rf"C\s*({_OCR_NUM})\s*{_FN_CLOSE}?\s*(?={_FN_AFTER})",
        lambda m: marker(m.group(1)),
        text,
    )

    # 鹤鸣( l J 兄、刘、周( l J 阅
    text = re.sub(
        rf"\(\s*({_OCR_NUM})\s*{_FN_CLOSE}?\s*(?={_FN_AFTER})",
        lambda m: marker(m.group(1)),
        text,
    )

    # 句末残留：( l J
    text = re.sub(
        rf"\(\s*({_OCR_NUM})\s*{_FN_CLOSE}?\s*$",
        lambda m: marker(m.group(1)),
        text,
        flags=re.MULTILINE,
    )

    # 规范化已有 [ i ] 写法
    text = re.sub(r"\[\s*(\d+)\s*\]", r"[\1]", text)
    return text


def normalize_jianguo_date_text(text: str) -> str:
    """修正建国以来毛泽东文稿 OCR 常见日期写法。"""
    text = re.sub(r"\s+", "", text)
    text = text.replace("O", "○")
    text = re.sub(r"([一二三四五六七八九])0", r"\1○", text)
    text = re.sub(r"一九五0", "一九五○", text)
    text = re.sub(r"一九五年", "一九五○年", text)
    # 缺「○/零」：一九六年 → 一九六○年（1960 年代常见 OCR）
    text = re.sub(r"一九([一二三四五六七八九])年", r"一九\1○年", text)
    return text


def parse_jianguo_chinese_date(date_text: str) -> tuple[str, str, str] | None:
    return parse_chinese_date(normalize_jianguo_date_text(date_text))


def cn_serial_to_int(token: str) -> int | None:
    """解析按语文件名前缀序号，如 三十七、一〇四。"""
    token = token.replace("O", "○").replace("〇", "○")
    if "○" in token or "零" in token:
        digits: list[int] = []
        for ch in token:
            if ch in ("○", "零"):
                digits.append(0)
            elif ch in CN_DIGIT:
                digits.append(CN_DIGIT[ch])
            else:
                return None
        if len(digits) >= 2:
            return int("".join(str(d) for d in digits))

    if "百" in token:
        hundreds_part, rest = token.split("百", 1)
        hundreds = cn_to_int(hundreds_part) if hundreds_part else 1
        if hundreds is None:
            return None
        if rest.startswith("零"):
            rest = rest[1:]
        tail = cn_to_int(rest) if rest else 0
        if tail is None:
            return None
        return hundreds * 100 + tail

    return cn_to_int(token)


def parse_anwei_serial(stem: str) -> int | None:
    if "一文按语" not in stem:
        return None
    match = ANWEI_STEM_PREFIX_RE.match(stem)
    if not match:
        return None
    return cn_serial_to_int(match.group(1))


def chaoanwei_date_for_serial(serial: int) -> tuple[str, str, str]:
    month = "09" if serial in CHAONAO_ANWEI_SEPTEMBER_SERIALS else "12"
    return "1955", month, "01"


def extract_jianguo_date_text(
    lines: list[str],
    stem: str,
    body_start: int | None = None,
    body_end: int | None = None,
    *,
    allow_full_file_scan: bool = True,
) -> str | None:
    """从 **日期** 行、文件名或正文首段中提取中文日期串（含 OCR 修正）。"""
    for line in lines:
        match = DATE_FIELD_RE.match(line.strip())
        if match:
            candidate = normalize_jianguo_date_text(match.group(1))
            if not AMBIGUOUS_MONTH_RE.search(candidate):
                if parse_jianguo_chinese_date(candidate):
                    return candidate

    for raw in reversed(extract_cn_dates(stem)):
        candidate = normalize_jianguo_date_text(raw)
        if parse_jianguo_chinese_date(candidate):
            return candidate

    if body_start is not None:
        end = body_end if body_end is not None else len(lines)
        for line in lines[body_start + 1: end]:
            stripped = line.strip()
            if not stripped:
                continue
            for raw in extract_cn_dates(stripped):
                candidate = normalize_jianguo_date_text(raw)
                if parse_jianguo_chinese_date(candidate):
                    return candidate
            break

    if allow_full_file_scan:
        for line in lines:
            for raw in extract_cn_dates(line):
                candidate = normalize_jianguo_date_text(raw)
                if parse_jianguo_chinese_date(candidate):
                    return candidate

    return None


def resolve_chaonao_anwei_date(
    lines: list[str],
    stem: str,
    body_start: int,
    body_end: int,
    serial: int,
) -> tuple[str, str, str]:
    """高潮按语：优先明确 **日期**，否则按篇目序号推断 1955-09/12-01。"""
    for line in lines:
        match = DATE_FIELD_RE.match(line.strip())
        if not match:
            continue
        candidate = normalize_jianguo_date_text(match.group(1))
        if AMBIGUOUS_MONTH_RE.search(candidate):
            break
        parsed = parse_jianguo_chinese_date(candidate)
        if parsed:
            return parsed

    date_text = extract_jianguo_date_text(
        lines, stem, body_start, body_end, allow_full_file_scan=False
    )
    if date_text:
        parsed = parse_jianguo_chinese_date(date_text)
        if parsed:
            return parsed

    return chaoanwei_date_for_serial(serial)


def literature_id_for_volume(vol_dir_name: str) -> int:
    match = VOLUME_NUM_RE.search(vol_dir_name)
    if not match:
        raise ValueError(f"无法从目录名解析册号: {vol_dir_name}")
    vol_num = int(match.group(1))
    if vol_num not in VOLUME_LITERATURE_ID:
        raise ValueError(f"不支持的册号: {vol_num}（目录: {vol_dir_name}）")
    return VOLUME_LITERATURE_ID[vol_num]


def parse_md_file(md_path: Path, literature_id: int) -> dict | None:
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    stem = md_path.stem

    body_start = find_section(lines, "正文")
    if body_start is None:
        return None

    anno_start = find_section(lines, "注释")
    body_end = anno_start if anno_start is not None else len(lines)

    vol_num = literature_id - 24
    anwei_serial = parse_anwei_serial(stem) if vol_num == 10 else None

    if anwei_serial is not None:
        year, month, day = resolve_chaonao_anwei_date(
            lines, stem, body_start, body_end, anwei_serial
        )
    else:
        date_text = extract_jianguo_date_text(lines, stem, body_start, body_end)
        if not date_text:
            return None
        parsed = parse_jianguo_chinese_date(date_text)
        if not parsed:
            return None
        year, month, day = parsed

    title_raw = extract_title(lines, stem, body_start, body_end)
    title = format_title(norm_jianguo_footnotes(title_raw))
    content = merge_body_paragraphs(lines[body_start + 1: body_end])
    content = norm_jianguo_footnotes(content)

    annotation = ""
    if anno_start is not None:
        annotation = parse_annotations(lines[anno_start + 1:])
        annotation = norm_jianguo_footnotes(annotation)

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
    literature_id = literature_id_for_volume(vol_name)

    md_dir = vol_dir / "md"
    json_dir = vol_dir / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    out_path = json_dir / f"{vol_name}.json"

    if skip_existing and out_path.exists():
        if verbose:
            print(f"跳过（已存在）: {out_path}")
        return 0, []

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
        print(f"literature_id: {literature_id}")
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
        if p.is_dir() and VOLUME_NUM_RE.search(p.name) and (p / "md").is_dir()
    )

    def vol_sort_key(path: Path) -> int:
        match = VOLUME_NUM_RE.search(path.name)
        return int(match.group(1)) if match else 999

    volumes.sort(key=vol_sort_key)

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
    if (input_path / "md").is_dir():
        convert_volume(input_path, skip_existing=skip_existing)
        return

    if input_path == DEFAULT_BASE_DIR or input_path.name == "建国以来毛泽东文稿":
        convert_all_volumes(input_path, skip_existing=skip_existing)
        return

    raise SystemExit(f"无法识别的路径: {input_path}")


if __name__ == "__main__":
    main()
