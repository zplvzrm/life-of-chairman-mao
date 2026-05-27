"""
用法:
  1. 安装依赖： pip install xparse-client
  2. 设置环境变量 TEXTIN_APP_ID 和 TEXTIN_SECRET_CODE
  3. python concert_pdf_to_md_from_textin.py
"""

import os
from pathlib import Path

import yaml
from xparse_client import XParseClient, ParseConfig, Capabilities

INPUT_DIR = Path("/Users/zhangpeng/Data/studies/datas/chairManMao/Selected-Works-of-MaoTseTung-master/毛泽东年谱/pdf版本/2023版本/毛泽东年谱(v2)9")
OUTPUT_DIR = Path("/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/毛泽东年谱/textin/md")

SKIP_STEMS: set = set()

# 从配置文件读取凭证
def load_credentials():
    config_path = Path(__file__).parent.parent.parent / "config" / "settings.local.yml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            return config.get("TEXTIN_APP_ID"), config.get("TEXTIN_SECRET_CODE")
    return None, None


def parse_pdf(client, file_path: Path, output_path: Path):
    print(f"正在解析: {file_path.name}")
    with open(file_path, "rb") as f:
        result = client.parse.run(
            file=f,
            filename=file_path.name,
            config=ParseConfig(
                capabilities=Capabilities(
                    include_table_structure=True,
                    title_tree=True,
                ),
            ),
        )
    print(f"  完成：{len(result.elements)} 个元素，{result.success_count} 页成功")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.markdown)
    print(f"  已保存: {output_path}")


def main():
    # 读取凭证
    app_id, secret_code = load_credentials()
    if not app_id or not secret_code:
        raise ValueError("无法从配置文件读取 TEXTIN_APP_ID 和 TEXTIN_SECRET_CODE")

    client = XParseClient(app_id=app_id, secret_code=secret_code)
    pdfs = sorted(INPUT_DIR.glob("*.pdf"))
    to_process = [p for p in pdfs if p.stem not in SKIP_STEMS]

    print(f"共找到 {len(pdfs)} 个 PDF，跳过 {len(SKIP_STEMS)} 个，待处理 {len(to_process)} 个\n")

    for pdf in to_process:
        output_path = OUTPUT_DIR / f"{pdf.stem}.md"
        if output_path.exists():
            print(f"跳过（已存在）: {pdf.name}")
            continue
        parse_pdf(client, pdf, output_path)

    print("\n全部完成！")


if __name__ == "__main__":
    main()
