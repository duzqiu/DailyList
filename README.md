# 每日清单（DailyList）

用 [Flet](https://flet.dev/)（Flutter + Python）写的本地**待办 / 倒数日** App：一套代码跑 iOS、Android、桌面和 Web，数据存本地 SQLite，不需要服务端。界面全中文，配色是白 - 天蓝 - 靛蓝的浅色系。

- 依赖：`flet>=1.0.1`、`flet-charts>=1.0.1`，Python >= 3.10
- 运行：`uv run flet run`（桌面）/ `uv run flet run --web`（浏览器）/ `python src/main.py`
- 打包：`flet build apk|ipa|windows`，iOS 用 `scripts/build_ios.sh`

---

## 一、功能

### 待办（首页）
- 顶部 7 天日期条（今天起，写成「09.28」），选中格下方一条滑动的黑横条；在列表上左右滑可切换日期，下方整叠滑一页
- 列表是时间轴样式（开始时间 + 点线 + 便签纸卡片），卡片右上角贴分类标签，完成的加删除线并挂「已完成」
- 点行或勾选框切换完成（方形圆角勾选框，勾上填青绿 + 对勾，并有弹一下的动画）；左滑露出编辑 / 删除
- 右下角透明圆按钮（1px 细灰边 + `add` 图标），点开毛玻璃面板选「新增待办 / 新增倒数日」

### 新增 / 编辑待办（`tools/todo_form.py`）
- 分类（三胶囊单选，红 / 黄 / 绿）、内容、日期、起止时间（点一格连弹两个时间选择器）、循环（十档，含工作日 / 非工作日）
- 输入框聚焦时隐藏底部菜单与「+」，弹窗贴到键盘上方

### 倒数日
- 卡片三段：图标 + 事项 / 天数大字 + 「天后」色块 / 日期·农历·周几，段间一排定距细点
- 「天后」按剩余天数分三档色：≥7 天绿、3–6 天黄、<3 天（含已过）红
- 最近一张通栏、其余双列；不循环的过期后收进底部「已过期 N」（全部双列、整卡置灰）
- 左滑编辑 / 删除；循环锚点自动走到下一次；新增入口统一在待办页的「+」

### 日历
- 月历格子 = 日期圈 + 农历 + 待办圆点（分类色，完成的淡一半；倒数日天蓝，已过置灰）
- 当天待办全做完画对勾；已过日期仍有未完成的画红「×」
- 格子高度按当月最忙那天算，全月同高；顶部「‹ 年月 ›」翻月，点月份从底部升起日期滚轮
- 点日期弹窗列出当天待办 + 倒数日，高度按内容「先估后量」
- 右上角两枚入口：数据在左、设置在右

### 数据（二级页）
- 数据统计：半圆完成率环（32 段由浅到深的刻度，圆点指示进度）
- 分类占比：饼图 + 右侧图例
- 待办趋势：三分类折线图，浮框与圆点自绘
- 三张卡各自独立切换 年 / 月 / 周，默认「周」

### 设置（二级页）
- 顶栏下一行设备 ID（数据就按它隔离）
- 通知设置：总开关（默认关）+ 渠道（9 种）+ 地址 —— 目前只有配置，没有发送实现
- 数据设置：导出 / 导入 JSON、云端同步开关（占位，默认关）
- 通用设置：检查新版本、联系方式（点一下复制）、清除缓存（待办与倒数日一起清）
- 末尾一行居中署名

### 页面与返回
- 二级 / 三级页是压进 `page.views` 的真 `View`，顶栏返回、左滑、系统返回共用 `go_back`
- 页面动画固定 `CUPERTINO`（横向推拉，两页不叠、不留残影）

---

## 二、文件说明

| 文件 | 说明 |
| --- | --- |
| `src/main.py` | 入口：建库 → 补默认设置 → 取设备 ID 当数据主键 → 注册 Service → 装配导航 |
| `src/pages/navigation.py` | 底部菜单、Tab 切换、二级页跳转与页面栈（`nav_stack` + `page.views`）、主题 |
| `src/pages/home.py` | 待办页：7 天日期条、按天列表、完成切换、「+」毛玻璃面板 |
| `src/pages/countdown.py` | 倒数日页：通栏 + 双列卡片、底部「已过期 N」开关 |
| `src/pages/calendar.py` | 日历页：月历网格、当天详情弹窗、右上角数据 / 设置入口 |
| `src/pages/data.py` | 数据页：完成率半环、分类占比饼图、待办趋势折线图 |
| `src/pages/preferences.py` | 设置页：设备 ID + 通知 / 数据 / 通用三档卡片 |
| `src/tools/db.py` | 数据层：建表与迁移、按设备隔离、待办与倒数日 CRUD、循环展开 |
| `src/tools/device.py` | 设备主键（iOS IDFV / macOS GUID / Windows device_id / Linux machine_id） |
| `src/tools/app_settings.py` | `settings` 表该有哪些键 + 启动时补默认值 |
| `src/tools/data_export.py` / `data_import.py` | 导出为 JSON / 从 JSON 恢复（整表替换） |
| `src/tools/layout.py` | 全局配色与尺寸常量、assets 图片路径、渐变、弹窗键盘定位、页面渐变 |
| `src/tools/todo_timeline.py` | 待办行与时间轴的画法（首页一条条搭、日历弹窗整列搭共用） |
| `src/tools/todo_form.py` / `countdown_form.py` | 新增 / 编辑待办弹窗、新增 / 编辑倒数日弹窗 |
| `src/tools/countdown_card.py` | 倒数日卡片（三档状态色、过期置灰） |
| `src/tools/line_chart.py` / `pie_chart.py` / `half_ring.py` | 趋势折线图、分类饼图、完成率半环 |
| `src/tools/segmented.py` / `popup_select.py` / `pickers.py` | 横向胶囊开关、统一下拉选择器、系统日期时间选择器 |
| `src/tools/swipe_delete.py` / `swipe_back.py` | 左滑露出行内操作、整页左滑返回 |
| `src/tools/toast.py` / `services.py` | 居中 toast、`ft.Service`（剪贴板 / 文件选择器）统一注册 |
| `src/tools/lunar.py` | 农历换算（1900–2099 查表，无外部依赖） |
| `src/tools/notifications.py` / `contacts.py` / `version_check.py` | 通知渠道配置、联系方式、检查新版本 |
| `src/tools/categories.py` | 三个类别及其颜色 |
| `src/assets/` | `icon.png` / `splash_android.png`（必须在根目录）+ `icons/` 五张图 |
| `scripts/build_ios.sh` | 一键打签名好的 iOS `.ipa` |
| `tests/test_main.py` | Flet 测试框架写的导航冒烟测试（当前已过期） |

---

## 三、数据（SQLite `dailylist.db`）

打包后优先用 `FLET_APP_STORAGE_DATA`，源码运行落在项目根。

| 表 | 列 |
| --- | --- |
| `todos` | id, due_date, due_time, end_time, category, content, done, repeat_cycle, owner, created_at |
| `countdowns` | id, due_date, cycle, content, bgcolor, owner, created_at |
| `settings` | name(主键), value |

- **按设备隔离**：`owner` = 设备主键；Android / Web 拿不到唯一标识，空串即「默认那一份」
- **自动迁移**：`init_db()` 自动补缺失列，不需要迁移脚本
- **循环待办物化**：新增 / 编辑时一次性铺满未来 365 天（上限 400 行），工作日 / 非工作日按星期筛选

---

## 四、开发约定

1. 颜色 / 尺寸集中在 `tools/layout.py` 与 `tools/categories.py`，页面里不写十六进制
2. 下拉一律用 `tools/popup_select.py`，不用 `ft.Dropdown`（它的框会盖住面板）；选项直接摊开时用 `segmented.py`
3. 弹窗统一 `RoundedRectangleBorder(12)` + `DIALOG_SURFACE` + `elevation=0`
4. 键盘用 `track_keyboard(page, dialog)`，别用 `on_focus` / `on_blur` 挪弹窗（会先下沉再弹回）
5. 列表底部留白用 `BOTTOM_MENU_INSET`，滚动一律 `ScrollMode.HIDDEN`
6. 折线图关掉自带触摸（`interactive=False`），浮框与圆点自绘、手势自己接
7. 页面选择状态存在 `pages/navigation.py` 的 `state_store`（切页会重建页面控件）
8. 日历弹窗高度「先估后量」，且估高不估矮
9. `ft.Service` 必须由 `main.py` 的 `register_app_services()` 在页面首帧前注册，之后注册客户端收不到
10. assets 根目录放 `icon.png` / `splash_android.png`（挪进子目录会静默回退成模板图标）；代码引用路径相对 assets，如 `icons/settings.png`
11. 页面层级只认 `nav_stack` + `page.views`，别自己写 `show_page(0)` 当返回
12. 页面不直接写 SQL（一律走 `db.py`），也不重复造控件（能共享的都放 `tools/`）
13. **每次修改代码后，都要在「修改记录」最上面加一条**：日期 + 一句话说明当次改了什么，简短精炼，一次修改只记一条，最新的一条排在最上面

---

## 五、已知问题

- **通知只有配置，没有发送**：开关只改文案与提示，接上发送后才是真开关
- **云端同步是占位**：状态落库，但不发任何请求
- **导入是「替换」不是「合并」**：待办与倒数日整表换成文件内容，只认本 App 导出的 JSON
- **两个 `dailylist.db`**：应用真正读写 `.flet/storage/data/dailylist.db`，项目根那份已过时
- **多实例同时跑会互相覆盖数据**
- **一级页按返回会退出 App**（Flet 没给拦截口子，属正常行为）
- **测试已过期**：`tests/test_main.py` 断言停留在旧文案，dev 依赖也没装
- **装依赖要用镜像**：直连 pypi.org 会拿到被截断的索引，`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple ...`

---

## 六、修改记录

_每次修改在此追加一条：`2026-10-12 一句话说明`（最新在最上面）_
