"""
将年谱 JSON 数据导入到 MySQL chronology 表
只导入 1949年10月之后的数据
"""
import json
import os
from pathlib import Path
import pymysql
from datetime import datetime
import yaml

# 读取数据库配置
config_path = Path(__file__).parent.parent / "config" / "settings.local.yml"
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

db_config = config['DATABASE']

# JSON 文件目录
JSON_DIR = "/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/毛泽东年谱/textin/json"

def get_json_files():
    """获取所有 JSON 文件"""
    json_dir = Path(JSON_DIR)
    files = sorted(json_dir.glob("*.json"))
    return files

def parse_date(year_str, month_str, day_str):
    """解析日期字符串为标准格式"""
    # 处理年份
    if not year_str or year_str == "未知":
        return None

    year = year_str.strip()

    # 处理月份
    if not month_str or month_str == "未知":
        month = "00"
    else:
        month = month_str.strip().zfill(2)

    # 处理日期
    if not day_str or day_str == "未知":
        day = "00"
    else:
        day = day_str.strip().zfill(2)

    return f"{year}-{month}-{day}"

def import_json_to_db():
    """导入 JSON 数据到数据库"""
    # 连接数据库
    conn = pymysql.connect(
        host=db_config['HOST'],
        port=db_config['PORT'],
        user=db_config['USERNAME'],
        password=db_config['PASSWORD'],
        database=db_config['NAME'],
        charset='utf8mb4'
    )

    try:
        cursor = conn.cursor()

        # 清空表（可选，根据需求决定）
        print("清空 chronology 表...")
        cursor.execute("TRUNCATE TABLE chronology")

        json_files = get_json_files()
        print(f"找到 {len(json_files)} 个 JSON 文件")

        total_records = 0

        for json_file in json_files:
            print(f"\n处理文件: {json_file.name}")

            with open(json_file, 'r', encoding='utf-8') as f:
                records = json.load(f)

            print(f"  记录数: {len(records)}")

            for record in records:
                # 解析日期
                date_str = parse_date(
                    record.get('year', ''),
                    record.get('month', ''),
                    record.get('day', '')
                )

                if not date_str:
                    continue

                # 插入数据（使用 INSERT IGNORE 避免重复）
                sql = """
                INSERT IGNORE INTO chronology
                (age, year, month, day, event, annotation, literature_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """

                cursor.execute(sql, (
                    record.get('age', 0),
                    record.get('year', ''),
                    record.get('month', ''),
                    record.get('day', ''),
                    record.get('do', ''),
                    record.get('annotation', ''),
                    record.get('literature_id', 0)
                ))

                total_records += 1

            conn.commit()
            print(f"  已导入 {len(records)} 条记录")

        print(f"\n总计导入 {total_records} 条记录")

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import_json_to_db()
