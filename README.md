# 每日清单（DailyList）

用 [Flet](https://flet.dev/)（Flutter + Python）写的**待办 / 倒数日** App：一套代码跑 iOS、Android、桌面和 Web。待办存在本机 SQLite 里（按设备隔离）；倒数日跟着**登录的账号**走 —— 后端 `/member/countdowns`（见 `src/api/member_countdowns.py`）。界面全中文，配色是白 - 天蓝 - 靛蓝的浅色系。

- 依赖：`flet>=1.0.1`、`flet-charts>=1.0.1`，Python >= 3.10
- 运行：`uv run flet run`（桌面）/ `uv run flet run --web`（浏览器）/ `python src/main.py`
- 打包：`flet build apk|ipa|windows`，iOS 用 `scripts/build_ios.sh`

---

## 一、功能

### 待办（首页）
- 顶部 7 天日期条（今天起，写成「09.28」），选中格下方一条滑动的黑横条；在列表上左右滑可切换日期，下方整叠滑一页
- 列表是时间轴样式（开始时间 + 点线 + 便签纸卡片），卡片右上角贴分类标签，完成的加删除线并挂「已完成」
- 点行或勾选框切换完成（方形圆角勾选框，勾上填青绿 + 对勾，并有弹一下的动画）；左滑露出编辑 / 删除
- 右下角透明圆按钮（1px 细灰边 + `add` 图标），点了**直接开「新增待办」**弹窗（倒数日的新增挪到倒数日页，见下）

### 新增 / 编辑待办（`tools/todo_form.py`）
- 分类（三胶囊单选，红 / 黄 / 绿）、内容、日期、起止时间（点一格连弹两个时间选择器）、循环（十档，含工作日 / 非工作日）
- 输入框聚焦时隐藏底部菜单与「+」，弹窗贴到键盘上方

### 倒数日
- **数据在后端、跟登录的账号走**：`/member/countdowns`（会员隔离）；进页面拉一次、缓存在 `tools/countdown_store.py`，日历页的格子圆点与当天弹窗读的是同一份缓存
- 未登录时这一页只显示「登录后可同步倒数日」（登录入口在设置页的「账号」卡片里）；右下角「+」点了直接开新增弹窗，没登录会提示
- 卡片三段：图标 + 事项 / 天数大字 + 「天后」色块 / 日期·农历·周几，段间一排定距细点
- 「天后」按剩余天数分三档色：≥7 天绿、3–6 天黄、<3 天（含已过）红
- 最近一张通栏、其余双列；不循环的过期后收进底部「已过期 N」（全部双列、整卡置灰）
- 左滑编辑 / 删除（都走后端）；循环锚点自动走到下一次；卡片底色按 id 稳定取一档浅色（后端没有颜色字段）
- 周期只提供**后端支持的 5 档**：不循环 / 每天 / 一周 / 一月 / 一年 —— App 另外那 5 档（三天 / 工作日 / 非工作日 / 三月 / 六月）后端 `CountdownCycle` 还没有对应取值

### 日历
- 月历格子 = 日期圈 + 农历 + 待办圆点（分类色，完成的淡一半；倒数日天蓝，已过置灰）
- 当天待办全做完画对勾；已过日期仍有未完成的画红「×」
- 格子高度按当月最忙那天算，全月同高；顶部「‹ 年月 ›」翻月，点月份从底部升起日期滚轮
- 点日期弹窗列出当天待办 + 倒数日，高度按内容「先估后量」
- 右上角三枚入口：数据、设置、登录（登录在最右，进的是登录页 —— 目前是 Demo，见 `src/pages/login.py`）

### 数据（二级页）
- 数据统计：半圆完成率环（32 段由浅到深的刻度，圆点指示进度）
- 分类占比：饼图 + 右侧图例
- 待办趋势：三分类折线图，浮框与圆点自绘
- 三张卡各自独立切换 年 / 月 / 周，默认「周」

### 设置（二级页）
- 账号：未登录显示「未登录」+「登录」按钮，点它进登录页（返回回到设置页）；已登录显示当前用户的昵称 / 邮箱 / 会员号 +「管理」（同样进账号页）
- 通知设置：总开关（默认关）+ 渠道（9 种）+ 地址 —— 目前只有配置，没有发送实现
- 数据设置：导出 / 导入 JSON、云端同步开关（占位，默认关）
- 通用设置：检查新版本、联系方式（点一下复制）、清除缓存（待办与倒数日一起清）
- 末尾一行居中署名
- 说明：待办 / 倒数日仍按「设备」隔离（`tools/device.py` 的设备主键），只是界面上不再显示这个 ID

### 登录 / 注册 / 忘记密码
- 入口：设置页「账号」卡片里的「登录」/「管理」→ 登录页（压在设置页之上，返回回到设置页）；登录页底部两个链接 → 注册页 / 忘记密码页（再深一层），返回逐层退
- 字段：登录（邮箱 + 密码）、注册（邮箱 + 邮箱验证码 + 密码 + 确认密码）、忘记密码（邮箱 + 验证码 + 新密码 + 确认新密码）
- 三页都调后端真实接口（`/member/auth/*`，封装见 `src/api/`）：登录成功后令牌存本地 settings 表，并**跳到待办页**；注册成功 / 重置密码成功都**回登录页**；提示直接用后端返回的 `message`，以**屏幕正中那一粒 toast** 弹出（`tools/toast.py`）
- 已登录时再进登录页是「账号」形态：显示当前用户的昵称 / 邮箱 / 会员号（`GET /member/auth/me`），卡片下面是「退出登录」（`POST /member/auth/logout`；后端是无状态 JWT，本地令牌由 `src/api/session.py` 清掉）。本地令牌已失效（401）时自动清掉并退回登录表单
- 两处「获取验证码」点下**立刻上锁**（再点无效），锁的秒数按后端返回的 `resend_after`、没给才用 60 秒
- 版式：表单固定摆在中上偏上（键盘弹出也不移动）；卡片与输入框都不填底色，**卡片连外框也去掉了**（只留内边距给内容定宽与上下留白），输入框仍以浅灰细边示意范围；输入框等高、**文字与提示都压在格子中线上**（对称内边距 `FIELD_TEXT_INSET`=11，配合 `text_vertical_align=CENTER` 与 `fit_parent_size`，整格都可点）；密码框右侧的「显示 / 隐藏」贴到框右端；卡片顶上的默认头像是 Flet 内置图标（`ft.Icons.PERSON`）；登录页的「忘记密码？」贴着**密码框外的右下角**（卡片内那一行、右对齐、**与密码框右边缘齐平**，与密码框的间距收到 `FIELD_HINT_GAP`=2），「还没有账号？去注册」**钉在页面左右居中偏下**（不跟表单走，见 `build_auth_page` 的 `footer`；它被钉在构建时那一屏的高度里，**键盘弹起也不会被顶上去**）

### 页面与返回
- 二级 / 三级页是压进 `page.views` 的真 `View`，顶栏返回、左滑、系统返回共用 `go_back`
- 页面动画固定 `CUPERTINO`（横向推拉，两页不叠、不留残影）

---

## 二、文件说明

| 文件 | 说明 |
| --- | --- |
| `src/main.py` | 入口：建库 → 补默认设置 → 取设备 ID 当数据主键 → 注册 Service → 装配导航 |
| `src/pages/navigation.py` | 底部菜单、Tab 切换、二级页跳转与页面栈（`nav_stack` + `page.views`）、主题 |
| `src/pages/home.py` | 待办页：7 天日期条、按天列表、完成切换、「+」新增待办 |
| `src/pages/countdown.py` | 倒数日页：「+」新增、通栏 + 双列卡片、底部「已过期 N」开关、未登录提示（数据来自后端） |
| `src/pages/calendar.py` | 日历页：月历网格、当天详情弹窗、右上角数据 / 设置入口（倒数日圆点读同一份缓存） |
| `src/pages/data.py` | 数据页：完成率半环、分类占比饼图、待办趋势折线图 |
| `src/pages/preferences.py` | 设置页：账号（登录态 / 当前用户）+ 通知 / 数据 / 通用四档卡片 |
| `src/pages/login.py` | 登录页：邮箱 / 密码 + 登录按钮（`/member/auth/login`），底部「忘记密码 / 注册新账号」进三级页 |
| `src/pages/register.py` | 注册新账号页：邮箱 / 邮箱验证码 / 密码 / 确认密码（`/member/auth/send-code`、`/register`） |
| `src/pages/forgot_password.py` | 忘记密码页：邮箱 / 验证码 / 新密码 / 确认新密码（`/member/auth/send-code`、`/reset-password`） |
| `src/api/client.py` | 请求底座：后端基址、用标准库 `urllib` 发请求（GET / POST / PUT / DELETE；**必须带浏览器 UA**，否则被 Cloudflare 403）、把错误体翻成 `ApiError` |
| `src/api/session.py` | 登录态：access / refresh 令牌的存取（落库 settings 表） |
| `src/api/member_auth.py` | 用户中心 · 认证接口：验证码 / 注册 / 登录 / 刷新 / 重置密码 / 当前会员 / 登出 |
| `src/api/member_countdowns.py` | 用户中心 · 倒数日接口：我的列表 / 新增 / 修改 / 删除（`/member/countdowns`），中文周期 ↔ 后端枚举的映射也在这儿 |
| `src/tools/db.py` | 数据层：建表与迁移、按设备隔离、**待办** CRUD、循环展开（倒数日已改走后端，本地那张表只剩历史数据） |
| `src/tools/device.py` | 设备主键（iOS IDFV / macOS GUID / Windows device_id / Linux machine_id） |
| `src/tools/app_settings.py` | `settings` 表该有哪些键 + 启动时补默认值 |
| `src/tools/data_export.py` / `data_import.py` | 导出为 JSON / 从 JSON 恢复（整表替换） |
| `src/tools/layout.py` | 全局配色与尺寸常量、assets 图片路径、渐变、弹窗键盘定位、页面渐变、控件是否还挂在页面上（`is_attached` / `safe_update`） |
| `src/tools/auth_form.py` | 登录 / 注册 / 忘记密码三页共用的表单骨架：页面壳、卡片、字段、主按钮、底部链接 |
| `src/tools/todo_timeline.py` | 待办行与时间轴的画法（首页一条条搭、日历弹窗整列搭共用） |
| `src/tools/todo_form.py` / `countdown_form.py` | 新增 / 编辑待办弹窗、新增 / 编辑倒数日弹窗（保存走后端） |
| `src/tools/countdown_card.py` | 倒数日卡片（三档状态色、过期置灰），数据读 `countdown_store` |
| `src/tools/countdown_store.py` | 倒数日的内存仓库：后端是唯一数据源，这里给页面一个**同步**读法 + 增删改 + 按 id 取色 |
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
14. **新增或修改功能后，README 里的功能说明要简洁明了**：一条一句，只写「做了什么 + 入口 / 关键行为」，实现细节留给代码注释；能一行说完就别铺成一段

---

## 五、已知问题

- **登录态只存不用**：令牌存在本地 settings 表里，但界面上还没有「当前登录是谁」的展示，也没有退出登录入口（接口 `member_auth.logout()` 已封装好）
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

- `2026-10-13` 修掉「页面切走后异步刷新崩掉」：页面每次切过去都是重建的，而拉数据 / 左滑删除 / 弹窗保存的回调要等网络回来，回来时那一页可能已经被换掉，`control.update()` 会抛 `RuntimeError: ... must be added to the page first`。`tools/layout.py` 新增 `is_attached` / `safe_update`，倒数日页的 `refresh()` 与日历页的 `update_calendar()` 改为先问一句再刷。
- `2026-10-13` 倒数日接入后端：数据源从本地 SQLite 换成 `/member/countdowns`（会员隔离，见 `src/api/member_countdowns.py`；`client.py` 补了 PUT / DELETE）。新增 `tools/countdown_store.py` 做**同步缓存**——日历页那 5 处同步读法因此一行没改。倒数日页右下角加上与待办页同款的「+」按钮（点了直接开新增弹窗；未登录给提示），待办页去掉「新增倒数日」及整个毛玻璃面板（「+」回到直接新增待办）。周期只提供后端支持的 5 档；卡片底色改为按 id 稳定推导（后端没有颜色字段）。
- `2026-10-13` 去掉日历页右上角的「登录」入口（连带 `PERSON_ICON_SRC` / `PERSON_ICON_SIZE` 两个常量，以及导航里已无人调用的 `show_login`）；登录页现在只从设置页「账号」卡片进（`show_login_from_settings`）。
- `2026-10-13` 设置页：去掉顶部那行设备 ID（连 `device_label()` 一起；数据归属那套——`tools/device.py` 与 `db.set_data_owner`——保持不变，否则待办 / 倒数日会混成一份），新增「账号」卡片：未登录给「未登录 + 登录」入口，已登录显示昵称 / 邮箱 / 会员号（`GET /member/auth/me`）与「管理」，两者都进登录页。为支持「设置页 → 登录页」且返回落回设置页，登录 / 注册 / 忘记密码三层改为带 `depth` 参数（从设置页进来的登录是第 2 层）。
- `2026-10-13` 去掉登录 / 注册 / 忘记密码三页卡片外圈的灰色范围线（`build_auth_card` 不再画 `border`，只留内边距给内容定宽与上下留白）；输入框那一圈细边与卡片顶上的头像圈保留。
- `2026-10-13` 修掉上一版引入的两个问题：① footer 那一层铺满整屏、却压在表单**上面**，把整张卡片盖住（输入框点不中、卡片里的「忘记密码？」也点不动）—— 改为插到 Stack **最底层**；② 这个输入框的内容其实是**顶部对齐**的，上下内边距置 0 会让整行明显偏上 —— 改为对称 `FIELD_TEXT_INSET`=11 把它压到中线，并加 `fit_parent_size` 让可编辑区填满整格（点上下边缘也能输入）。
- `2026-10-13` 登录页两处：「还没有账号？去注册」不再被键盘顶上去（`build_auth_page` 的 footer 改成夹在一个高度 = 构建时那一屏的容器里，`bottom` 相对它算，视口变矮也不动）；输入框的上下内边距收到 0，让提示文字（hint）与输入文字一起落在格子中线上。
- `2026-10-13` 登录页三处细节：「忘记密码？」的右边缘与密码框齐平（`build_link_row` 新增 `side_padding`，那一行传 0）；密码框那枚「显示 / 隐藏」再往右（`FIELD_TRAILING_INSET` 4 → 0）；卡片默认头像改用 Flet 内置图标 `ft.Icons.PERSON`（`build_card_heading` 新增 `icon` 参数，不再依赖 `icons/person.png`）。
- `2026-10-13` 登录页细节：「忘记密码」→「忘记密码？」（加问号），并把这一行与密码框的间距收到 `FIELD_HINT_GAP`=2（不再用卡片的 12），贴紧密码框右下角；页面下方那件文案改成「还没有账号？去注册」。
- `2026-10-13` 登录页改两处位置：「忘记密码」从卡片下面那行挪到**密码框外的右下角**（卡片内、右对齐，`build_link_row` 新增 `alignment`）；「注册新账号」挪到**页面左右居中偏下**（`build_auth_page` 新增 `footer`，按屏高比例钉在离底 12% 处，不跟着表单一列走）。注册页 / 忘记密码页不受影响。
- `2026-10-13` 登录 / 注册 / 忘记密码改跳转与登录态：注册成功、重置密码成功都回登录页（`go_back`），登录成功跳待办页（新增 `open_todo`）；登录页新增「已登录」形态 —— 进页面调 `GET /member/auth/me` 显示当前用户的昵称 / 邮箱 / 会员号，并提供「退出登录」（`POST /member/auth/logout` + `/member/auth/logout` 清本地令牌），令牌失效（401）自动退回登录表单（新增 `reload_login`）。
- `2026-10-13` 修掉提示不在页面正中：Flet 的 SnackBar 同时给 `width` 与 `margin` 时**只认 `width`、`margin` 被整个忽略**，所以那粒提示其实一直掉在屏幕底部 —— `tools/toast.py` 改成只用 `margin` 定位（宽度由左右留白表达），登录 / 注册 / 忘记密码 / 设置等所有用到 toast 的页面一并生效。
- `2026-10-13` 修掉所有接口都返回 403 的问题：域名前面挂着 Cloudflare，它按浏览器指纹过滤（Error 1010: Access denied），`urllib` 默认的 `Python-urllib/3.x` 会被直接拦掉 —— `api/client.py` 改为带浏览器 `User-Agent` 等默认请求头；同时让错误提示在拿不到后端信封时退到中间层的 `title` / `detail`，403 不再只有一句笼统的「没有权限访问」。
- `2026-10-13` 登录 / 注册 / 忘记密码接入后端真实接口：新建 `src/api/`（`client.py` 请求底座 + `session.py` 登录态 + `member_auth.py` 认证分类），三页改为调 `/member/auth/*` 并原样提示后端错误；「获取验证码」锁的秒数改用后端的 `resend_after`，并在点击瞬间上锁（避免响应回来前连点重复发请求）。
- `2026-10-13` 「获取验证码」改成真的倒计时：点一次锁 60 秒、每秒报剩余秒数、期间点击不响应、归零后恢复（`tools/auth_form.py` 的 `start_code_countdown`，锁记在按钮的 `data` 上）。
- `2026-10-13` 登录 / 注册 / 忘记密码补三处版式问题：输入框加 `text_vertical_align=CENTER`（只钉高度不会让文字居中）、表单位置改成固定像素并整体再上移、页面壳改用 `Stack` 定位使键盘弹起时不再把整页往上挤。
- `2026-10-13` 登录 / 注册 / 忘记密码三页版式微调：表单改居中偏上、去掉标题与首个输入框之间的横线、输入框内文字垂直居中、密码框的「显示 / 隐藏」贴到框右端；注册页去掉用户名字段（邮箱 + 验证码 + 密码 + 确认密码），与忘记密码页对齐。
- `2026-10-13` 新增开发约定 14（新增 / 修改功能后，README 的功能说明要简洁明了），并按它精简「登录 / 注册 / 忘记密码」那段功能说明。
- `2026-10-13` 登录 / 注册 / 忘记密码三页改版：表单上下居中、输入框等高、去掉卡片与输入框的底色（改用浅灰细边示意范围）、去掉页面上的 Demo 字样；注册页新增邮箱验证码（验证码行抽到 `auth_form.build_code_row` 与忘记密码页共用）。
- `2026-10-13` 新增「注册新账号」与「忘记密码」两个 Demo 页（登录页底部两个链接进三级页），并把登录 / 注册 / 忘记密码三页共用的表单骨架抽到 `tools/auth_form.py`。
- `2026-10-13` 日历页右上角新增「登录」入口（`icons/person.png`，落在最右），点击进入新增的登录页 Demo —— 只有界面与提示，未接鉴权。
