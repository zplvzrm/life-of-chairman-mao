"""将《毛泽东早期文稿》JSON 数据导入 MySQL early_manuscript 表。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pymysql
import yaml

JSON_DIR = Path(
    "/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/毛泽东早期文稿/json"
)

CREATE_EARLY_MANUSCRIPT_SQL = """
CREATE TABLE IF NOT EXISTS early_manuscript (
    id            BIGINT        NOT NULL AUTO_INCREMENT        COMMENT '主键',
    age           INT           NOT NULL                       COMMENT '年龄',
    year          CHAR(4)       NOT NULL                       COMMENT '公历年份，如 1949',
    month         VARCHAR(10)   NOT NULL DEFAULT ''            COMMENT '月份（中文），如 正月',
    day           VARCHAR(10)   NOT NULL DEFAULT ''            COMMENT '日（中文），如 初一',
    title         TEXT          NOT NULL                       COMMENT '文章标题',
    content       MEDIUMTEXT    NOT NULL                       COMMENT '文章正文',
    annotation    MEDIUMTEXT                                   COMMENT '注释 / 出处，可为空',
    literature_id BIGINT        NULL                           COMMENT '文献 ID，关联 literature 表',

    PRIMARY KEY (id),
    INDEX idx_year          (year),
    INDEX idx_year_month    (year, month),
    INDEX idx_literature_id (literature_id),
    FULLTEXT INDEX ft_event (content)
)   ENGINE  = InnoDB
    DEFAULT CHARSET  = utf8mb4
    COLLATE = utf8mb4_unicode_ci
    COMMENT = '毛泽东早期文稿 1912·06-1920·11'
"""


def load_db_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "settings.local.yml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)["DATABASE"]


def connect_db(db_config: dict) -> pymysql.connections.Connection:
    return pymysql.connect(
        host=db_config["HOST"],
        port=db_config["PORT"],
        user=db_config["USERNAME"],
        password=db_config["PASSWORD"],
        database=db_config["NAME"],
        charset="utf8mb4",
    )


def ensure_early_manuscript_table(conn: pymysql.connections.Connection) -> None:
    with conn.cursor() as cursor:
        cursor.execute(CREATE_EARLY_MANUSCRIPT_SQL)
    conn.commit()
    print("已确认 early_manuscript 表存在")


def sort_key(record: dict) -> tuple[str, str, str, str]:
    return (
        str(record.get("year", "")),
        str(record.get("month", "")).zfill(2),
        str(record.get("day", "")).zfill(2),
        str(record.get("title", "")),
    )


def get_json_files() -> list[Path]:
    if not JSON_DIR.is_dir():
        raise FileNotFoundError(f"JSON 目录不存在: {JSON_DIR}")

    files = sorted(JSON_DIR.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"目录中未找到 JSON 文件: {JSON_DIR}")
    return files


def load_records(json_files: list[Path]) -> list[dict]:
    records: list[dict] = []
    for json_file in json_files:
        data = json.loads(json_file.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"JSON 格式错误（应为数组）: {json_file}")
        print(f"读取: {json_file.name}（{len(data)} 条）")
        records.extend(data)
    records.sort(key=sort_key)
    return records


def import_json_to_db(*, truncate: bool = True, create_table: bool = False) -> int:
    db_config = load_db_config()
    conn = connect_db(db_config)

    total_records = 0
    try:
        if create_table:
            ensure_early_manuscript_table(conn)

        json_files = get_json_files()
        records = load_records(json_files)
        print(f"\n合并后共 {len(records)} 条，按日期顺序写入 early_manuscript 表\n")

        with conn.cursor() as cursor:
            if truncate:
                print("清空 early_manuscript 表...")
                cursor.execute("TRUNCATE TABLE early_manuscript")

            insert_sql = """
                INSERT INTO early_manuscript
                (age, year, month, day, title, content, annotation, literature_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

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
            print(f"总计导入 {total_records} 条记录")
    finally:
        conn.close()

    return total_records


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    truncate = "--no-truncate" not in args
    create_table = "--create-table" in args
    import_json_to_db(truncate=truncate, create_table=create_table)


if __name__ == "__main__":
    main()
