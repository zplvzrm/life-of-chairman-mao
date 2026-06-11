在所有任务完成后，如果代码风格、组件结构或技术栈发生了变更，请务必更新本文件。

# 毛泽东年谱 · 项目文档

## 项目概述

- **名称**：教员的一生（life_of_chairman_mao）
- **主题**：毛泽东生平年谱可视化网站，涵盖 1893 年出生至 1976 年逝世，共 84 年
- **目标**：以星空为背景，将 84 年人生轨迹以 84 颗星星呈现，用户点击星星进入对应年份的详情页
- **技术栈**：Python 3.11 · FastAPI · MySQL · aiomysql · 原生 HTML / CSS / JavaScript
- **包管理**：Poetry
- **作者**：zp

---

## 技术架构

| 层级     | 技术                    | 说明                                     |
|----------|-------------------------|------------------------------------------|
| 前端     | 原生 HTML / CSS / JS    | 无框架；localStorage 存匿名 UUID         |
| API      | FastAPI + Uvicorn       | Python 异步，轻量，自动生成 OpenAPI 文档 |
| 数据库   | MySQL                   | `chronology` + `user_visits` 两张表      |
| 异步驱动 | aiomysql                | 异步 MySQL 连接池                        |
| 配置管理 | dynaconf                | 读取 settings.toml / .secrets.toml       |
| 部署     | Uvicorn + Nginx         | 标准 Python 异步部署                     |

---

## 数据来源与格式

原始数据来自《毛泽东年谱》扫描版 PDF，经 TextIn OCR 识别后转为 Markdown，
再由脚本解析为结构化 JSON，按年份存放：

```
/Users/zhangpeng/Data/studies/datas/chairManMao/处理后资料/毛泽东年谱/textin/json/
├── 1893年.json
├── 1894年.json
├── ...
└── 1976年.json
```

每个 JSON 文件为数组，每条记录结构如下：

```json
{
  "age":  12,
  "year": "1905",
  "month": "正月",
  "day":  "初一",
  "do":   "事件正文描述",
  "annotation": "注释或出处（可为空）"
}
```

---

## 项目结构

```
life_of_chairman_mao/
├── src/life_of_chairman_mao/
│   ├── __init__.py
│   ├── cmdline.py                   # CLI 入口
│   ├── log.py                       # 日志配置
│   ├── config/
│   │   └── __init__.py
│   ├── data_process/
│   │   ├── __init__.py
│   │   └── parse/
│   │       ├── __init__.py
│   │       ├── concert_pdf_to_md_from_textin.py   # PDF → Markdown
│   │       ├── parse_nianpu.py                    # 年谱 Markdown/JSON 解析
│   │       ├── parse_wenji_md.py                  # 文集 MD → JSON
│   │       ├── parse_xuanji.py                    # 选集 txt → JSON
│   │       ├── parse_jianguo_wengao_md.py         # 建国以来毛泽东文稿 MD → JSON
│   │       └── parse_zaoqi_wengao_md.py           # 毛泽东早期文稿 MD → JSON
│   ├── data_etl/
│   │   ├── __init__.py
│   │   └── init_sql.sql             # 建库建表 SQL
│   └── api/
│       ├── __init__.py
│       ├── main.py                  # FastAPI 应用入口
│       ├── database.py              # aiomysql 连接池
│       ├── schemas.py               # Pydantic 数据模型
│       └── routers/
│           ├── __init__.py
│           ├── chronology.py        # /api/years  /api/events/{year}  /api/events/adjacent  /api/search
│           └── visits.py            # /api/visit  /api/last-visit/{user_id}
├── web/
│   ├── home.html                    # 首页（星空交互页）
│   ├── detail.html                  # 年份详情页
│   └── images/                      # 背景图片资源
├── docs/
│   └── system_design.md
├── tests/
├── pyproject.toml
└── CLAUDE.md
```

---

## 数据处理流程

```
原始 PDF
  ↓ TextIn OCR
Markdown 文件
  ↓ concert_pdf_to_md_from_textin.py
结构化 Markdown
  ↓ parse_nianpu.py
JSON 文件（按年份）
  ↓ ETL 导入脚本（待开发）
MySQL · chronology 表
  ↓ FastAPI
前端页面
```

---

## 数据库设计（MySQL）

### chronology（年谱事件表）

| 字段       | 类型         | 说明                             |
|------------|--------------|----------------------------------|
| id         | BIGINT AUTO_INCREMENT PRIMARY KEY | 主键          |
| age        | INT          | 年龄                             |
| year       | CHAR(4)      | 公历年份（如 1949）              |
| month      | VARCHAR(10)  | 月份（中文），如 正月            |
| day        | VARCHAR(10)  | 日（中文），如 初一              |
| event      | TEXT         | 事件正文（对应 JSON 中的 do 字段）|
| annotation | TEXT         | 注释 / 出处                      |

索引：`idx_year(year)` · `idx_year_month(year, month)` · `FULLTEXT ft_event(event)`

### manuscript（建国以来毛泽东文稿表）

| 字段          | 类型         | 说明                                      |
|---------------|--------------|-------------------------------------------|
| id            | BIGINT AUTO_INCREMENT PRIMARY KEY | 主键 |
| age           | INT          | 年龄                                      |
| year          | CHAR(4)      | 公历年份                                  |
| month         | VARCHAR(10)  | 月份                                      |
| day           | VARCHAR(10)  | 日                                        |
| title         | TEXT         | 文章标题                                  |
| content       | MEDIUMTEXT   | 文章正文                                  |
| annotation    | MEDIUMTEXT   | 注释 / 出处                               |
| literature_id | BIGINT       | 文献 ID（25–44 对应各册文稿）             |

索引：`idx_year` · `idx_year_month` · `idx_literature_id` · `FULLTEXT ft_event(content)`

### user_visits（用户浏览历史表）

| 字段       | 类型        | 说明                              |
|------------|-------------|-----------------------------------|
| id         | BIGINT AUTO_INCREMENT PRIMARY KEY | 主键           |
| user_id    | CHAR(36)    | 前端生成的匿名 UUID（UNIQUE）     |
| year       | CHAR(4)     | 最后浏览的年份                    |
| month      | VARCHAR(10) | 最后浏览的月份                    |
| day        | VARCHAR(10) | 最后浏览的日                      |
| visited_at | DATETIME    | 最后访问时间（自动更新）          |

每个 user_id 只保留一条记录，通过 `ON DUPLICATE KEY UPDATE` 实现 upsert。

---

## 用户浏览历史追踪方案

**无需注册登录，使用匿名 UUID 实现跨次访问记忆。**

```
用户首次访问
  → 前端：生成 UUID，存入 localStorage（key: "lcm_uid"）
  → 用户点击进入某年某月某日事件
  → 前端：POST /api/visit { user_id, year, month, day }
  → 后端：upsert user_visits 表（同一 user_id 只保留最新记录）

用户再次访问
  → 前端：读取 localStorage 中的 UUID
  → 前端：GET /api/last-visit/{user_id}
  → 后端：返回 { year, month, day } 或 null
  → 前端：高亮对应年份的星星（脉冲闪烁）
  → 用户点击该星星：直接跳转到上次浏览的月份/事件
```

---

## API 路由一览

| 方法 | 路径                        | 说明                           |
|------|-----------------------------|--------------------------------|
| GET  | `/api/years`                | 返回所有有记录的年份列表       |
| GET  | `/api/events/{year}`        | 返回某年所有事件               |
| GET  | `/api/events/adjacent`      | 返回相邻日期（前一日/后一日）  |
| GET  | `/api/search?q=关键词`      | 全文搜索事件正文               |
| GET  | `/api/backgrounds/home`     | 返回首页背景图                 |
| GET  | `/api/backgrounds/detail/{year}` | 返回指定年份详情页背景图  |
| POST | `/api/visit`                | 记录用户最后一次浏览           |
| GET  | `/api/last-visit/{user_id}` | 查询用户上次浏览位置           |

---

## 前端设计

### 首页（home.html）

- **背景**：全屏图片 `web/images/星辰山峰.jpg`（`object-fit: cover`，底部对齐）
- **星云动画**：Canvas 绘制，`normal` 混合模式，覆盖于背景图之上
- **星星层**：Canvas 绘制 84 颗五角星（对应 1893–1976 每年一颗）
  - 星星按椭圆轨迹分布于画面，随机偏移，营造自然感
  - 悬停时发光放大，点击触发涟漪动画
  - **点击交互**：第一次点击→涟漪扩散+星星持续高亮1秒→时空隧道特效→跳转详情页；再次点击同一颗已选中星星→取消选中，不跳转
  - **上次浏览的星星**：额外脉冲闪烁效果，区别于普通星星
- **时空隧道特效**：`#tunnel-overlay`（`position:fixed; inset:0; z-index:200`）覆盖全屏，Canvas 绘制同心椭圆环缩放动画，结束后跳转
- **标题**：`Cinzel` 衬线字体，金色，居中固定于顶部
- **年份搜索框**：右上角胶囊形输入框，输入年份后高亮对应星星并跳转
- **气泡提示**：鼠标悬停星星时，气泡显示年份数字（`Cinzel` 字体，金黄色）
- **底部提示文字**：淡色小字，引导用户点击星星

### 年份详情页（detail.html）

- 独立页面，通过 `?year=1949` URL 参数指定年份；`?month=&day=` 可直接定位到具体日期
- **英雄区**：全屏背景图（由 `/api/backgrounds/detail/{year}` 提供，回退为首页背景），底部渐变遮罩，右上角显示年份与年龄（`Cinzel` 字体，金黄色）
- **返回按钮**：左上角胶囊形按钮，点击返回 `home.html`
- **左侧日期滚筒（day drum）**：可拖拽/滚轮滚动的日期选择条，展示当月所有有数据的日期，选中日高亮放大；月份切换时重建
- **事件卡片**：固定于英雄区底部，显示「年 月 日」格式日期、事件正文（段首空两个全角空格 `\u3000\u3000`）、注释
- **底部月份条（month strip）**：横向展示该年所有有数据的月份，点击切换月份
- **双指触控板手势（wheel 事件）**：
  - 垂直滑动：上划 → 下一条有数据日期，下划 → 上一条有数据日期（跨月自动切换）
  - 水平滑动：右划 → 下一个月，左划 → 上一个月
  - 年份边界自动跳转相邻年份（`?gotoLast=1` 参数表示落地到该年最后一个有数据日期）
- **键盘导航**：↑ = 下一日，↓ = 上一日，→ = 下一月，← = 上一月；与双指滑动效果相同
- **跨年跳转**：`flatDates[]` 平铺全年所有有数据日期，`flatIdx` 追踪当前位置；边界时通过 `window.location.href` 重定向
- **字体风格**：正文使用 `Noto Serif SC`，标题/年份使用 `Cinzel`，整体古典金色调

### 配色基调

| 用途         | 颜色                          |
|--------------|-------------------------------|
| 背景         | 纯黑 `#000`                   |
| 星星 / 标题  | 金黄 `#ffd87a` / `#e8d5a3`   |
| 边框         | `rgba(255,220,100,0.35)`      |
| 正文         | `#f0e8d0`                     |
| 注释         | `rgba(200,180,130,0.5)`       |

---

## 常用命令

| 命令 | 用途 |
|------|------|
| `poetry install` | 安装依赖 |
| `poetry run life_of_chairman_mao` | 运行 CLI |
| `uvicorn life_of_chairman_mao.api.main:app --reload` | 启动 API 开发服务器 |
| `pytest` | 运行测试 |
| `python -m src.life_of_chairman_mao.data_process.parse.parse_nianpu` | 解析年谱 |
| `PYTHONPATH=src python -m life_of_chairman_mao.data_process.parse.parse_jianguo_wengao_md [--force] <册目录或根目录>` | 解析建国以来毛泽东文稿各册 MD → JSON（literature_id 25–44） |
| `PYTHONPATH=src python -m life_of_chairman_mao.data_process.parse.parse_zaoqi_wengao_md [--force] [md目录] [json目录]` | 解析《毛泽东早期文稿》MD → JSON（literature_id 45，正编 131 篇） |
| `PYTHONPATH=src python -m life_of_chairman_mao.data_etl.import_manuscript [--create-table]` | 建表并导入文稿 JSON → `manuscript` 表 |

---

## 开发规范

### Python
- 版本：3.11+
- 格式化：pylint（最大行长 120）
- 排序：isort
- 测试：pytest，测试文件命名 `test_*.py`

### 前端
- 纯原生 HTML / CSS / JavaScript，无框架依赖
- CSS 变量统一管理配色
- JS 逻辑集中在单文件底部 `<script>` 块中
- 不引入构建工具

### Git
- 分支命名：`feature/描述` 或 `fix/描述`
- Commit 格式：conventional commits（`feat:` / `fix:` / `docs:` 等）
- 不提交敏感信息（数据库密码放在 `.secrets.toml`，已加入 `.gitignore`）

---

## 待办事项

- [ ] 将 JSON 数据批量导入 MySQL（ETL 脚本）
- [x] 年份详情页对接真实 API 数据
- [ ] 首页：上次浏览星星脉冲高亮逻辑
- [ ] 星星位置算法优化（避免重叠）
- [ ] 移动端适配
- [ ] 部署方案确定（Nginx 反代 Uvicorn）

---

**最后更新**：2026-06-08
