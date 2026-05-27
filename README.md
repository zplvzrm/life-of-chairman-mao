# life-of-chairman-mao

## 1. Overview

毛主席的一生。

## 2. Usage

### 2.1 init project

```bash
poetry install -v
```

### 2.2 usage

TODO

## 3. Develop

You may need to read the [develop document](./docs/development.md) to use SRC Layout in your IDE.
# life-of-chairman-mao



  1. 确保 MySQL 已运行，并初始化数据库

  # 首次运行（建库建表）
  mysql -u root -p < src/life_of_chairman_mao/data_etl/init_sql.sql

  2. 配置数据库连接

  在项目根目录创建 .secrets.toml（不提交到 git）：

  [default]
  db_host = "127.0.0.1"
  db_port = 3306
  db_user = "root"
  db_password = "你的密码"
  db_name = "jiaoyuan"

  3. 安装依赖并启动后端

  poetry install
  poetry run uvicorn life_of_chairman_mao.api.main:app --reload --port 8000

  后端启动后访问 http://127.0.0.1:8000/docs 可确认 API 是否正常。

  4. 启动前端静态服务器

  cd web
  python3 -m http.server 8080

  浏览器打开 http://localhost:8080/home.html

  ---
  5. 插入一张首页背景图（否则背景为纯黑）

  USE jiaoyuan;
  INSERT INTO background_images (scene_type, image_url, mime_type, title)
  VALUES ('home', 'https://images.unsplash.com/photo-1419242902214-272b3f66ee7a?w=1920', 'image/jpeg', '星空背景');

  ---
  验证效果

  - 首页加载：84 颗星星出现在星空背景上
  - 点击任意星星：播放隧道动画 → 跳转到 detail.html?year=XXXX
  - 详情页：加载对应年份的事件（需要 chronology 表有数据），月份导航栏高亮有数据的月份

  如果 chronology 表还没有数据，详情页会显示"暂无该年份记录"，这是正常的——需要先跑 ETL 把 JSON 导入数据库。
