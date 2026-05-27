#!/usr/bin/env python3
"""为 1953 年之前的 JSON 文件添加 literature_id 字段"""

import json
import re
from pathlib import Path


def get_literature_id(year: int) -> int:
    """根据年份返回对应的 literature_id"""
    if year <= 1936:
        return 1
    elif year <= 1945:
        return 2
    elif year <= 1949:
        return 3
    elif year <= 1952:
        return 4
    else:
        return 5


def main():
    json_dir = Path("/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/毛泽东年谱/textin/json")

    # 找到所有 JSON 文件
    json_files = sorted(json_dir.glob("*.json"))

    updated_count = 0
    skipped_count = 0

    for json_file in json_files:
        # 从文件名提取年份
        year_match = re.search(r'(\d{4})', json_file.stem)
        if not year_match:
            print(f"跳过（无法提取年份）: {json_file.name}")
            skipped_count += 1
            continue

        year = int(year_match.group(1))

        # 只处理 1953 年之前的文件
        if year >= 1953:
            continue

        # 读取 JSON 文件
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 检查是否已有 literature_id 字段
        if data and isinstance(data, list) and 'literature_id' in data[0]:
            print(f"跳过（已有 literature_id）: {json_file.name}")
            skipped_count += 1
            continue

        # 获取对应的 literature_id
        literature_id = get_literature_id(year)

        # 为每条记录添加 literature_id
        for record in data:
            record['literature_id'] = literature_id

        # 写回文件
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"更新: {json_file.name} (year={year}, literature_id={literature_id}) -> {len(data)} 条记录")
        updated_count += 1

    print(f"\n完成！更新了 {updated_count} 个文件，跳过了 {skipped_count} 个文件")


if __name__ == "__main__":
    main()
