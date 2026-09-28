# 每日清单（DailyList）

用 [Flet](https://flet.dev/)（Flutter + Python）写的本地**待办 / 倒数日** App：一套代码跑 iOS、Android、桌面和 Web，数据存在本地 SQLite，不需要服务端。界面全中文，配色是白 + 天蓝 + 靛蓝的浅色系。

---

## 一、功能

### 待办（首页）
- 顶部「待办」标题 + 7 天日期条（今天 ±3 天，今天那格写「今」），点某天切换下方列表
- 列表标题「9月26日待办」，每行是时间轴样式：左边时间 + 点线轴，右边类别标签 + 待办文字
- 点一行切换完成（完成变灰加删除线）；左滑一行露出「编辑 / 删除」
- 空态显示「今天没有待办事项哦」
- 右下角毛玻璃圆形「+」（天蓝 `#B2E0F4` 60% 透明 + Blur 20），点开新增弹窗；弹窗只弹出，**不自动聚焦输入框**

### 新增 / 编辑待办弹窗（`tools/todo_form.py`）
- 日期：系统日期选择器（新增时最早只能选今天，编辑可移到过去）
- 时间：系统时间选择器，默认当前时刻向下取整到 5 分钟
- 类别：★ 重要（红）/ ★ 一般（黄）/ ★ 可选（绿）
- 循环：不循环 / 每天 / 三天 / 一周 / 一月 / 三月 / 六月 / 一年
- 内容：多行输入，2–5 行
- 输入框获得焦点时，底部菜单栏和「+」一起隐藏，弹窗贴到键盘上方（不会被键盘顶飞，也不会有中间那条灰带）

### 倒数日
- 卡片分三段：上段「图标 + 事项」（底色是这张卡自选的颜色）；中段天数大字 + 「天后」色块；下段「日期 · 农历 · 周几」
- 天数按剩余天数上色：已过 → 红，3 天内 → 黄，其余 → 绿
- 最近的一张通栏，其余按两列排（窄屏自动落成一张）
- 左滑编辑 / 删除；周期和待办共用一套，循环锚点会自动走到下一次（生日只需记一次）

### 日历
- 月历卡片：每格 = 日期圈（选中的填蓝）+ 农历 + 最多 4 条彩色小条（分类色；完成的加删除线；倒数日用天蓝），超出显示「+N」
- 顶部「‹ 年月 ›」翻月；点月份标题打开系统日期选择器直接跳到某天
- 点任意日期 → 弹窗列出当天全部内容：待办（时间轴，可左滑编辑 / 删除）+ 倒数日（卡片）；空态「这天没有待办事项」

### 我的
- **数据统计**：三张分类卡（重要 / 一般 / 可选），每张显示「全部 / 已完成 / 未完成 / 完成率」，完成率低于 50% 标红，无数据显示「—」
- **分类占比**：饼图（`flet-charts`），悬停 / 点按扇区凸出，圆心显示总数，右侧图例
- **待办趋势**：多系列折线图（`flet-charts`），三条线 = 三个类别，点按数据点弹出数值；X 轴随周期变化（年 = 12 个月，月 = 当月每天，周 = 周一至周日），左侧有 Y 轴线
- 三张卡各自独立切换 **年 / 月 / 周**，默认「周」
- 右上角齿轮 → 设置二级页

### 设置（二级页，`pages/preferences.py`）
- 通知渠道：Bark / Pushdeer / Server酱 / 企业微信 / 钉钉 / 飞书 / Telegram / Discord / Slack + 通知地址（存 `settings` 表）
- 清除缓存：二次确认后清空所有待办，并提示清除了多少条
- 云端数据：开关（**占位功能，不落库、不发请求**）

---

## 二、目录结构

| 文件 | 行数 | 职责 |
| --- | --- | --- |
| `src/main.py` | 13 | 入口：`db.init_db()` 建库 → `build_navigation(page)` |
| `src/pages/navigation.py` | 182 | 底部毛玻璃菜单 + 4 个 Tab 切换 + 二级页（设置）跳转；键盘弹起时把菜单顶起来 |
| `src/pages/home.py` | 325 | 待办页：日期条、按天列表、完成切换、毛玻璃「+」 |
| `src/pages/countdown.py` | 195 | 倒数日页：通栏 + 两列卡片列表 |
| `src/pages/calendar.py` | 542 | 日历页：月历卡片网格、当天详情弹窗 |
| `src/pages/settings.py` | 635 | 「我的」页：数据统计 / 分类占比 / 待办趋势三张卡 |
| `src/pages/preferences.py` | 413 | 设置二级页：通知渠道、清除缓存、云端开关 |
| `src/tools/db.py` | 561 | 数据层：建表 / 迁移 / 待办与倒数日 CRUD / 循环展开 / settings |
| `src/tools/layout.py` | 161 | 全局配色与尺寸常量、页面渐变、弹窗键盘定位、文字宽度估算、可读字色 |
| `src/tools/categories.py` | 61 | 三个类别及其颜色、星标控件 |
| `src/tools/todo_timeline.py` | 245 | 待办时间轴行（首页与日历弹窗共用） |
| `src/tools/todo_form.py` | 232 | 新增 / 编辑待办弹窗 |
| `src/tools/swipe_delete.py` | 124 | 左滑露出操作按钮的行容器 |
| `src/tools/popup_select.py` | 219 | 统一的下拉选择器（年/月/周、类别、循环、通知渠道都用它） |
| `src/tools/pickers.py` | 123 | 系统日期 / 时间选择器封装（含 UTC 时区修正） |
| `src/tools/countdown_card.py` | 247 | 倒数日卡片 |
| `src/tools/countdown_form.py` | 237 | 新增 / 编辑倒数日弹窗（含卡片底色选择） |
| `src/tools/line_chart.py` | 186 | 待办趋势折线图（`flet-charts` 多系列 LineChart） |
| `src/tools/pie_chart.py` | 82 | 分类占比饼图（`flet-charts` PieChart + 悬停凸出） |
| `src/tools/lunar.py` | 124 | 农历换算（1900–2099 查表，无外部依赖） |
| `src/tools/notifications.py` | 18 | 通知渠道清单与文案（目前只有配置，没有发送实现） |
| `tests/test_main.py` | 22 | Flet 测试框架写的导航冒烟测试 |
| `scripts/build_ios.sh` | 105 | 一键打签名好的 iOS `.ipa`（免费 Personal Team 自动签名） |

---

## 三、架构

```
main.py
  └── pages/navigation.py           页面装配 + 底部菜单 + 主题
        ├── pages/home.py           ──┐
        ├── pages/countdown.py        │  页面只管「编排 + 状态」，
        ├── pages/calendar.py         │  控件画法全部委托给 tools/
        ├── pages/settings.py         │
        └── pages/preferences.py    ──┘
              ↓
        tools/*.py                  共享控件与数据层
              ↓
        tools/db.py  ──→  SQLite（dailylist.db）
```

约定：**页面不直接写 SQL**，一律经 `tools/db.py`；**页面不重复造控件**，能共享的（时间轴行、卡片、弹窗、下拉、选择器）都放在 `tools/`。`navigation.py` 每次切页都重建页面控件（`build_xxx_page`），并把 `set_menu_visible` 回调传下去，页面在弹窗 / 键盘出现时用它收起底部菜单和「+」按钮。

---

## 四、数据（SQLite）

数据库位置（`tools/db.py`）：打包后的 App 目录只读，所以优先用 Flet 给的 `FLET_APP_STORAGE_DATA`；从源码运行时用**项目根目录**的 `dailylist.db`。

| 表 | 列 |
| --- | --- |
| `todos` | `id`, `due_date`(ISO 日期), `due_time`("HH:MM"), `category`, `content`, `done`, `repeat_cycle`, `created_at`（另有 `idx_todos_due_date` 索引） |
| `countdowns` | `id`, `due_date`, `cycle`, `content`, `bgcolor`, `created_at` |
| `settings` | `name`(主键), `value` |

两个设计点：

- **自动迁移**：`init_db()` 跑 `CREATE TABLE IF NOT EXISTS` + `_add_missing_columns()`，老库缺的列（`repeat_cycle` / `due_time` / `bgcolor`）启动时自动补上，不需要单独的迁移脚本。
- **循环待办物化**：循环不是运行时算的，而是在新增 / 编辑时按周期一次性铺满未来 `REPEAT_HORIZON_DAYS = 365` 天（每天最多 `MAX_OCCURRENCES = 400` 行），这样首页和日历直接查日期区间就行，不需要后台任务。编辑一条循环待办会**整条序列重建**（`db.update_todo`），已完成的按序号保留勾选状态。

---

## 五、开发约定

改代码前值得知道的几条（都是踩过坑留下来的）：

1. **颜色 / 尺寸集中在 `tools/layout.py` 和 `tools/categories.py`**：卡片色、选中蓝、完成灰、弹窗圆角（`DIALOG_RADIUS = 12`，Material 默认 28）、弹窗表面色（`DIALOG_SURFACE`）等都在这里，页面里不要再手写十六进制。
2. **下拉一律用 `tools/popup_select.py`**，不要用 `ft.Dropdown`：Dropdown 的触发器是 Material TextField，`InputDecorator` 会在弹层之上再画一遍自己的框，把贴在它下面的面板盖住一半。现在用 `PopupMenuButton + menu_position=UNDER`。
3. **弹窗**统一 `shape=RoundedRectangleBorder(radius=DIALOG_RADIUS)` + `bgcolor=DIALOG_SURFACE` + `elevation=0`。
4. **键盘处理**：输入框 `on_focus` 里调 `anchor_dialog_above_keyboard(dialog, True)`（弹窗贴键盘上方）并用 `set_menu_visible(False)` 收起底部菜单和浮动按钮；`on_blur` 复原。
5. **列表底部留白**用 `BOTTOM_MENU_INSET`，否则最后一行会被浮动菜单栏压住。
6. 页面内容滚动一律 `scroll=ft.ScrollMode.HIDDEN` 隐藏滚动条。

---

## 六、运行

依赖（`pyproject.toml`）：`flet >= 1.0.1`、**`flet-charts >= 1.0.1`**（折线图和饼图必需，Flet 1.0 把图表拆成了独立包）。

```bash
uv run flet run          # 桌面窗口
uv run flet run --web    # 浏览器
python src/main.py       # 直接用解释器跑（src 已在 sys.path 上，DB 始终落在项目根）
```

> ⚠️ 本机实测：conda 环境 `D:\ProgramData\miniconda3\envs\flet` 里 flet 是 1.0.1，但**没装 `flet-charts`**（其它 conda 环境也没有），直接运行会报
> `ModuleNotFoundError: No module named 'flet_charts'`（`pages/settings.py`、`tools/line_chart.py`、`tools/pie_chart.py` 需要它）。
> 先补依赖：`pip install "flet-charts>=1.0.1"`（或 `uv sync`）。

## 七、打包

```bash
flet build apk -v        # Android
flet build ipa -v        # iOS（或直接用下面的脚本）
flet build windows -v    # 也支持 macos / linux / web
```

iOS 用 `scripts/build_ios.sh`（**在已登录的桌面终端里跑，不要加 sudo**）：它先 `flet build ipa`，再用 Xcode 自动签名 archive + export，产物在 `build/ios-build/export/dailylist.ipa`；遇到「启动即退」用 `scripts/build_ios.sh --clean`。

`pyproject.toml` 里已固定：`org = com.duzqiu`、`product = 每日清单`、`bundle_id = com.duzqiu.dailylist`（跟签名描述文件一致），并用 `[tool.flet.flutter.pubspec.dependency_overrides]` 把 `device_info_plus` 钉在 12.3.0、`connectivity_plus` 钉在 7.0.0，规避 Xcode 16 / iOS 18 SDK 编不过的问题。

## 八、测试

`tests/test_main.py` 是 Flet 官方测试框架（`flet.testing` + pytest，`pyproject.toml` 里配了 `asyncio_mode = "auto"`）写的导航冒烟测试，运行方式：

```bash
pytest
```

现状：本机没有安装 dev 依赖（`flet[test]` → pytest / numpy 都缺），跑不起来；而且该测试的断言还停留在旧文案（找「日历页面」「设置页面」），与现在的「日历」「我的 / 设置」不一致，重新启用前需要同步。

## 九、已知问题 / 待办

- **依赖缺失**：`flet-charts` 未安装，App 目前无法启动（见「运行」）。
- **测试过期**：`tests/test_main.py` 断言与当前 UI 文案不符。
- **通知渠道只有配置**：`tools/notifications.py` 只存渠道名和地址，没有真正发送推送的逻辑。
- **云端数据是占位**：开关不落库、不请求（代码注释里写明「先只做样子」）。
- **仓库里的 `dailylist.db` 是活数据文件**：当前只有 `todos`(204 行) / `settings`，既没有 `countdowns` 表，`todos` 也缺 `due_time` 列 —— 说明该文件早于「倒数日 / 时间」功能，首次运行会被 `init_db()` 自动补齐。它是跟着仓库走的，改动数据会体现为一次文件改动。
- **多实例同时写库**：应用的 DB 路径固定在项目根，同时开多个实例（或一边跑 App 一边跑测试脚本）会互相覆盖数据，调试时注意先关掉旧实例。
