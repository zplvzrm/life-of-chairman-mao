# 前端实现说明（web/）

本项目前端为**纯原生 HTML / CSS / JavaScript**，无 React/Vue 等框架，无构建工具。逻辑集中在各页面底部 `<script>` 中，通过 FastAPI 后端（默认 `http://127.0.0.1:8000/api`）读取 MySQL 年谱数据。

---

## 目录结构

```
web/
├── home.html          # 首页：星空 + 84 颗年份星星
├── detail.html        # 年份详情页：事件浏览
└── images/
    ├── 星辰山峰.jpg    # 首页默认背景
    ├── 红日初升.jpg    # 详情页默认背景
    └── jiaoyuan/       # 按年份的人物肖像（如 1913.png）
        ├── 1913.png
        ├── 1919.png
        └── 1920.png
```

---

## 技术栈与约定

| 项目 | 说明 |
|------|------|
| 样式 | 页面内 `<style>`，CSS 变量与金色古典配色 |
| 字体 | Google Fonts：`Cinzel`（标题/年份）、`Noto Serif SC`（正文） |
| 绘图 | Canvas 2D（星云、星星、时空隧道） |
| 数据 | `fetch` 调用 REST API；首页星星坐标为**内嵌硬编码** |
| API 基址 | `const API_BASE = 'http://127.0.0.1:8000/api'`（两页均定义） |

---

## 页面关系与导航流

```mermaid
flowchart LR
  home[home.html 星空首页]
  detail[detail.html 年份详情]
  home -->|点击星星 + 隧道动画| detail
  detail -->|返回星空按钮| home
  detail -->|跨年/跨月边界| detail
```

| 跳转方式 | URL 示例 |
|----------|----------|
| 首页 → 详情 | `detail.html?year=1949` |
| 详情定位到月日 | `detail.html?year=1949&month=四月&day=初一` |
| 跨年落到上一年末日 | `detail.html?year=1948&gotoLast=1` |

---

## 一、首页 `home.html`

### 1.1 页面职责

以全屏山景 + 星云 + **84 颗五角星**（1893–1976 每年一颗）呈现毛泽东一生时间轴；用户悬停/搜索高亮年份，点击进入对应年份详情页。

### 1.2 UI 组件一览

| 组件 | DOM / 选择器 | 功能 | 数据来源 |
|------|----------------|------|----------|
| 背景图 | `#bg` | 全屏封面，`object-fit: cover`，底部对齐 | 静态：`images/星辰山峰.jpg` |
| 星云层 | `#nebula`（Canvas） | 22 朵径向渐变云团漂移，仅绘制画面上方 62%（天空区） | **运行时生成**（随机位置/速度/色相） |
| 星星层 | `#starCanvas`（Canvas） | 绘制 84 颗可交互五角星 | **硬编码数组 `stars[]`**（year, x%, y%, size, color, opacity） |
| 标题区 | `.title-block` | 中英文标题「教员的一生 · 1893—1976」 | 静态文案 |
| 年份搜索 | `#search-box` / `#yearInput` | 输入 1893–1976，高亮并 pin 对应星星，显示 tooltip | 用户输入 + `stars[]` 查找 |
| 气泡提示 | `#tooltip` | 悬停或搜索时显示年份、年龄 | `stars[i].year`，年龄 = year − 1893 |
| 底部提示 | `#hint` | 引导文案 | 静态 |
| 点击涟漪 | `.ripple`（动态创建） | 点击星星时的扩散动画 | 纯 CSS 动画 |
| 时空隧道 | `#tunnel-overlay` / `#tunnel-canvas` | 跳转详情前的全屏椭圆环缩放 + 渐亮 | **Canvas 动画**（`runTunnel()`） |

> **说明**：`home.html` 中已定义 `API_BASE`，但当前**未调用** `/api/backgrounds/home`、`/api/visit` 等接口；背景图与星星布局均不依赖后端。浏览历史 API 在设计文档中已规划，前端尚未接入。

### 1.3 核心逻辑模块

#### （1）星云 `drawNebula(t)`

- 维护 `clouds[]`（位置、速度、半径、色相、透明度）。
- 每帧清空画布，在天空裁剪区内绘制径向渐变圆。
- 水平环绕、垂直在天空区内反弹。

#### （2）星星渲染 `drawOneStar` / `starPath` / `drawGlow`

- 五角星路径 + 多层径向发光。
- 状态：`hoveredIdx`（悬停）、`selectedIdx`（点击选中）、`pinnedIdx`（搜索框锁定）。
- 空闲态随机 `flicker`（6–24 秒触发一次短暂闪烁）。

#### （3）主循环 `animate()`

每帧依次：`drawNebula` → 清空星星画布 → 遍历 `stars` 绘制。

#### （4）鼠标交互

- `mousemove`：距离检测（阈值约 `size*2.5+14` px），更新 `hoveredIdx` 与 tooltip 位置；近顶/近底时 tooltip 箭头方向切换（`positionTooltip`）。
- `click`：同一颗星再次点击取消选中；否则涟漪 → `selectedIdx` → 1s 后 `runTunnel` → `location.href = detail.html?year=...`。
- `mouseleave`：清除悬停。

#### （5）年份搜索 `yearInput`

- `input` 事件：校验范围，合法则 `pinnedIdx = findIndex(year)` 并短暂显示 tooltip。
- `keydown` 阻止冒泡，避免与全局快捷键冲突。

#### （6）时空隧道 `runTunnel(onDone)`

- 约 1.1s 动画：28 个椭圆环外扩 + 暗角 + 末尾金光；结束后执行回调（页面跳转）。

### 1.4 响应式

`resize` 时同步重置 `#nebula` 与 `#starCanvas` 尺寸。

---

## 二、详情页 `detail.html`

### 2.1 页面职责

展示**某一公历年份**的年谱事件：全屏背景、年份/年龄/肖像、按**月**切换、按**日**滚筒选择，卡片展示当日事件正文与注释；支持触控板双指滑动、键盘与跨年导航。

### 2.2 UI 组件一览

| 组件 | DOM / 选择器 | 功能 | 数据来源 |
|------|----------------|------|----------|
| 加载遮罩 | `#loading` | 背景图加载完成前全屏 LOADING | 本地状态 |
| 英雄区 | `#detail-hero` | 主视觉区域（flex 占满剩余高度） | — |
| 背景图 | `#detail-bg-img` | 年份详情背景，默认压暗 | API：`GET /api/backgrounds/detail/{year}`；失败则用 `images/红日初升.jpg` |
| 渐变遮罩 | `#detail-hero-overlay` | 底部加深，保证文字可读 | CSS 渐变 |
| 返回按钮 | `#detail-back` | 链接回 `home.html` | 静态 |
| 年份徽章 | `#detail-yr-num` | 大号年份数字 | URL 参数 `year` |
| 年龄标签 | `#detail-age-tag` | 「N 岁」 | 计算：`Number(year) - 1893` |
| 人物肖像 | `#detail-portrait` | 右上角可选 PNG | 静态：`images/jiaoyuan/{year}.png`（无图则隐藏） |
| 事件卡片 | `#detail-content-card` | 底部浮层，展示日期 + 正文 + 注释 + 出处 | API 事件数据 + 本地滚动 |
| 事件日期 | `#detail-event-date` | 「YYYY 年 M月 D日」 | 当前选中日 |
| 事件正文 | `#detail-event-text` | 段首两个全角空格；多日多条用 `.event-block` | `event` 字段 |
| 注释 | `#detail-event-annotation` | 斜体小字 | `annotation` 字段 |
| 出处 | `#detail-event-source` | 右对齐，文献名 | `literature_title`（JOIN `literature` 表） |
| 日期滚筒 | `#detail-day-panel` / `#day-drum` | 左侧滑入；可拖拽/滚轮；选中项居中高亮 | 当月有数据的日期列表 |
| 月份条 | `#detail-month-strip` | 底部 12 格样式 Tab，仅有数据的月份带 `has-data` | `yearEvents` 去重 `month` |

### 2.3 核心数据结构与 API

#### 初始化

```javascript
const params = new URLSearchParams(location.search);
const year = params.get('year') || ...
```

#### `loadPage()` 数据加载（页面入口）

| 步骤 | 接口 | 写入 | 数据库表 |
|------|------|------|----------|
| 1 | `GET /api/backgrounds/detail/{year}` | `#detail-bg-img.src`（`image_url` 或 base64） | `background_images` |
| 2 | `GET /api/events/{year}` | `window.yearEvents` | `chronology` LEFT JOIN `literature` |

**事件对象字段**（与后端 `Event` 模型一致）：

| 字段 | 含义 |
|------|------|
| `id` | 主键 |
| `age` | 年龄 |
| `year` | 公历年份 |
| `month` | 中文月份（如 `四月`） |
| `day` | 中文日（如 `初一`） |
| `event` | 事件正文 |
| `annotation` | 注释（可为空） |
| `literature_title` | 文献名称（可为空） |

### 2.4 核心逻辑模块

#### （1）`buildFlatDates()`

将全年事件按 `month` 顺序、再按 `day` 聚合成 `flatDates[]`：

```javascript
{ day, month, events: [...] }  // 同一月同日多条合并
```

用于**纵向跨日**导航（上一条/下一条有数据日期）。

#### （2）`selectMonth(month, jumpToDay?)`

- 设置 `detailMonth`，高亮月份 Tab。
- 过滤 `yearEvents` 生成 `drumEvents`（当月每日一组）。
- 重建 `#day-drum` DOM（`.day-item` 列表 + 上下 padding 使选中项居中）。
- 打开 `#detail-day-panel`，调用 `selectDayGroup` 显示首日或 `jumpToDay`。

#### （3）`selectDayGroup(dayGroup)`

- 同步 `flatIdx`、滚筒 `activeIdx`、月份 Tab。
- 卡片淡入淡出更新日期、正文、注释、出处。
- 调用 `resetTextScroll()` 重置正文滚动偏移。

#### （4）日期滚筒交互 `initDrumScroll`

- `mousedown` + `mousemove` / `mouseup`：拖拽滚动，`snapTo` 吸附最近日。
- `wheel` on panel：滚轮滚动滚筒。
- `snapTo(idx)`：更新 `drumOffset` 与 `.active` 样式。

#### （5）正文滚动 `scrollText` / `getTextScrollMax`

- 对 `#detail-text-inner` 使用 `translateY` 实现卡片内滚动。
- 到达顶部/底部后继续滑动，累积 `boundaryAccY`，触发 `navigateFlat(±1)` 切换日期。

#### （6）`navigateFlat(delta)` / `navigateMonth(delta)`

- **跨日**：在 `flatDates` 中前后移动；越界则 `window.location` 到相邻年份（`gotoLast=1` 表示上一年最后一天）。
- **跨月**：在 `monthOrder` 中切换；越界同样跨年跳转。

#### （7）双指触控板 `wheel`（绑定在 `#detail-hero`）

| 手势 | 行为 |
|------|------|
| 水平滑动（`|deltaX| > |deltaY|`） | 累积超过阈值 → `navigateMonth(±1)` |
| 垂直滑动 | 优先滚动正文；边界处切换上/下一有数据日 |

带 `WHEEL_COOLDOWN`（600ms）防抖。

#### （8）键盘导航

| 按键 | 行为 |
|------|------|
| ↑ / ↓ | 正文滚动；到顶/底后 `navigateFlat(-1/+1)` |
| ← / → | `navigateMonth(-1/+1)` |

#### （9）URL 落地逻辑（`loadPage` 末尾）

优先级：`gotoLast=1` → `month` + `day` 参数 → 第一个有数据的月份 → `showNoData()`。

### 2.5 全局状态变量

| 变量 | 作用 |
|------|------|
| `window.yearEvents` | 当年全部 API 事件 |
| `flatDates` / `flatIdx` | 全年扁平日期序与当前索引 |
| `drumEvents` / `activeIdx` / `drumOffset` | 当月滚筒数据与滚动位置 |
| `detailMonth` | 当前选中月份 |
| `textScrollOffset` | 正文垂直滚动像素 |
| `wheelLocked` / `wheelAccX` / `boundaryAccY` | 手势导航防抖与累积 |

---

## 三、后端 API 与前端对接关系

| API | 方法 | 使用页面 | 说明 |
|-----|------|----------|------|
| `/api/backgrounds/home` | GET | 未使用 | 可替换首页 `#bg` |
| `/api/backgrounds/detail/{year}` | GET | `detail.html` | 详情背景，无则回退首页图 |
| `/api/events/{year}` | GET | `detail.html` | 详情页核心数据 |
| `/api/years` | GET | 未使用 | 可用于校验有数据年份 |
| `/api/events/adjacent` | GET | 未使用 | 可用作相邻日导航替代方案 |
| `/api/search?q=` | GET | 未使用 | 全文搜索 |
| `/api/visit` | POST | 未使用 | 记录浏览位置（设计：localStorage UUID） |
| `/api/last-visit/{user_id}` | GET | 未使用 | 首页星星脉冲高亮（待实现） |

数据库对应（`jiaoyuan` 库）：

- 详情事件：`chronology` + `literature`
- 背景图：`background_images`
- 浏览历史：`user_visits`（前端未接）

---

## 四、静态资源策略

| 资源 | 策略 |
|------|------|
| 首页背景 | 固定 `images/星辰山峰.jpg`，不读 API |
| 详情背景 | API 优先 → 默认 `images/红日初升.jpg` |
| 肖像 | 按年尝试 `images/jiaoyuan/{year}.png`，`onerror` 隐藏 |
| 星星坐标 | 写死在 `home.html` 的 `stars` 数组（百分比 x/y） |

---

## 五、本地开发与联调

1. 启动 API：`uvicorn life_of_chairman_mao.api.main:app --reload --port 8000`
2. 用静态服务器打开 `web/`（或直接打开 HTML；需注意 `fetch` 跨域，API 已开 CORS `*`）
3. 确保 `detail.html` 中 `API_BASE` 与后端端口一致
4. 年谱数据需先 ETL 导入 `chronology` 表

---

## 六、待完善项（相对设计文档）

- [ ] 首页接入 `GET /api/backgrounds/home` 动态背景
- [ ] 首页 `localStorage` UUID + `POST /api/visit` / `GET /api/last-visit` 上次浏览星星脉冲
- [ ] 首页年份搜索可对接 `GET /api/years` 仅高亮有数据年份
- [ ] 全局搜索页或搜索框对接 `GET /api/search`
- [ ] 选集/文集/文稿等扩展内容的前端展示（当前仅年谱 `chronology`）

---

**文档版本**：与 `web/home.html`、`web/detail.html` 及 `src/life_of_chairman_mao/api/` 路由实现同步（2026-05）。
