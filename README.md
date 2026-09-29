# 每日清单（DailyList）

用 [Flet](https://flet.dev/)（Flutter + Python）写的本地**待办 / 倒数日** App：一套代码跑 iOS、Android、桌面和 Web，数据存在本地 SQLite，不需要服务端。界面全中文，配色是白 + 天蓝 + 靛蓝的浅色系。

---

## 一、功能

### 待办（首页）
- 顶部「待办」标题 + 7 天日期条（今天排第一个、往后连着 7 天，**每格都写成「09.28」这样的月.日**，字号 10 —— 今天也写日期、不写「今」）；**日期不带底色**，选中的那天只是日期**加粗**，选中标记是日期正下方一条 16×3 的黑横条（`DATE_BAR_*`）：**整条日期条只画这一条**，它钉在日期卡片底边上、紧贴下面那条灰间隔线（日期条与灰线之间那条 10px 的缝挪进了卡片，所以灰线以下一点没动）；点某天、或者**在下方那块（待办列表）上左右滑**（横滑挂在列表外面那层手势上，日期条自己不接；`DATE_SWIPE_DISTANCE` / `DATE_SWIPE_VELOCITY`，左滑看后一天、右滑看前一天，走到头就停住不绕回来；竖着滑还是列表自己滚，起点落在某条待办上时那一条的左滑（露出编辑 / 删除）优先），横条都会按 `offset`（= 选中格中线到日期条中线的距离 ÷ 日期条宽，见 `date_bar_offset`）**慢慢滑到那一格下面**（`DATE_BAR_SLIDE_MS = 500` + `animate_offset`；日期条宽度要等布局完量出来，第一帧先按 `DATE_STRIP_ESTIMATED_WIDTH` 估）；下方是**一叠「一天一页」**（`PAGE_SLIDE_KEY = "date-pages"`），切日期时**整叠滑一格 —— 旧的一页滑出去、新的一页滑进来**（每页 `offset = 该天的下标 − 选中下标`，配 `DATE_PAGE_SLIDE_MS = 500` + `animate_offset`，跟黑横条同一套时间；七页一起摆在栈里，新的一页才有「上一个位置」可以滑过来，见 `slide_pages`）；这一叠**铺满整屏宽** —— 左右那 24px 的边距收进了每一页自己（`Stack` 上 `fit=StackFit.EXPAND`，七页都拉成和叠一样大），`offset` 是按控件**自身宽度**换算的，页盒只有「屏宽 − 48」时「挪一格」也只挪「屏宽 − 48」，屏幕左右那 24px 里就会漏出邻居那一页的一角；页盒 = 整屏宽以后，滑走的那页是整个滑出屏幕，边上不再剩影子
- 日期条与下方待办列表之间一条浅灰 1px 间隔线（`ft.Divider`，`STRIP_DIVIDER_COLOR = "#F1F5F9"`）；列表每行是时间轴样式：左边时间（居中摆，和日期条头一格的「周一」共用一条中线）+ 点线轴（空心圆紧跟着时间：轴压进时间那一格右边的空里，离卡片留 4px）；**当天弹窗里不摆这一套** —— 走 `show_timeline=False` 的一行只剩卡片自己（左边那格时间、点线、卡片左边让给轴的那一截空当都不要），卡片直接铺满正文的宽，起止时间就在卡片自己那排上；卡片里是**两排、各自水平对齐**：上面一排是「起止时间（「14:00 - 15:30」）—— 类别标签」（中间那格 `expand` 把标签顶到行尾，所以**时间段与标签水平对齐**），下面一排是「勾选框 - 待办文字 - 已完成」（三者同在 `Row` 的 `CENTER` 中线上，「已完成」被 `expand` 的文字顶到**最右**，与文字的间距就是 `Row` 的 `spacing` —— 和左边「勾选框 - 文字」那一档相同）；**待办文字不跟着分类上色**，统一用 `TODO_TEXT_COLOR = #64748B` 的灰字（比「已完成」那档 `#94A3B8` 深一级；分类色只留在那枚标签和时间轴的圆点上，完成的仍变灰加删除线）；主体的**左右内边距对称**（`left = right = DOT_TO_TEXT_GAP`），标签和「已完成」离边都是这么多；左边那格时间是不加粗的灰字，时间轴那列仍然只报**开始时间**；**时间一律不折行**（`ft.Text(no_wrap=True)`）—— 弹窗那档的格子按最宽的「00:00」留到 `TIME_SLOT_WIDTH_DIALOG = 36`（`text_width` 粗估才 30px，真机字距一撑就把「04:05」这类挤出格子折成两行，一折行整条时间轴的高度就被撑起来），轴与卡片由常量链跟着右移同样的量，三者相对位置不变
- 点一行**或点文字前面那枚勾选框**都能切换完成（完成变灰加删除线，并在「勾选框 - 文字」那一行**末尾挂一行灰字「已完成」**（`DONE_LABEL`，灰 `#94A3B8`、字号跟着起止时间那行）—— 它和勾选框、文字**同在一个 `Row` 里、共用 `CrossAxisAlignment.CENTER`**，文字用 `expand` 把它顶到最右，间距用 `Row` 自己的 `spacing`（与左侧一致）；「已完成」离卡片右边的距离 = 左边的 `DOT_TO_TEXT_GAP`，**左右对称**）；勾选框是**方形带圆角**（`TODO_CHECK_SIZE = 16`、圆角 `TODO_CHECK_RADIUS = 5`）：没勾是空心方框（灰框 `#94A3B8` 1.5），勾上了填**青绿底 `#14B8A6` + 一枚黑色对勾 `#000000`**（和列表里那枚圆形的完成标记 `build_todo_mark` 不是一回事，别混着用）；左滑一行露出「编辑 / 删除」
- 空态显示「今天没有待办事项哦」
- 右下角毛玻璃圆形按钮（天蓝 `#B2E0F4` 60% 透明 + Blur 20，图标就是一个「+」`ADD`）：点一下先**从按钮那一角弹出一块毛玻璃小面板**（奶白 `#B3FFFFFF` 70% 透明 + Blur 20，缩放 + 淡入 200ms），面板里两条入口「新增待办 / 新增倒数日」，选完才开对应的新增弹窗；再点一次「+」或点面板外的空白处收起
- 新增待办弹窗只弹出，**不自动聚焦输入框**
- 右上角柱状图图标（`BAR_CHART`）→ 数据二级页

### 新增 / 编辑待办弹窗（`tools/todo_form.py`）
- 分类：**三个胶囊并排（复用 `tools/segmented.py`），单选** —— 选中项填自己的分类色（红 / 黄 / 绿），字色跟着底色挑深浅（黄底深蓝、红 / 绿底白）；点另一档就切过去，点当前这一档不会松开，永远留一个选中。这排用方一点的那款（square=True）：圆角收小，两档之间立一条浅灰竖线，和「数据」页的 年/月/周 胶囊区分开。胶囊底是一层降过白的浅灰白 #F8FAFC（比待办卡片的 #F1F5F9 亮一格）
- 内容：单行输入
- 日期：系统日期选择器（新增时最早只能选今天，编辑可移到过去）
- 时间：一个格写「09:30 - 10:30」，点它**连着弹两个**系统时间选择器（标题分别是「选择开始时间 / 选择结束时间」）—— 一次点击就把起止都选完；开始默认当前时刻向下取整到 5 分钟，结束默认「开始 + 1 小时」，开始往后挪过了结束就把时长补回 1 小时
- 循环：不循环 / 每天 / 三天 / 一周 / **工作日（周一–周五）** / **非工作日（周六周日）** / 一月 / 三月 / 六月 / 一年
- 输入框获得焦点时，底部菜单栏和「+」一起隐藏，弹窗贴到键盘上方（不会被键盘顶飞，也不会有中间那条灰带）

### 倒数日
- 卡片分三段：上段「图标 + 事项」（底色是这张卡自选的颜色）；中段天数大字 + 「天后」色块（**过期的卡片中段写「天前」，天数和状态色跟下段「已过期 N 天」是同一个数**）；下段「日期 · 农历 · 周几」
- 「天后」色块按剩余天数分三档，用的就是待办类别那三色，天数越近越像「重要」：**≥7 天 = 可选绿（`#16A34A`）/ 3–6 天 = 一般黄（`#EAB308`）/ <3 天（含已过）= 重要红（`#DC2626`）**；黄底上的字自动换成深蓝
- 不循环的倒数日**一过到期日就收进底部的「已过期」**（到期当天还留在正列表里），循环的永远等下一次
- 最近的一张通栏，其余按两列排（窄屏自动落成一张）
- 左滑编辑 / 删除；周期和待办共用一套，循环锚点会自动走到下一次（生日只需记一次）
- 列表最底下有一个「已过期 N」开关：没有边框也没有底色，只剩一行**浅灰小字**（`#94A3B8`，12pt）+ 小箭头，点一下展开、再点收起（箭头跟着翻）；展开后过期卡片排在它下面，**全部双列**（谁也不占整行），最近过期的排最前
- 过期卡片就是同一张卡（`expired=True`）：整张卡连图标（`#94A3B8`）、「天前」色块（`#CBD5E1`）一并置灰 —— 上段 `#D5DBE4`、中下段 `#F1F5F9`，三段分界还看得出来（上段这档灰必须比日历弹窗的底色 `DIALOG_SURFACE = #E4E9EF` 深出一截 —— 早先的 `#E2E8F0` 和它只差一两个色阶，过期卡片一进弹窗，上段就跟弹窗底色融成一片，看着像没画背景）；只有下段的日期那行换成「已过期 N 天」，字色仍是灰的；左滑照样能编辑 / 删除
- 一条都没有（未过期的和过期的都没有）才回到「还没有倒数日」空态；只要有过期的，底部就有那个开关
- **倒数日页自己没有「+」**：新增入口统一在待办页右下角那个按钮上（面板里选「新增倒数日」），列表空的时候提示语也指到那里

### 日历
- 月历卡片：日期圈（选中的填蓝）+ 农历 + 有几条待办就画几颗**实心小圆点**（`DOT_SIZE=6`、点距 `DOT_GAP=2`；`item_dot` 里宽高都写死、不带 content，就是图例圆点的画法），从左往右排；格子里不再写待办文字，圆点颜色就是分类色、完成的同色淡一半（`66RRGGBB`）；倒数日用天蓝，**过了那天的那条用灰 `#CBD5E1`**（循环的那条也算：所看那天在今天之前就置灰，和当天弹窗同步）；点多了也不省略，格子横里摆不下就用 `Row` 的 `wrap` / `run_spacing` 自己换到下一行；**已过日期（那天在今天之前）只要还有一条没做完的待办**，那一格就不再摆点，改在日期行下面那块空档里画**一枚居中的红色「×」**（`overdue_count` 判定、`overdue_mark` 画）—— 它和「全做完」那枚绿色对勾是**一对**：尺寸同样取 `DONE_MARK_SIZE=14`、同样占满日期行下面的空档并上下左右居中，只是颜色（`#DC2626`）和「对 / 错」相反；不管有几条没做完都只画一枚，格子高度也就按一行算；**当天的待办全部打完勾时那一格不再画点**，日期行下面那块空档改画一枚**居中的绿色对勾**（`DONE_MARK_SIZE=14`，色取 `layout.TODO_MARK_DONE_BG` `#22C55E`，和首页列表的完成标记同一个绿）—— `item_lines` 用 `all_done(todos)` 判断（当天**有**待办且每条都 `done`；当天没有待办时照旧画倒数日的点，不会被当成「全做完了」），对勾那块的高度正好是「格子高 − 日期行」剩下的空档，图标在里头上下左右居中
- **格子高度是动态算出来的**：`cell_height(rows)` = 日期行 + rows 行圆点（含行距）+ 上下留白（只摆一行那天按对勾的 `DONE_MARK_SIZE` 留高，见上一条）；**待办全做完的那天只按 1 行算**（它只画一枚对勾，不按条目数把整个月的格子撑高）；**一个月里所有格子同高** = `max(正方形底线, cell_height(当月最忙那天要的行数))` —— 底线是 `cell_min_height`（**高 = 一格宽，至少是正方形**，估宽下 `DAY_CELL_HEIGHT ≈ 47`），所以空闲的格子也是方的、点到第三行也不会被格子切掉；一行摆得下几个点由格子实际宽度决定 —— 第一帧先按 `page.width` 算（`estimated_grid_width`；页面还没布局、宽度拿不到时才退回手机竖屏的 `ESTIMATED_PAGE_WIDTH=400`），第一周那行量到真实宽度后（`on_size_change` → `learn_row_width`）换算成每行容量重排一次（`cell_width` / `dots_per_run` / `dot_row_count`），量到的宽度记在页面 `state` 里，切 Tab / 翻月 / 选日期都直接复用，只有热重载才退回估的值。首帧就照真宽度摆，进日历页时整片格子不会「先画一遍再收缩一下」；`learn_row_width` 量出来跟当前这一版一样宽时只记下来、不重排
- 圆点的先后**按时间排**：全天（没填时间）的排最前，其余按时间早晚，同一时间按录入顺序 —— 和首页时间轴、当天弹窗共用 `tools/todo_timeline.py` 的 `sorted_todos`
- 顶部「‹ 年月 ›」翻月；点月份标题**从底部升起一条日期滚轮面板**（`open_date_picker` 用 `ft.BottomSheet`：顶上 `show_drag_handle` 留一枚拖拽手柄，往下拉或点面板外都能关），里头是**系统级的 `ft.CupertinoDatePicker`**（`CupertinoDatePickerMode.DATE`：年、月、日三列滚轮，`date_order=YEAR_MONTH_DAY` 排成「年 | 月 | 日」，年份能滚的范围是 ± `YEAR_SPAN = 10` 年）；滚动只更新草稿（`on_change` 每停一格回一次，不立刻重建日历），点「确定」才跳过去（`jump_to_day`）：日历翻到那天所在的月份，并**选上那一天** —— Material 那款 `ft.DatePicker` 是居中弹窗、还得在里头的日历上找日子，所以这里用 Cupertino 的滚轮
- 点任意日期 → 弹窗列出当天全部内容：待办（**一列卡片，不摆时间轴** —— 左边那格时间和点线都没有，卡片铺满正文的宽，可左滑编辑 / 删除）+ 倒数日（卡片，**过了的也置灰**：只要所看那天在今天之前，这一次的倒数日就按过期样式 —— 循环的那条也算，`countdown_expired` 只判不循环的那条，循环的按设计永远等下一次、它判不出来；天数一律按**所看那天 − 今天**算 —— 正数还有几天、负数已过几天、0 就是今天，**中段和下段共用这一个数**（过期时中段写「N 天前」、下段写「已过期 N 天」，连状态色都是同一档灰），不能靠 `next_occurrence` 反推，那会推到还在未来的下一次去、天数成负的）；空态「这天没有待办事项」
- 弹窗高度**按内容的多少来**：够矮时贴着内容收缩，只有量出来超过 `DIALOG_BODY_MAX_HEIGHT`（330）才把正文钉在这个高度上、打开滚动（`ScrollMode.HIDDEN`，不画滚动条）；第一帧先按 `estimate_day_height` 估的高度撑起来（**估高不估矮**），量到真高度再收回去 —— 内容多的那些天点开时不会先按全部内容闪一下、把弹窗撑高。粗算漏掉的是字体行高、标签高度这些固定量，所以「一条差多少」会摊到条数上记进页面 `state`（`DAY_HEIGHT_SLACK_KEY`），下一次估的时候补上：点开两三次之后第一帧就是最终高度，弹窗不再有那一下上下撑开 / 收回
- 弹窗里**日期行和右上角「×」钉在顶上**：它们放在 `AlertDialog` 的标题槽里、弹窗 `scrollable=False`，滚的只有正文那一个 `Column`
- 右上角齿轮 → 设置二级页

### 数据（二级页，从待办页右上角进入）
- 顶部左边「‹ 返回」回到待办页，标题「数据」居中
- **数据统计**：三张分类卡（重要 / 一般 / 可选），每张显示「全部 / 已完成 / 未完成 / 完成率」，完成率低于 50% 标红，无数据显示「—」
- **分类占比**：饼图（`flet-charts`），悬停 / 点按扇区凸出，圆心显示总数，右侧图例
- **待办趋势**：多系列折线图（`flet-charts`），三条线 = 三个类别，点按数据点弹出数值；X 轴随周期变化（年 = 12 个月，月 = 当月每天，周 = 周一至周日），左侧有 Y 轴线
- 三张卡各自独立切换 **年 / 月 / 周**，默认「周」；退出去再进来仍是原来那一档

### 设置（二级页，从日历页右上角进入，`pages/preferences.py`）
- 通知渠道：Bark / Pushdeer / Server酱 / 企业微信 / 钉钉 / 飞书 / Telegram / Discord / Slack + 通知地址（存 `settings` 表）
- 清除缓存：二次确认后清空所有待办，并提示清除了多少条
- 云端数据：开关（**占位功能，不落库、不发请求**）

### 二级 / 三级页的返回（`page.views` + `tools/swipe_back.py`）
- 二级 / 三级页各自是**一层压进 `page.views` 的真 `ft.View`**（`navigation.py` 的 `show_layer`），不是在一级页的 `content` 里换控件。所以真机的「返回」—— Android 返回键 / 两侧边缘的返回手势、iOS 的边缘返回 —— 有层可弹：弹掉一层就是回上一页，`page.on_view_pop` 接住这一下、走和「‹ 返回」按钮**同一个** `go_back()`。
- 除了一级页，**在页面上左滑一下**也回上一页：手指往左走够 `SWIPE_BACK_DISTANCE = 24`，或者甩得够快（`SWIPE_BACK_VELOCITY = 300`），都算一次返回；不够就什么都不做 —— 页面不跟手，也没有「滑到一半」的中间态。这两个阈值跟首页切日期那套横滑取同一档，整台机器手感一致。
- 这个手势只绑**横滑那一族**（`on_horizontal_drag_*`），不碰 `on_pan_*`：页面里竖着滚的列表照样抢得走竖滑。起点落在某条左滑行上时，行自己那层在更里面、先进手势竞技场，仍然优先露出编辑 / 删除（和首页同一套安排）。
- 另外两道闸：**竖着划过去的（`|dy| > |dx|`）不算返回**（那其实是页面在自己滚）；**起手点落在屏幕左右各 `SWIPE_BACK_EDGE_INSET = 32` 之内也不算** —— 那两条边是系统手势区，交给系统去弹 View（走上面那条路）就行，App 再接一次就会「一次划掉两层」。
- `go_back()` 只做两件事：把 `page.views` 顶上那层弹掉，再让父层重画自己（父层要么是 `render_data` / `render_preferences` 这种只重画、不动栈的函数，要么是一级页的 `show_page`）。回调外面包了一层 `try/except` + `logger.exception`：返回失败最多是这一下没退，不会把异常漏进事件循环（那会把整个会话带下去，客户端表现为掉线、回到 Flet 首页）。一级页（根）上 `nav_stack` 是空的，`go_back()` 什么也不做 —— 在首页按返回仍然是退出 App，那是系统的正常行为。
- **进 / 退场动画钉成了 `PAGE_TRANSITION = ft.PageTransitionTheme.CUPERTINO`**（在 `navigation.py` 顶部，`page.theme.page_transitions` 五个平台都设它）。Android 那档默认是 `FADE_UPWARDS`、桌面是 `ZOOM`，两者都要**让新旧两页一起淡**：两页同时叠在屏上，这套自己画渐变底的自定义页面就会被看穿，看着像上一个页面留下的残影（进入下一页、退回上一页时都能看到）。`CUPERTINO` 是纯横向推拉 —— 两页各自整块不透明地滑进滑出，前后不叠；配边缘返回手势也是这一档最顺。想干脆不要动画，把它换成 `ft.PageTransitionTheme.NONE` 即可。

---

## 二、目录结构

| 文件 | 行数 | 职责 |
| --- | --- | --- |
| `src/main.py` | 13 | 入口：`db.init_db()` 建库 → `build_navigation(page)` |
| `src/pages/navigation.py` | 297 | 底部毛玻璃菜单 + 3 个 Tab 切换 + 二级页（数据 / 设置）跳转；按页面名保管选择状态；二级 / 三级页各压一层真 `ft.View`（`show_layer`），`nav_stack` 记楼层，返回按钮 / 左滑 / 真机的系统返回（`on_view_pop`）共用 `go_back`；页面动画用 `PAGE_TRANSITION`（横向推拉，不留残影） |
| `src/pages/home.py` | 689 | 待办页：日期条、按天列表、完成切换、毛玻璃「+」面板（新增待办 / 新增倒数日）、右上角「数据」入口 |
| `src/pages/countdown.py` | 250 | 倒数日页：通栏 + 两列卡片列表 + 底部「已过期 N」开关（过期卡片全部双列；没有「+」，新增入口在待办页） |
| `src/pages/calendar.py` | 1016 | 日历页：月历卡片网格、当天详情弹窗、右上角设置入口（月份与选中日期跨 Tab 保留） |
| `src/pages/data.py` | 596 | 「数据」二级页：数据统计 / 分类占比 / 待办趋势三张卡（年/月/周 保留） |
| `src/pages/preferences.py` | 372 | 设置二级页：通知渠道、清除缓存、云端开关 |
| `src/tools/db.py` | 610 | 数据层：建表 / 迁移 / 待办与倒数日 CRUD / 循环展开（含工作日 / 非工作日）/ settings |
| `src/tools/layout.py` | 239 | 全局配色与尺寸常量、页面渐变、二级页顶栏（返回 + 居中标题）、弹窗键盘定位、文字宽度估算、可读字色、时间文案 |
| `src/tools/categories.py` | 62 | 三个类别及其颜色（红 / 黄 / 绿）、星标控件 |
| `src/tools/todo_timeline.py` | 461 | 待办行 / 时间轴（首页一条条搭、日历弹窗整列搭都走它；点线随卡片拉伸、点本身仍是圆点；**轴两端不补点** —— 首行上、末行下都不画小圆点，`first` / `last` 由调用方传；**`show_timeline=False` 只剩下卡片**（待办行、整天的一列都支持这一档），当天弹窗用的就是它） |
| `src/tools/todo_form.py` | 278 | 新增 / 编辑待办弹窗（分类胶囊 + 内容 + 日期 + 起止时间一格 + 周期） |
| `src/tools/swipe_delete.py` | 124 | 左滑露出操作按钮的行容器 |
| `src/tools/swipe_back.py` | 102 | 整页左滑返回上一页的壳（二级 / 三级页用；只绑横滑，竖滑和屏幕两侧的系统手势区都让出去） |
| `src/tools/popup_select.py` | 219 | 统一的下拉选择器（待办/倒数日的日期、类别、循环、通知渠道都用它） |
| `src/tools/segmented.py` | 152 | 横向胶囊分段开关（「数据」页 年/月/周、待办弹窗的三个分类；可一项一色） |
| `src/tools/pickers.py` | 129 | 系统日期 / 时间选择器封装（含 UTC 时区修正、可选标题） |
| `src/tools/countdown_card.py` | 353 | 倒数日卡片（三档状态色、中段钉高所以张张等高、过期不循环的自动收起；`expired=True` 把日期行换成「已过期 N 天」，整张卡连图标、「天前」一并置灰） |
| `src/tools/countdown_form.py` | 237 | 新增 / 编辑倒数日弹窗（含卡片底色选择） |
| `src/tools/line_chart.py` | 365 | 待办趋势折线图（`flet-charts` 多系列 LineChart + 毛玻璃自绘浮框） |
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
        ├── pages/data.py             │
        └── pages/preferences.py    ──┘
              ↓
        tools/*.py                  共享控件与数据层
              ↓
        tools/db.py  ──→  SQLite（dailylist.db）
```

约定：**页面不直接写 SQL**，一律经 `tools/db.py`；**页面不重复造控件**，能共享的（时间轴行、卡片、弹窗、下拉、选择器）都放在 `tools/`。`navigation.py` 每次切页都重建页面控件（`build_xxx_page`），并把 `set_menu_visible` 回调传下去，页面在弹窗 / 键盘出现时用它收起底部菜单和「+」按钮；二级 / 三级页还要接住传下来的 `go_back`（顶栏返回按钮、左滑、真机的系统返回都调它），具体退到哪一层由 `nav_stack`、压了几层由 `page.views` 决定 —— 一级页的外壳在 `views[0]`，往上一层一个 View。

---

## 四、数据（SQLite）

数据库位置（`tools/db.py`）：打包后的 App 目录只读，所以优先用 Flet 给的 `FLET_APP_STORAGE_DATA`；从源码运行时用**项目根目录**的 `dailylist.db`。

| 表 | 列 |
| --- | --- |
| `todos` | `id`, `due_date`(ISO 日期), `due_time`(开始时间 "HH:MM"), `end_time`(结束时间 "HH:MM"，可空), `category`, `content`, `done`, `repeat_cycle`, `created_at`（另有 `idx_todos_due_date` 索引） |
| `countdowns` | `id`, `due_date`, `cycle`, `content`, `bgcolor`, `created_at` |
| `settings` | `name`(主键), `value` |

两个设计点：

- **自动迁移**：`init_db()` 跑 `CREATE TABLE IF NOT EXISTS` + `_add_missing_columns()`，老库缺的列（`repeat_cycle` / `due_time` / `end_time` / `bgcolor`）启动时自动补上，不需要单独的迁移脚本。
- **循环待办物化**：循环不是运行时算的，而是在新增 / 编辑时按周期一次性铺满未来 `REPEAT_HORIZON_DAYS = 365` 天（每天最多 `MAX_OCCURRENCES = 400` 行），这样首页和日历直接查日期区间就行，不需要后台任务。编辑一条循环待办会**整条序列重建**（`db.update_todo`），已完成的按序号保留勾选状态。
- **工作日 / 非工作日**（`db.SKIP_CYCLES`）：这两个周期不是「隔几天一次」的步长，而是**一天一天走日历、只留下属于它的那几类星期**（`_weekday_dates`），所以「工作日」的序列里永远不会冒出周六；锚点自己不在周期里（比如「工作日」挑了周六）时，序列从它之后第一个符合的日子开始。

---

## 五、开发约定

改代码前值得知道的几条（都是踩过坑留下来的）：

1. **颜色 / 尺寸集中在 `tools/layout.py` 和 `tools/categories.py`**：卡片色、选中蓝、完成灰、弹窗圆角（`DIALOG_RADIUS = 12`，Material 默认 28）、弹窗表面色（`DIALOG_SURFACE`）等都在这里，页面里不要再手写十六进制。
2. **下拉一律用 `tools/popup_select.py`**，不要用 `ft.Dropdown`：Dropdown 的触发器是 Material TextField，`InputDecorator` 会在弹层之上再画一遍自己的框，把贴在它下面的面板盖住一半。现在用 `PopupMenuButton + menu_position=UNDER`。例外是「数据」页的 年/月/周 和新增待办弹窗的分类：选项直接摊在卡片标题行 / 弹窗行里，用 `tools/segmented.py` 的横向胶囊开关，点一下就切，不必先点开面板。
3. **弹窗**统一 `shape=RoundedRectangleBorder(radius=DIALOG_RADIUS)` + `bgcolor=DIALOG_SURFACE` + `elevation=0`。
4. **键盘处理**：输入框 `on_focus` 里调 `anchor_dialog_above_keyboard(dialog, True)`（弹窗贴键盘上方）并用 `set_menu_visible(False)` 收起底部菜单和浮动按钮；`on_blur` 复原。
5. **列表底部留白**用 `BOTTOM_MENU_INSET`，否则最后一行会被浮动菜单栏压住。
6. 页面内容滚动一律 `scroll=ft.ScrollMode.HIDDEN` 隐藏滚动条。
7. **折线图的浮框是自绘的**（`tools/line_chart.py`）：fl_chart 的浮框是一个系列一行、每行只能一种颜色（`text_spans` 在 flet-charts 1.0.1 里传不到 Dart 侧，一用整个浮框都画不出来），做不出「灰色日期 + 彩点 + 黑色数值」。所以控件自带的浮框只留一个透明的壳，内容换成挂在 `ft.Stack` 上的 `ft.Container`，由 `LineChart.on_event` 的悬停事件摆位置、换内容。浮框贴在锚点左右：`TIP_OFFSET` 比 fl_chart 10px 的 x 命中半径大，光标压不到它，否则会出现「浮框盖住光标 → 图表 pointerExit → 浮框消失 → 又冒出来」的抖动。浮框是毛玻璃：半透明灰白底（`#CCF1F5F9`，`#AARRGGBB`）+ `blur=ft.Blur(12, 12, ft.BlurTileMode.CLAMP)`，与「+」按钮、底部菜单栏同一套写法。
8. **页面选择状态存在 `pages/navigation.py`**：切页时页面控件是重建的（待办数据要现从 db 读），但「在看哪个月 / 选了哪一档」这类选择必须留住，所以 `build_navigation` 里有一份按页面名索引的 `state_store`，由 `page_state(name)` 按名字取（没有就现建一个空的）；页面把它当自己的草稿本 —— 日历页存 `month` / `day`，数据页存三张卡各自的 年/月/周，只有热重载重跑 `main()` 才会回到初始值。
9. **日历弹窗的高度是「先估后量」**：正文的真高度由 `open_day_dialog` 里那层探针（`on_size_change`）量出来，量一次得等一帧（客户端是 post-frame 回调），所以第一帧先用 `estimate_day_height()` 把 `body.height` / `scroll` 定上。估算**估高不估矮**：估高了下一帧就收回，估矮了弹窗会先按全部内容撑高一下再弹回来 —— 就是「点日期先闪一下全部数据」的样子。
10. **页面的上下层关系只认 `navigation.py` 的 `nav_stack` + `page.views`**（`tools/swipe_back.py` 把左滑接到它上面）：进一层时把「上一层怎么画」压进 `nav_stack`（`render_data` / `render_preferences` 那类只重画、不动栈的函数），`go_back()` 只弹一层 —— 同时弹掉 `page.views` 顶上那层真 View。所以**别在页面里自己写 `show_page(0)` 当返回**，也别在栈里压一个会再压栈的 `show_xxx`；另外别把子页塞回 `content.content`（那样真机的返回就又没有层可弹、直接退出 App 了）。层数多深都按这个来。

---

## 六、运行

依赖（`pyproject.toml`）：`flet >= 1.0.1`、**`flet-charts >= 1.0.1`**（折线图和饼图必需，Flet 1.0 把图表拆成了独立包）。

```bash
uv run flet run          # 桌面窗口
uv run flet run --web    # 浏览器
python src/main.py       # 直接用解释器跑（src 已在 sys.path 上，DB 始终落在项目根）
```

> 本机依赖现状：conda 环境 `D:\ProgramData\miniconda3\envs\flet` 里是 `flet 1.0.1` + `flet-charts 1.0.1`。`flet-charts` 由
> `pages/data.py`、`tools/line_chart.py`、`tools/pie_chart.py` 使用，缺了启动就报 `ModuleNotFoundError: No module named 'flet_charts'`：
>
> ```bash
> pip install "flet-charts>=1.0.1"
> ```
>
> 注意：本机直连 pypi.org 时 pip 会拿到**被截断的 JSON 索引**（`JSONDecodeError: Unterminated string at char 21277`），
> 换国内镜像即可：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple "flet-charts>=1.0.1"`。

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

现状：本机没有安装 dev 依赖（`flet[test]` → pytest / numpy 都缺），跑不起来；而且该测试的断言还停留在旧文案（找「日历页面」「设置页面」），与现在的「日历」「数据 / 设置」不一致，还点了已经不存在的 `settings-tab`，重新启用前需要同步。

## 九、已知问题 / 待办

- **装依赖要用镜像**：从 pypi.org 直装会被截断（见「运行」），本机目前是照镜像那条命令装上的。
- **测试过期**：`tests/test_main.py` 断言与当前 UI 文案不符。
- **通知渠道只有配置**：`tools/notifications.py` 只存渠道名和地址，没有真正发送推送的逻辑。
- **云端数据是占位**：开关不落库、不请求（代码注释里写明「先只做样子」）。
- **仓库里的 `dailylist.db` 是活数据文件**：当前只有 `todos`(204 行) / `settings`，既没有 `countdowns` 表，`todos` 也缺 `due_time` / `end_time` 列 —— 说明该文件早于「倒数日 / 时间」功能，首次运行会被 `init_db()` 自动补齐。它是跟着仓库走的，改动数据会体现为一次文件改动。
- **多实例同时写库**：应用的 DB 路径固定在项目根，同时开多个实例（或一边跑 App 一边跑测试脚本）会互相覆盖数据，调试时注意先关掉旧实例。
- **一级页按返回会退出 App**：二级 / 三级页现在是真 View，系统返回弹的是它们；回到一级页（`page.views` 只剩一层）之后按返回就没有可弹的层了，客户端会结束 Activity、回到 Flet 首页 —— 这是系统返回的正常行为，不是 bug。想在首页也拦住返回，得自己接管客户端的返回事件，Flet 目前没给这层口子。
