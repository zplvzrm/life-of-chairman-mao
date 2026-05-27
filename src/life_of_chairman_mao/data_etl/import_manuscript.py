"""将《建国以来毛泽东文稿》JSON 数据导入 MySQL manuscript 表。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pymysql
import yaml

BASE_DIR = Path(
    "/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/建国以来毛泽东文稿"
)

VOLUME_NUM_RE = re.compile(r"第\s*0*(\d+)\s*册")

CREATE_MANUSCRIPT_SQL = """
CREATE TABLE IF NOT EXISTS manuscript (
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
    COMMENT = '建国以来毛泽东文稿表'
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


def ensure_manuscript_table(conn: pymysql.connections.Connection) -> None:
    with conn.cursor() as cursor:
        cursor.execute(CREATE_MANUSCRIPT_SQL)
    conn.commit()
    print("已确认 manuscript 表存在")


def sort_key(record: dict) -> tuple[str, str, str, str]:
    return (
        str(record.get("year", "")),
        str(record.get("month", "")).zfill(2),
        str(record.get("day", "")).zfill(2),
        str(record.get("title", "")),
    )


def get_json_files() -> list[Path]:
    if not BASE_DIR.is_dir():
        raise FileNotFoundError(f"文稿目录不存在: {BASE_DIR}")

    volumes = [
        p for p in BASE_DIR.iterdir()
        if p.is_dir() and VOLUME_NUM_RE.search(p.name) and (p / "json").is_dir()
    ]

    def vol_sort_key(path: Path) -> int:
        match = VOLUME_NUM_RE.search(path.name)
        return int(match.group(1)) if match else 999

    volumes.sort(key=vol_sort_key)

    ordered: list[Path] = []
    missing: list[str] = []

    for vol_dir in volumes:
        json_path = vol_dir / "json" / f"{vol_dir.name}.json"
        if not json_path.is_file():
            missing.append(vol_dir.name)
            continue
        ordered.append(json_path)

    if missing:
        raise FileNotFoundError(f"缺少 JSON 文件: {', '.join(missing)}")

    return ordered


def import_json_to_db(*, truncate: bool = True, create_table: bool = False) -> int:
    db_config = load_db_config()
    conn = connect_db(db_config)

    total_records = 0
    try:
        if create_table:
            ensure_manuscript_table(conn)

        with conn.cursor() as cursor:
            if truncate:
                print("清空 manuscript 表...")
                cursor.execute("TRUNCATE TABLE manuscript")

            json_files = get_json_files()
            print(f"将按册序及日期顺序导入 {len(json_files)} 个 JSON 文件\n")

            insert_sql = """
                INSERT INTO manuscript
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
    create_table = "--create-table" in args
    import_json_to_db(truncate=truncate, create_table=create_table)


if __name__ == "__main__":
    main()
