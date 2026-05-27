"""将《毛泽东文集》JSON 数据导入 MySQL collected_works 表。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pymysql
import yaml

BASE_DIR = Path(
    "/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/毛泽东文集"
)

# 按卷名顺序导入
VOLUME_ORDER = [
    "毛泽东文集第一卷",
    "毛泽东文集第二卷",
    "毛泽东文集第三卷",
    "毛泽东文集第四卷",
    "毛泽东文集第五卷",
    "毛泽东文集第六卷",
    "毛泽东文集第七卷",
    "毛泽东文集第八卷",
]

def load_db_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "settings.local.yml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)["DATABASE"]


def sort_key(record: dict) -> tuple[str, str, str, str]:
    """按年、月、日排序（同卷内）。"""
    return (
        str(record.get("year", "")),
        str(record.get("month", "")).zfill(2),
        str(record.get("day", "")).zfill(2),
        str(record.get("title", "")),
    )


def get_json_files() -> list[Path]:
    if not BASE_DIR.is_dir():
        raise FileNotFoundError(f"文集目录不存在: {BASE_DIR}")

    ordered: list[Path] = []
    missing: list[str] = []

    for volume in VOLUME_ORDER:
        json_path = BASE_DIR / volume / "json" / f"{volume}.json"
        if not json_path.is_file():
            missing.append(volume)
            continue
        ordered.append(json_path)

    if missing:
        raise FileNotFoundError(f"缺少 JSON 文件: {', '.join(missing)}")

    return ordered


def import_json_to_db(*, truncate: bool = True) -> int:
    db_config = load_db_config()
    conn = pymysql.connect(
        host=db_config["HOST"],
        port=db_config["PORT"],
        user=db_config["USERNAME"],
        password=db_config["PASSWORD"],
        database=db_config["NAME"],
        charset="utf8mb4",
    )

    total_records = 0
    try:
        with conn.cursor() as cursor:
            if truncate:
                print("清空 collected_works 表...")
                cursor.execute("TRUNCATE TABLE collected_works")

            json_files = get_json_files()
            print(f"将按卷序及日期顺序导入 {len(json_files)} 个 JSON 文件\n")

            insert_sql = """
                INSERT INTO collected_works
                (age, year, month, day, title, content, annotation, literature_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            for json_file in json_files:
                records = json.loads(json_file.read_text(encoding="utf-8"))
                records.sort(key=sort_key)
                volume_name = json_file.parent.parent.name
                print(f"处理: {volume_name}（{len(records)} 条）")

                for record in records:
                    cursor.execute(
                        insert_sql,
                        (
                            record.get("age", 0),
                            record.get("year", ""),
                            record.get("month", ""),
                            record.get("day", ""),
                            record.get("title", ""),
                            record.get("content", ""),
                            record.get("annotation", "") or "",
                            record.get("literature_id"),
                        ),
                    )
                    total_records += 1

                conn.commit()

            print(f"\n总计导入 {total_records} 条记录")
    finally:
        conn.close()

    return total_records


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    truncate = "--no-truncate" not in args
    import_json_to_db(truncate=truncate)


if __name__ == "__main__":
    main()
