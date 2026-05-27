"""将《毛泽东选集》JSON 数据导入 MySQL selected_works 表。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pymysql
import yaml

JSON_DIR = Path(
    "/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/毛泽东选集/json"
)

# 按卷名顺序导入（非文件名字母序）
VOLUME_ORDER = [
    "第一卷",
    "第二卷",
    "第三卷",
    "第四卷",
    "第五卷",
    "第六卷（静火版）",
    "第七卷（静火版）",
]


def load_db_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "settings.local.yml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)["DATABASE"]


def get_json_files() -> list[Path]:
    if not JSON_DIR.is_dir():
        raise FileNotFoundError(f"JSON 目录不存在: {JSON_DIR}")

    files_by_stem = {p.stem: p for p in JSON_DIR.glob("*.json")}
    ordered: list[Path] = []
    missing: list[str] = []

    for volume in VOLUME_ORDER:
        path = files_by_stem.get(volume)
        if path is None:
            missing.append(volume)
            continue
        ordered.append(path)

    if missing:
        raise FileNotFoundError(f"缺少 JSON 文件: {', '.join(missing)}")

    extra = set(files_by_stem) - set(VOLUME_ORDER)
    if extra:
        print(f"提示: 以下 JSON 未在卷序列表中，已跳过: {', '.join(sorted(extra))}")

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
                print("清空 selected_works 表...")
                cursor.execute("TRUNCATE TABLE selected_works")

            json_files = get_json_files()
            print(f"将按卷序导入 {len(json_files)} 个 JSON 文件\n")

            insert_sql = """
                INSERT INTO selected_works
                (age, year, month, day, title, content, annotation, literature_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            for json_file in json_files:
                records = json.loads(json_file.read_text(encoding="utf-8"))
                print(f"处理: {json_file.name}（{len(records)} 条）")

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
