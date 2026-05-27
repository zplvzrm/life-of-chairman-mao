"""
data_etl/import_json.py — 将 JSON 年谱数据批量导入 MySQL chronology 表

用法:
    cd life_of_chairman_mao/
    poetry run python -m life_of_chairman_mao.data_etl.import_json

注意:
    - 每次运行前会清空 chronology 表，避免重复插入
    - JSON 字段 "do" 对应数据库列 "event"
"""
import asyncio
import json
from pathlib import Path

import aiomysql

from ..config import settings

JSON_DIR = Path("/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/毛泽东年谱/textin/json")

INSERT_SQL = """
    INSERT INTO chronology (age, year, month, day, event, annotation)
    VALUES (%s, %s, %s, %s, %s, %s)
"""


async def import_all() -> None:
    pool = await aiomysql.create_pool(
        host=settings.DATABASE.HOST,
        port=int(settings.DATABASE.PORT),
        user=settings.DATABASE.USERNAME,
        password=settings.DATABASE.PASSWORD,
        db=settings.DATABASE.NAME,
        charset="utf8mb4",
        autocommit=False,
    )

    json_files = sorted(JSON_DIR.glob("*.json"))
    print(f"找到 {len(json_files)} 个 JSON 文件\n")

    total = 0
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # 清空旧数据，保证幂等
            await cur.execute("TRUNCATE TABLE chronology")
            await conn.commit()
            print("已清空 chronology 表\n")

            for json_path in json_files:
                with open(json_path, encoding="utf-8") as f:
                    records = json.load(f)

                if not records:
                    print(f"  跳过（空文件）: {json_path.stem}")
                    continue

                rows = [
                    (
                        r["age"],
                        r["year"],
                        r["month"],
                        r["day"],
                        r["do"],
                        r.get("annotation", "") or "",
                    )
                    for r in records
                ]

                await cur.executemany(INSERT_SQL, rows)
                await conn.commit()
                total += len(rows)
                print(f"  {json_path.stem:<28} → {len(rows):>4} 条")

    pool.close()
    await pool.wait_closed()
    print(f"\n全部完成，共导入 {total} 条记录。")


def main() -> None:
    asyncio.run(import_all())


if __name__ == "__main__":
    main()
