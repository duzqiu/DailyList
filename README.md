# 每日清单（DailyList）

用 [Flet](https://flet.dev/)（Flutter + Python）写的本地**待办 / 倒数日** App：一套代码跑 iOS、Android、桌面和 Web，数据存在本地 SQLite，不需要服务端。界面全中文，配色是白 + 天蓝 + 靛蓝的浅色系。

---

## 一、功能

### 待办（首页）
- 顶部「待办」标题 + 7 天日期条（今天排第一个、往后连着 7 天，**每格都写成「09.28」这样的月.日**，字号 10 —— 今天也写日期、不写「今」）；**日期不带底色**，选中的那天只是日期**加粗**，选中标记是日期正下方一条 16×3 的黑横条（`DATE_BAR_*`）：**整条日期条只画这一条**，它钉在日期卡片底边上、紧贴下面那条灰间隔线（日期条与灰线之间那条 10px 的缝挪进了卡片，所以灰线以下一点没动）；点某天、或者**在下方那块（待办列表）上左右滑**（横滑挂在列表外面那层手势上，日期条自己不接；`DATE_SWIPE_DISTANCE` / `DATE_SWIPE_VELOCITY`，左滑看后一天、右滑看前一天，走到头就停住不绕回来；竖着滑还是列表自己滚，起点落在某条待办上时那一条的左滑（露出编辑 / 删除）优先），横条都会按 `offset`（= 选中格中线到日期条中线的距离 ÷ 日期条宽，见 `date_bar_offset`）**慢慢滑到那一格下面**（`DATE_BAR_SLIDE_MS = 500` + `animate_offset`；日期条宽度要等布局完量出来，第一帧先按 `DATE_STRIP_ESTIMATED_WIDTH` 估）；下方是**一叠「一天一页」**（`PAGE_SLIDE_KEY = "date-pages"`），切日期时**整叠滑一格 —— 旧的一页滑出去、新的一页滑进来**（每页 `offset = 该天的下标 − 选中下标`，配 `DATE_PAGE_SLIDE_MS = 500` + `animate_offset`，跟黑横条同一套时间；七页一起摆在栈里，新的一页才有「上一个位置」可以滑过来，见 `slide_pages`）；这一叠**铺满整屏宽** —— 左右那 24px 的边距收进了每一页自己（`Stack` 上 `fit=StackFit.EXPAND`，七页都拉成和叠一样大），`offset` 是按控件**自身宽度**换算的，页盒只有「屏宽 − 48」时「挪一格」也只挪「屏宽 − 48」，屏幕左右那 24px 里就会漏出邻居那一页的一角；页盒 = 整屏宽以后，滑走的那页是整个滑出屏幕，边上不再剩影子
- 日期条与下方待办列表之间一条浅灰 1px 间隔线（`ft.Divider`，`STRIP_DIVIDER_COLOR = "#F1F5F9"`）；列表每行是时间轴样式：左边时间（居中摆，和日期条头一格的「周一」共用一条中线）+ 点线轴（空心圆紧跟着时间：轴压进时间那一格右边的空里，离卡片留 4px）；**当天弹窗里不摆这一套** —— 走 `show_timeline=False` 的一行只剩卡片自己（左边那格时间、点线、卡片左边让给轴的那一截空当都不要），卡片直接铺满正文的宽，起止时间就在卡片自己那排上；**每张待办是一枚便签纸**：**一种纸色**（原来的那块灰 `UNSELECTED_CARD_BG = #F1F5F9`，和数据页卡片、分类 tile 同一档），下沿压一道深一档的边 2px（`CARD_EDGE = #E2E8F0`）当纸的厚度，圆角收到 `CARD_RADIUS = 6`；**完成的也是这张纸**（不再另换底色，那行灰字加删除线已经够区分）。纸边只能用**下边框**画、**不能用 `shadow`**：卡片外面套着左滑那一层（`build_todo_row` 的 `body`），它按卡片的边界裁，投影伸出去的部分会被切掉、剩下的反而像一道硬边；卡片里是**两排**：上面一行起止时间（「14:00 - 15:30」），下面一排是「勾选框 - 待办文字 - 已完成」（三者同在 `Row` 的 `CENTER` 中线上；**「已完成」那块位置一直给它留着** —— 文字容器固定带 `padding-right = DONE_LABEL_GAP + DONE_LABEL_WIDTH`（12 + 「已完成」的宽），而「已完成」本身是外层 `ft.Stack` 的定位子、**不参与这一排的宽度分配**：勾没勾上，`Row` 的子控件都只有「勾选框 + 文字」两项，文字能用的宽度分毫不差、折行也一样，所以**卡片不会点一下就从一行跳成两行**）；**待办文字不跟着分类上色**，统一用 `TODO_TEXT_COLOR = #64748B` 的灰字（比「已完成」那档 `#94A3B8` 深一级；分类色只留在那枚标签和时间轴的圆点上，完成的仍变灰加删除线）；**类别标签贴在卡片右上角、贴近边缘**（外层 `ft.Stack` 的定位子 `top=0, right=0`，盖在正文上面）—— 没有起止时间的那一张，正文会顶到最上面跟它撞上，所以主体顶部垫出标签那块高 `TAG_CLEARANCE`（有时间时时间行本来就压在它那一排，不用垫）；主体的**左右内边距对称**（`left = right = DOT_TO_TEXT_GAP`），「已完成」离边就是这么多；左边那格时间是不加粗的灰字，时间轴那列仍然只报**开始时间**；**时间一律不折行**（`ft.Text(no_wrap=True)`）—— 弹窗那档的格子按最宽的「00:00」留到 `TIME_SLOT_WIDTH_DIALOG = 36`（`text_width` 粗估才 30px，真机字距一撑就把「04:05」这类挤出格子折成两行，一折行整条时间轴的高度就被撑起来），轴与卡片由常量链跟着右移同样的量，三者相对位置不变
- 点一行**或点文字前面那枚勾选框**都能切换完成（完成变灰加删除线，并在「勾选框 - 文字」那一行**末尾挂一行灰字「已完成」**（`DONE_LABEL`，灰 `#94A3B8`、字号跟着起止时间那行）—— 它和勾选框、文字**同在一个 `Row` 里、共用 `CrossAxisAlignment.CENTER`**，文字用 `expand` 把它顶到最右，间距用 `Row` 自己的 `spacing`（与左侧一致）；「已完成」离卡片右边的距离 = 左边的 `DOT_TO_TEXT_GAP`，**左右对称**）；勾选框是**方形带圆角**（`TODO_CHECK_SIZE = 16`、圆角 `TODO_CHECK_RADIUS = 5`）：没勾是空心方框（灰框 `#94A3B8` 1.5），勾上了填**青绿底 `#14B8A6` + 一枚黑色对勾 `#000000`**（和列表里那枚圆形的完成标记 `build_todo_mark` 不是一回事，别混着用）；**刚勾上的那一条，对勾会弹一下**（`build_todo_check` 的 `pop`：先缩到 `CHECK_POP_START = 0.3`，等这一帧布局完 —— `on_size_change` 是布局之后才回的 —— 再放回原大，140ms `EASE_OUT_BACK`）—— 切完成会把整页重铺一遍、换上来的是新控件，没有「上一个状态」可以插值，所以「这次勾的是谁」只能由调用方现告诉它：首页 `toggle_todo` 把它记进 `just_done`，`reload_todos` 铺完就清，取消完成和别的时候重建都不弹；左滑一行露出「编辑 / 删除」
- 空态显示「今天没有待办事项哦」（左边那枚图换成 assets 里的 `CALENDAR_ICON_SRC = icons/calendar.png`，20×20；日历页当天弹窗里那句「这天没有待办事项」用的是同一张、同样 20×20）
- 右下角**没有底色的圆形按钮**（52×52，`bgcolor=ft.Colors.TRANSPARENT` + **一圈 1px 细灰边** `ADD_BUTTON_BORDER = #E2E8F0`（和卡片边、空态提示那圈、倒数日卡片同一个灰；`shape=CIRCLE` 会让这圈边自己走成圆的），只留中间那枚图：assets 里的 `ADD_ICON_SRC = icons/add.png`，缩到 `ADD_ICON_SIZE = 24`；点上去仍有圆形墨迹 —— `IconButton` 的 `style=CircleBorder()` 留着）。原来那块天蓝毛玻璃（`#99B2E0F4` + Blur 20）和 `ADD_BUTTON_BG` / `ADD_BUTTON_BLUR` 两个常量都删了 —— **「只留模糊、不留底色」并不等于清玻璃**：`Container.blur` 是按控件那块**矩形**铺的、不跟着 `shape` 裁圆，压在一直滚动的列表上就是一块方糊斑，比不加还脏；真要清玻璃得把底色和 `clip_behavior` 一起加回来。点一下就**从按钮那一角弹出一块毛玻璃小面板**（奶白 `#B3FFFFFF` 70% 透明 + Blur 20）：玻璃底淡入 160ms，**两条入口是一条一条弹出来的** —— 各自从按钮那一角由小撑到原大（220ms，`EASE_OUT_BACK` 带一点过冲，像弹出菜单那样顿一下），第二条比第一条晚 `CHOOSE_STAGGER_MS = 70ms` 起步；收起不做错峰，一下收掉才跟手。选完才开对应的新增弹窗；再点一次按钮或点面板外的空白处收起。按钮**始终是这一张图**，点前点后都一样 —— 不换图标、也不转（试过「转一圈变 ×」，旋转量按圈还是按弧度都对不上、两个图标的号也配不平，干脆去掉）。**这是 `ft.IconButton.icon` 收控件的用法**（Flet 1.0 里那个字段的类型是 `IconData | Control`）：按钮本身（圆形墨迹、`tooltip`、48×48 点击区）一个都不用改，只是图标从字形换成图 —— 尺寸也因此从 `icon_size` 挪到图自己身上，`icon_color` 对图无效（图是什么色就是什么色）
- 新增待办弹窗只弹出，**不自动聚焦输入框**
- 右上角**原来那枚「数据」入口已经挪到日历页**（和设置并排、数据在左，见下面日历页那节）：待办页右上角现在空着。图标仍是 assets 里的柱状图（不是内置的 `Icons.BAR_CHART`，原来那档天蓝 `DATA_ICON_COLOR` 早就删了）

### 新增 / 编辑待办弹窗（`tools/todo_form.py`）
- 分类：**三个胶囊并排（复用 `tools/segmented.py`），单选** —— 选中项填自己的分类色（红 / 黄 / 绿），字色跟着底色挑深浅（黄底深蓝、红 / 绿底白）；点另一档就切过去，点当前这一档不会松开，永远留一个选中；切的时候旧的底色与字淡出、新的淡入（`SEGMENT_SWITCH`，180ms —— `ft.Text` 的字色没法直接做动画，所以一档的文字摆两份叠着交叉淡入）。这排用方一点的那款（square=True）：圆角收小，两档之间立一条浅灰竖线，和「数据」页的 年/月/周 胶囊区分开。胶囊底是一层降过白的浅灰白 #F8FAFC（比待办卡片那张灰纸 #F1F5F9 亮一格）
- 内容：单行输入
- 日期：系统日期选择器（新增时最早只能选今天，编辑可移到过去）
- 时间：一个格写「09:30 - 10:30」，点它**连着弹两个**系统时间选择器（标题分别是「选择开始时间 / 选择结束时间」）—— 一次点击就把起止都选完；开始默认当前时刻向下取整到 5 分钟，结束默认「开始 + 1 小时」，开始往后挪过了结束就把时长补回 1 小时
- 循环：不循环 / 每天 / 三天 / 一周 / **工作日（周一–周五）** / **非工作日（周六周日）** / 一月 / 三月 / 六月 / 一年（十档，下拉面板钉成固定高度 `MENU_HEIGHT`（184，6 行），多出来的在面板里上下滚；倒数日弹窗的周期下拉同样处理）
- 输入框获得焦点时，底部菜单栏和「+」一起隐藏，弹窗贴到键盘上方（不会被键盘顶飞，也不会有中间那条灰带）

### 倒数日
- 卡片分三段：上段「图标 + 事项」（底色是新增时从 `CARD_COLORS` 里**随机**挑的那个浅色）；中段天数大字 + 「天后」色块（**过期的卡片中段写「天前」，天数和状态色跟下段「已过期 N 天」是同一个数**）；中下两段之间是一排**定大又定距**的细小圆点（`DOT_SIZE = 2`、点距 `DOT_GAP = 2`，中心距恒为 4；卡片宽就多摆几个点、窄就少摆几个 —— 点数由量到的宽度按定死的点距算，所以通栏和双列是同一条点线，不会像摊开间距那样在通栏上变稀）；下段「日期 · 农历 · 周几」
- 「天后」色块按剩余天数分三档，用的就是待办类别那三色，天数越近越像「重要」：**≥7 天 = 可选绿（`#16A34A`）/ 3–6 天 = 一般黄（`#EAB308`）/ <3 天（含已过）= 重要红（`#DC2626`）**；黄底上的字自动换成深蓝
- 不循环的倒数日**一过到期日就收进底部的「已过期」**（到期当天还留在正列表里），循环的永远等下一次
- 最近的一张通栏，其余按两列排（窄屏自动落成一张）
- 左滑编辑 / 删除；周期和待办共用一套，循环锚点会自动走到下一次（生日只需记一次）
- 列表最底下有一个「已过期 N」开关：没有边框也没有底色，只剩一行**浅灰小字**（`#94A3B8`，12pt）+ 小箭头，点一下展开、再点收起（箭头跟着翻）；展开后过期卡片排在它下面，**全部双列**（谁也不占整行），最近过期的排最前
- 过期卡片就是同一张卡（`expired=True`）：整张卡连图标（`#94A3B8`）、「天前」色块（`#CBD5E1`）一并置灰 —— 上段 `#D5DBE4`、中下段 `#F1F5F9`，三段分界还看得出来（上段这档灰必须比日历弹窗的底色 `DIALOG_SURFACE = #E4E9EF` 深出一截 —— 早先的 `#E2E8F0` 和它只差一两个色阶，过期卡片一进弹窗，上段就跟弹窗底色融成一片，看着像没画背景）；只有下段的日期那行换成「已过期 N 天」，字色仍是灰的；左滑照样能编辑 / 删除
- 一条都没有（未过期的和过期的都没有）才回到「还没有倒数日」空态；只要有过期的，底部就有那个开关
- **倒数日页自己没有「+」**：新增入口统一在待办页右下角那个按钮上（面板里选「新增倒数日」），列表空的时候提示语也指到那里

### 日历
- 月历卡片：日期圈（选中的填蓝）+ 农历 + 有几条待办就画几颗**实心小圆点**（`DOT_SIZE=6`、点距 `DOT_GAP=2`；`item_dot` 里宽高都写死、不带 content，就是图例圆点的画法），从左往右排；格子里不再写待办文字，圆点颜色就是分类色、完成的同色淡一半（`66RRGGBB`）；倒数日用天蓝，**过了那天的那条用灰 `#CBD5E1`**（循环的那条也算：所看那天在今天之前就置灰，和当天弹窗同步）；点多了也不省略，格子横里摆不下就用 `Row` 的 `wrap` / `run_spacing` 自己换到下一行；**已过日期（那天在今天之前）只要还有一条没做完的待办**，那一格就不再摆点，改在日期行下面那块空档里画**一枚居中的红色「×」**（`overdue_count` 判定、`overdue_mark` 画）—— 它和「全做完」那枚对勾图是**一对**：尺寸同样取 `DONE_MARK_SIZE=14`、同样占满日期行下面的空档并上下左右居中，只是颜色（`#DC2626`）和「对 / 错」相反；不管有几条没做完都只画一枚，格子高度也就按一行算；**当天的待办全部打完勾时那一格不再画点**，日期行下面那块空档改画一枚**居中的对勾图**（`CHECK_ICON_SRC = icons/check.png`，缩到 `DONE_MARK_SIZE=14`；原来那枚内置 `Icons.CHECK` 和一档绿 `TODO_MARK_DONE_BG` 都删了 —— 图的颜色就是它自己的）—— `item_lines` 用 `all_done(todos)` 判断（当天**有**待办且每条都 `done`；当天没有待办时照旧画倒数日的点，不会被当成「全做完了」），对勾那块的高度正好是「格子高 − 日期行」剩下的空档，图标在里头上下左右居中
- **格子高度是动态算出来的**：`cell_height(rows)` = 日期行 + rows 行圆点（含行距）+ 上下留白（只摆一行那天按对勾的 `DONE_MARK_SIZE` 留高，见上一条）；**待办全做完的那天只按 1 行算**（它只画一枚对勾，不按条目数把整个月的格子撑高）；**一个月里所有格子同高** = `max(正方形底线, cell_height(当月最忙那天要的行数))` —— 底线是 `cell_min_height`（**高 = 一格宽，至少是正方形**，估宽下 `DAY_CELL_HEIGHT ≈ 47`），所以空闲的格子也是方的、点到第三行也不会被格子切掉；一行摆得下几个点由格子实际宽度决定 —— 第一帧先按 `page.width` 算（`estimated_grid_width`；页面还没布局、宽度拿不到时才退回手机竖屏的 `ESTIMATED_PAGE_WIDTH=400`），第一周那行量到真实宽度后（`on_size_change` → `learn_row_width`）换算成每行容量重排一次（`cell_width` / `dots_per_run` / `dot_row_count`），量到的宽度记在页面 `state` 里，切 Tab / 翻月 / 选日期都直接复用，只有热重载才退回估的值。首帧就照真宽度摆，进日历页时整片格子不会「先画一遍再收缩一下」；`learn_row_width` 量出来跟当前这一版一样宽时只记下来、不重排
- 圆点的先后**按时间排**：全天（没填时间）的排最前，其余按时间早晚，同一时间按录入顺序 —— 和首页时间轴、当天弹窗共用 `tools/todo_timeline.py` 的 `sorted_todos`
- 顶部「‹ 年月 ›」翻月；点月份标题**从底部升起一条日期滚轮面板**（`open_date_picker` 用 `ft.BottomSheet`：顶上 `show_drag_handle` 留一枚拖拽手柄，往下拉或点面板外都能关），里头是**系统级的 `ft.CupertinoDatePicker`**（`CupertinoDatePickerMode.DATE`：年、月、日三列滚轮，`date_order=YEAR_MONTH_DAY` 排成「年 | 月 | 日」，年份能滚的范围是 ± `YEAR_SPAN = 10` 年）；滚动只更新草稿（`on_change` 每停一格回一次，不立刻重建日历），点「确定」才跳过去（`jump_to_day`）：日历翻到那天所在的月份，并**选上那一天** —— Material 那款 `ft.DatePicker` 是居中弹窗、还得在里头的日历上找日子，所以这里用 Cupertino 的滚轮
- 点任意日期 → 弹窗列出当天全部内容：待办（**一列卡片，不摆时间轴** —— 左边那格时间和点线都没有，卡片铺满正文的宽，可左滑编辑 / 删除）+ 倒数日（卡片，**过了的也置灰**：只要所看那天在今天之前，这一次的倒数日就按过期样式 —— 循环的那条也算，`countdown_expired` 只判不循环的那条，循环的按设计永远等下一次、它判不出来；天数一律按**所看那天 − 今天**算 —— 正数还有几天、负数已过几天、0 就是今天，**中段和下段共用这一个数**（过期时中段写「N 天前」、下段写「已过期 N 天」，连状态色都是同一档灰），不能靠 `next_occurrence` 反推，那会推到还在未来的下一次去、天数成负的）；空态「这天没有待办事项」
- 弹窗高度**按内容的多少来**：够矮时贴着内容收缩，只有量出来超过 `DIALOG_BODY_MAX_HEIGHT`（330）才把正文钉在这个高度上、打开滚动（`ScrollMode.HIDDEN`，不画滚动条）；第一帧先按 `estimate_day_height` 估的高度撑起来（**估高不估矮**），量到真高度再收回去 —— 内容多的那些天点开时不会先按全部内容闪一下、把弹窗撑高。粗算漏掉的是字体行高、标签高度这些固定量，所以「一条差多少」会摊到条数上记进页面 `state`（`DAY_HEIGHT_SLACK_KEY`），下一次估的时候补上：点开两三次之后第一帧就是最终高度，弹窗不再有那一下上下撑开 / 收回
- 弹窗里**日期行和右上角「×」钉在顶上**：它们放在 `AlertDialog` 的标题槽里、弹窗 `scrollable=False`，滚的只有正文那一个 `Column`
- 右上角**两枚入口并排摆：数据在左、设置在右**（`DATA_ICON_SIZE` / `SETTINGS_ICON_SIZE` 都是 22），各自那圈 6px 点击留白挨在一起、看着就是 12px 的间距（`TOPBAR_ICON_GAP = 0`）。两枚都是从内置图标换成 assets 里的图（`icons/data.png` / `icons/settings.png`，256×256，`ft.Image` 缩到 22、`fit=CONTAIN`）→ 数据 / 设置二级页。**数据那枚原来挂在待办页的右上角**：两个入口分在两张一级页上，想找哪个都得先猜它挂在谁那儿，现在归到一处，日历页一眼看全

### 数据（二级页，从日历页右上角进入）
- 顶部左边「‹ 返回」回到进来时的那一页（一级页），标题「数据」居中
- **数据统计**：**一枚小长方卡**，宽度是**动态**的 —— `stats_card_width(page)` = 卡片可用宽（`card_area_width()`：**页面宽减去两侧 24**，**不设上限**，窗口一变就跟着变）减掉中间那道缝（12）再**平分**、**往下取整**（手机上 157、414 的屏上 177、宽屏按一半涨）；**高度跟着内容走** —— `build_card(..., width=...)` 只给宽、不写高，所以**半圆下面不留空白**；和「分类占比」并排摆在一层 `Row` 里（`wrap=True`、顶对齐），否则 ListView 会把子项拉满整行宽、小卡又变回通栏。这一张还和别的卡都不同：**底色透明**（`build_card(..., bgcolor=None)`：卡片不铺色，环浮在页面渐变上，只留那圈 1px 边框）、**内边距更小**（`STATS_CARD_PADDING_H/V = 12/8`，所以**标题行贴着上边框**）、**标题 11pt 而且是灰的**（`CARD_TITLE_SIZE = 11` / `CARD_TITLE_COLOR = MUTED_COLOR`，是 `build_card` 的默认 —— **这一页三张卡的标题都这一套**）、年/月/周 用**紧凑款**胶囊（`build_segmented(..., compact=True)`：格高 16、字号 8、左右内边距 5，宽 64）、环画布 = 卡内宽但**收在 `RING_MAX_WIDTH = 260`**（宽屏上卡片很宽，环别跟着无限拉长 —— 它的字和圆点是定号的；手机这种窄屏够不到这个上限，就是「卡内宽」）；环那一行的高度不是它自己天生的半圆高，而是和「分类占比」共用的 `figure_height`（= 饼的直径，见下一条），半圆在里头居中。宽度下限 `STATS_CARD_MIN_WIDTH = 142`：「标题 44 + 间隙 6（`STATS_CARD_TITLE_GAP`）+ 紧凑胶囊 64 = 114」加左右内边距 24 是 138、再留 4px 余量；窄到这个下限时两张卡会折成两行。卡内那一列从**顶上**排，装环那一行**不加 `expand`**（卡高跟着内容走，那一行再撑高就会在环下面多出一块）。里面是一枚**半圆完成率环**（`tools/half_ring.py`），画的是**全部待办**在这一档（年/月/周）的完成率。**进度不填色**：整条半圆本身就是刻度 —— 切成 `TRACK_SEGMENTS = 32` 小段，每段插一个从浅 `#BAE6FD` 到深 `#0369A1` 的实色，看着就是一条由浅到深的弧；**进度由一个圆点指示** —— 进页面时圆点从最左边（0%）**走到**完成率那一格（`sweep`：24 步、700ms、缓出，环里那个百分比跟着一起涨；切 年/月/周 时从当前那格接着走、不是从 0 重来；连点两下由 `sweep_token` 让前一次自己退出），圆点的颜色就取那一格的深浅（越靠右越深）。环里只写「**完成率大字 + 完成率**」两个字段（低于 50% 数字标红、否则绿；这一档没有待办时写「—」、圆点停在起点）。环的画法见 `tools/half_ring.py`：`PieChart` 只画上半圈（`start_degree_offset = 180` 从九点钟起笔，扫到三点钟），下面那半个圆压根不画；**别改用扇区的 `gradient`** —— fl_chart 是按扇区自己的包围盒算渐变的，半圆那段的包围盒中心不在圆心，渐变会歪
- **分类占比**：和「数据统计」**同款小卡、并排摆在它右边**（同宽 `stats_card_width()`、透明底、11pt 灰标题、紧凑款胶囊、高度跟内容走；两张宽度 + 中间那道缝正好铺满一行，窄屏会折行、顶对齐）。内容是饼图 + **右边一列图例**（`● 重要 3` 一行一个分类，8pt）。**两张卡等宽也等高**：宽度都取 `stats_card_width()`（平分，见上一条），高度都不写，图上那一行给的是**共同高度** —— 饼的直径取「卡内宽 − 图例宽（36，估算，实际约 35）− 缝（6）」和「环高 × `PIE_GROW = 1.4`」里的小者。**窄屏上卡住饼的是宽度那条**（手机：91 = 133 − 36 − 6，已经顶到图例），`PIE_GROW` 只在宽屏兜底（768 的窗口上饼 182、环盒 130）；环的高度是天生的半圆高，饼不该跟着那么小，所以这样两张卡的图上那一行还是一样高（手机上 91），环在里头**居中**（上下各让出约 12px）。于是两张的内容高完全相等、谁也不用靠底部留白来凑。悬停 / 点按扇区凸出，**半径按画布大小等比缩**（`tools/pie_chart.py` 的 `pie_scale`：原来那套半径是按 152 的画布调的，小卡里整张饼小一圈，凸出那一下也不会顶出画布）；圆孔是**透明**的（卡片透明底，露出来的是页面渐变），孔小、只放得下总数一个数字（各分类的条数在图例里）
- **待办趋势**：多系列折线图（`flet-charts`），三条线 = 三个类别，点按数据点弹出数值；X 轴随周期变化（年 = 12 个月，月 = 当月每天，周 = 周一至周日），左侧有 Y 轴线。**标题和上面两张卡一样是 11pt 灰字**（`build_card` 的默认就是这一套）、年/月/周 也用**紧凑款**胶囊（标题行 30 → 22），折线画布的高度**保持原来那一档**（`TREND_HEIGHT = 150`，三条线要看得清，图不能压太扁），卡的整体高度靠另外两处收：**图例贴住画布**（`TREND_GAP = 0`，原来写死 8 —— 画布底边本来就留着 X 轴标签那一截，图例紧接在下面看着仍是一条）+ 标题行用紧凑款胶囊（30 → 22），整卡高约 **225**（原来约 241）。**卡片底色透明**（`build_card(..., bgcolor=None)`，和上面两张小卡一个材质）：折线图本身就不带底色（网格线 `#E2E8F0`、坐标轴文字 `#64748B` 都是画上去的，`LineChart.bgcolor` 是 `None`、外面那层 `Stack` 也没有底色），所以卡片一透明，图就直接落在页面渐变上
- 三张卡各自独立切换 **年 / 月 / 周**，默认「周」；退出去再进来仍是原来那一档

### 设置（二级页，从日历页右上角进入，`pages/preferences.py`）
顶栏下面**先是一行设备 ID**（`device_label()`：`设备 ID：9F3A1B2C-…`，就是数据按它存取的那个主键，见 tools/db.py 的 `data_owner`；拿不到设备标识的平台写「设备 ID：未获取到（数据按默认一份存取）」）。**显示时只留冒号后面那截** —— `ios:` / `windows:` 这些前缀是 tools/device.py 的 `_compose` 加的（防两个平台的标识恰好撞上），摆给人看没意义，存储里那份照旧带着。它是排查「换机之后数据怎么都不见了」的第一个线索，所以摆在 ListView 的**第一项**（三档卡片上面、不进卡片）—— 但**跟着内容一起滚**，不钉在顶上：它不常看，没必要一直占着版面。UUID 那种没空格的长串一号字也放不下时宁可省略（`no_wrap` + 省略号），别折成两截把卡片顶下去。

下面是**三档卡片**（`settings_section`：卡片上方一行灰字小标题，条目摆在自己那张卡片里；`setting_row` 是卡片里的一行 = 左「标题 + 小字说明」+ 右动作控件）：
- **通知设置** → **通知提醒**（卡片里自己一行的一个总开关 `ft.Switch`，**不放在「通知渠道」弹窗里** —— 它管「发不发」，弹窗里那两项管「怎么发」；拨一下就**立刻落库**（和云端那个开关一个做法，没有「保存」按钮），switch 的 `on_change` 照例**构建后**再挂（`ft.Switch(on_change=...)` 是构建时求值，写在处理函数之前会 `UnboundLocalError`）；状态存 `settings` 的 `notify_enabled`（`"1"` / `"0"`），**默认关着**：通知是这个 App 唯一会往外发东西的能力，不该在用户还没表态时替他打开。拨完做两件事：换自己那行小字（「有新提醒时按下面的渠道推送」/「关着的时候不推送提醒」）、弹一句 toast（「已开启通知提醒」/「已关闭通知提醒」）。**它不改「通知渠道」那行的摘要** —— 那行只说渠道和地址配没配好（`notifications.summary(channel, url)`），和总开关是两码事，联动的话关掉提醒就看不见地址到底填了没有）、通知渠道：Bark / Pushdeer / Server酱 / 企业微信 / 钉钉 / 飞书 / Telegram / Discord / Slack + 通知地址（存 `settings` 表）。下拉**每一项和触发按钮都带渠道图标**（`notifications.CHANNEL_ICONS` / `channel_icon()`：Telegram、Discord、微信是官方品牌图标，其余挑意思最近的一枚；图标 `CHANNEL_ICON_SIZE = 16`、`apply_text_scaling=False`，**宽度要算进面板宽度**，否则行宽被钉死会把名字挤出去）；**面板钉成固定高度**（`menu_height=MENU_HEIGHT`，9 个渠道在里面上下滚）。卡片里那行摘要**不折行**（`no_wrap` + `TextOverflow.ELLIPSIS`）—— 带 `access_token` 的地址能到 580px 宽，而卡片里只放得下 260px，一折就把卡片顶高、地址还断在半截；弹窗里那一格地址**分成「看」和「改」两层**：平时是一行省略号收尾的 `ft.Text`（点一下才换成输入框，**光标直接落进去**：`autofocus=True` 管控件挂上去那一帧，再补一次 `await url_field.focus()`；注意 **`focus()` 是 async 方法、不是布尔字段** —— 写成 `url_field.focus = True` 只会把方法覆盖掉，客户端一点动静都没有，就是「点了光标不出来」。切换后高度不变，都按 `URL_FIELD_HEIGHT = 40`）—— 因为 **Flet 的 `TextField` 没有 `overflow`**，长链接塞进去只会被硬裁（右边直接切掉、连省略号都不给），省略号只有 `Text` 上有；换成输入框后是单行（`multiline=False`），长地址在格子里横向滚。**键盘跟随走 `track_keyboard(page, dialog)`**（和新增待办 / 新增倒数日那两个弹窗一个做法）：`on_focus` / `on_blur` 只负责 `set_menu_visible`，**不碰弹窗位置** —— 焦点事件比键盘动画早到一步，照它挪会先往屏幕底下一沉、键盘真升起来再弹回来（就是「先下拉再弹起」那个抖动，见约定 4）；弹窗关掉时（取消 / 保存两处）调 `unwatch_keyboard()` 把 media 处理还原
- **数据设置** → 导出数据（**导出为 JSON**：`tools/data_export.py` 把待办 / 倒数日 / 设置拍成一份 JSON，经 `FilePicker.save_file(src_bytes=...)` 交给系统 —— 桌面弹「另存为」，手机和 Web 上表现为导出 / 下载；小字与对话框标题都写明是 JSON）、**导入数据**（**从 JSON 恢复**：`tools/data_import.py` —— 按下去先二次确认，再 `pick_files(with_data=True)` 选文件；**待办与倒数日整表替换**、设置逐条覆盖；文件必须验明正身（只认本 App 导出的 `format` 标记），认不出就拒 —— 不然随手选个别的 JSON 就把库清了）、云端数据：开关（**开关状态存 `settings` 的 `cloud_enabled`**：开 = `"1"`、关 = `"0"`，所以关掉再进来还是关着；同步本身仍是占位，不发请求）。**默认关着**（云端同步是后加的能力，不在用户没表态时就替他打开）；那一行小字不是死文案，跟着开关在「数据只保存在本机」（关）和「本地数据会同步到云端」（开）之间换；**开、关各弹一句提示**（「已开启云端同步」/「已关闭云端同步」）—— 这个开关管的是「数据出不出本机」，值得让用户知道刚做了什么。四条文案集中在 `CLOUD_ON_LABEL` / `CLOUD_OFF_LABEL` / `CLOUD_ON_TOAST` / `CLOUD_OFF_TOAST`，免得两边对不上
- **通用设置** → **检查新版本**（右侧就是当前版本号 `v0.1.0`，**点整行**去仓库问一次：先看 `releases/latest`、没发过 Release 就退到 `tags`，比完弹一句 —— 「发现新版本 vX.Y.Z」/「已是最新版本」/「还没有已发布的版本」/「检查失败，请稍后重试」，请求期间右边先显示「检查中…」。当前版本是 `tools/version_check.py` 的 `APP_VERSION`，和 `pyproject.toml` 的 `version` 是一对，改版本号得两处一起改）、**联系方式**（`tools/contacts.py` 里逐条列：邮箱、微信；**值同样存在 `settings` 表**（`contact_email` / `contact_wechat`），启动时 `contacts.ensure_defaults()` 把表里还没有的补上默认值 —— 所以以后改联系方式只要改表、不必动代码，导出 / 导入也会带着它们走；**点一下复制到剪贴板**并弹一句**屏幕中间**的提示「已复制邮箱 / 已复制微信」（走 `tools/toast.py`），右侧一枚复制图标当提示）、清除缓存（二次确认后清空所有待办，并提示清除了多少条）
- 页面**最下方**是**一行**居中署名（`app_info()`）：`每日清单 v0.1.0 · © 2026 duzqiu` —— App 名用常量 `APP_NAME`（和 `pyproject.toml` 的 `product` 是一对），版本直接引 `version_check.APP_VERSION`（不在这里重复一个字面量），版权年份发版时改 `APP_COPYRIGHT`。它摆在 ListView 末尾、**跟着内容一起滚**，不是固定底栏；宽度拉满靠 `text_align=CENTER` 居中，字色比卡片里的说明还浅一档（落款不抢内容），183px 宽、窄屏也放得下

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
| `src/main.py` | 37 | 入口（**`async def main`**，`ft.run` 支持协程入口）：`db.init_db()` 建库 → `app_settings.ensure_defaults()` 补默认设置项 → **`db.set_data_owner(await device.read_key(page))`** 问一次设备信息当数据主键（`get_device_info()` 是协程，所以要 async；这一步顺带认领老数据）→ **`register_app_services(page)`** 注册 Service（剪贴板 / 文件选择器，**必须赶在页面首次发给客户端之前**）→ `build_navigation(page)`；`ft.run(main, assets_dir=ASSETS_DIR)` 显式给出资源目录（见约定 11） |
| `src/pages/navigation.py` | 303 | 底部毛玻璃菜单（**这一排三个 Tab 都用内置图标**：待办 `HOME` / 倒数日 `HOURGLASS` / 日历 `CALENDAR_MONTH`，选中与未选中是「实心 / 空心」那一对 —— 全 App 只有这一处没用 assets 里的图） + 3 个 Tab 切换 + 二级页（数据 / 设置）跳转；按页面名保管选择状态；二级 / 三级页各压一层真 `ft.View`（`show_layer`），`nav_stack` 记楼层，返回按钮 / 左滑 / 真机的系统返回（`on_view_pop`）共用 `go_back`；页面动画用 `PAGE_TRANSITION`（横向推拉，不留残影） |
| `src/pages/home.py` | 792 | 待办页：日期条、按天列表、完成切换、毛玻璃「+」面板（新增待办 / 新增倒数日）、空态提示（`icons/calendar.png`）、「+」按钮（透明底 + 1px 细灰边 + `icons/add.png`，走 `IconButton.icon` 收控件那一手）—— 右上角那枚「数据」入口已挪到日历页 |
| `src/pages/countdown.py` | 250 | 倒数日页：通栏 + 两列卡片列表 + 底部「已过期 N」开关（过期卡片全部双列；没有「+」，新增入口在待办页） |
| `src/pages/calendar.py` | 1122 | 日历页：月历卡片网格（当天待办全做完那格画 `icons/check.png`）、当天详情弹窗（含空态那枚 `icons/calendar.png`）、右上角**两枚入口 —— 数据（`icons/data.png`）+ 设置（`icons/settings.png`），数据在左**；月份与选中日期跨 Tab 保留 |
| `src/pages/data.py` | 621 | 「数据」二级页：数据统计 + 分类占比（**两张同款小卡并排**）/ 待办趋势三张卡（年/月/周 保留） |
| `src/pages/preferences.py` | 905 | 设置二级页：顶栏下一行**设备 ID**（`device_label()`），下面三档卡片 —— 通知设置（通知提醒开关、通知渠道）、数据设置（导出 / 导入 JSON、云端开关）、通用设置（检查新版本、联系方式、清除缓存），末尾一行署名 |
| `src/tools/db.py` | 819 | 数据层：建表 / 迁移 / **按设备隔离**（`todos` / `countdowns` 各带 `owner` 列，读写一律 `owner = data_owner()`；settings 不分设备）/ `set_data_owner()`（记下设备键 + **只做一次**的老数据认领，见下）/ 待办与倒数日 CRUD / 循环展开（含工作日 / 非工作日）/ `list_all_todos()`、`list_settings()`（导出用）/ `replace_data()`（导入用：只替换**本机**的行，**原样存、不展开**） |
| `src/tools/device.py` | 68 | 设备主键（`key_from(info)` 纯函数 + `read_key(page)` 协程）：iOS `identifier_for_vendor` / macOS `system_guid` / Windows `device_id` / Linux `machine_id`，拼成 `平台:标识`；**Android 与 Web 返回空串**（拿不到唯一标识：Android 的 `id` 其实是 `Build.ID` 构建号、同型号全一样）—— 空串就是"默认那一份" |
| `src/tools/data_export.py` | 73 | 导出数据：把库里的待办 / 倒数日 / 设置拍成一份 JSON（`export_bytes()` 出字节、`export_file_name()` 出文件名；中文不转义，文件里带 `format` / `version` 标记） |
| `src/tools/data_import.py` | 157 | 导入数据：把 `data_export` 那份 JSON 解析后写回库（`import_bytes()`；`ImportFailed` 的消息是写给用户看的一句话；坏行跳过并计数）。**坑**：写回去必须**原样**，别改成 `db.add_todo()` —— 文件里的循环待办本来就是铺开后的行，再展开一次一天变一年 |
| `src/tools/layout.py` | 328 | 全局配色与尺寸常量、**assets 里那几张图的路径**（`ADD_ICON_SRC` / `DATA_ICON_SRC` / `CALENDAR_ICON_SRC` / `SETTINGS_ICON_SRC` / `CHECK_ICON_SRC`，日历那一张三处共用）、页面渐变、二级页顶栏（返回 + 居中标题）、弹窗键盘定位、**`is_mounted` / `update_if_mounted`**（异步回调里刷界面用，见约定 13）、文字宽度估算、可读字色、时间文案 |
| `src/tools/toast.py` | 76 | 居中的 toast 提示（`build_toast(page, message)`）：`SnackBar` 用 FLOATING 档 + 「(屏高 − 48) / 2」的底部留白顶到**屏幕正中**，宽度按文字估、封顶 `TOAST_MAX_WIDTH = 240`；各页面的提示统一走它，别再自己拼 SnackBar |
| `src/tools/services.py` | 81 | Service 的统一注册：`register_app_services(page)` 由 `main.py` 在页面首次发出**之前**调用（时机是关键，见约定 10），页面里用 `ensure_service(page, 类型)` 取 |
| `src/tools/version_check.py` | 95 | 查新版本：`APP_VERSION` 常量 + `latest_version()`（GitHub `releases/latest`，没发过 Release 就退到 `tags`；标准库 `urllib`，**阻塞**，调用方扔 `asyncio.to_thread`）、`is_newer()`、`parse_version()`（`v` 前缀、位数不同都能比）。**坑**：`User-Agent` 必须是 ASCII，拿中文应用名去拼会在发请求前就抛 `UnicodeEncodeError` |
| `src/tools/categories.py` | 62 | 三个类别及其颜色（红 / 黄 / 绿）、星标控件 |
| `src/tools/todo_timeline.py` | 535 | 待办行 / 时间轴（首页一条条搭、日历弹窗整列搭都走它；点线随卡片拉伸、点本身仍是圆点；**轴两端不补点** —— 首行上、末行下都不画小圆点，`first` / `last` 由调用方传；**`show_timeline=False` 只剩下卡片**（待办行、整天的一列都支持这一档），当天弹窗用的就是它） |
| `src/tools/todo_form.py` | 278 | 新增 / 编辑待办弹窗（分类胶囊 + 内容 + 日期 + 起止时间一格 + 周期） |
| `src/tools/swipe_delete.py` | 124 | 左滑露出操作按钮的行容器 |
| `src/tools/swipe_back.py` | 102 | 整页左滑返回上一页的壳（二级 / 三级页用；只绑横滑，竖滑和屏幕两侧的系统手势区都让出去） |
| `src/tools/popup_select.py` | 219 | 统一的下拉选择器（待办/倒数日的日期、类别、循环、通知渠道都用它） |
| `src/tools/segmented.py` | 191 | 横向胶囊分段开关（「数据」页 年/月/周、待办弹窗的三个分类；可一项一色；`compact=True` 是更小的一档（格高 16、字号 8、左右内边距 5），数据页那张小长方卡用它和标题并排放在一行） |
| `src/tools/pickers.py` | 129 | 系统日期 / 时间选择器封装（含 UTC 时区修正、可选标题） |
| `src/tools/countdown_card.py` | 356 | 倒数日卡片（三档状态色、中段钉高所以张张等高、过期不循环的自动收起；`expired=True` 把日期行换成「已过期 N 天」，整张卡连「天前」一并置灰 —— 上段那枚图也从 `icons/calendar.png` 压成 `EXPIRED_ICON_COLOR` 那档灰，`color` + `color_blend_mode=SRC_IN` 只留形状、颜色换掉） |
| `src/tools/countdown_form.py` | 188 | 新增 / 编辑倒数日弹窗（字段自上而下：**输入框 → 日期 → 周期**；输入框是**单行**，和 新增待办 那个一样；**弹窗里不摆颜色** —— 新增时从 `CARD_COLORS` 随机取一个当卡片底色，编辑时沿用原色） |
| `src/tools/line_chart.py` | 514 | 待办趋势折线图（`flet-charts` 多系列 LineChart + 毛玻璃自绘浮框 + 自绘圆点：平时实心、点住空心放大）：`interactive=False` 关掉自带触摸（它还会画竖直指示线、放大圆点），手势由外面 `ft.GestureDetector` 接（点一下停在那一格、横向拖动看别的点、桌面悬停跟随）；点住那一列的几颗圆点会被一条浅灰细虚线串起来 |
| `src/tools/pie_chart.py` | 88 | 分类占比饼图（`flet-charts` PieChart + 悬停凸出；半径按画布大小等比缩（`pie_scale`），圆孔透明） |
| `src/tools/half_ring.py` | 134 | 半圆完成率环（数据页用）：`PieChart` 只画上半圈（九点钟起笔、扫 180°，下半圈不画）；弧是 32 段从浅到深的实色刻度（不用 `gradient`，fl_chart 按扇区包围盒算渐变会歪），进度由一个圆点表示（直径 = 环厚，这样它停在弧两端正好压着画布两边、不会探出去）—— 圆点沿弧走到完成率那格、颜色取那格的深浅，`set_value()` 一步步喂（客户端不插值，`animation=0`）；外面套「高 = 半径」的 Stack，圆心那块交给调用方放内容，画布边长与环厚由调用方给 |
| `src/tools/lunar.py` | 124 | 农历换算（1900–2099 查表，无外部依赖） |
| `src/tools/notifications.py` | 42 | 通知的总开关（`ENABLED_SETTING` = `notify_enabled`，`ENABLED_ON` / `ENABLED_OFF`）、渠道清单、每档的图标（`CHANNEL_ICONS` / `channel_icon()`）与摘要文案（`summary(channel, url)` —— 只说渠道和地址，不看总开关；目前只有配置，没有发送实现） |
| `src/tools/contacts.py` | 24 | 联系方式：值存 `settings`（`contact_email` / `contact_wechat`），`items()` 读出来给页面显示；默认值由 `app_settings` 统一补 |
| `src/tools/app_settings.py` | 33 | **`settings` 表里该有哪些行**的清单（通知提醒开关 / 通知渠道 / 通知地址 / 云端开关 / 邮箱 / 微信）+ `ensure_defaults()`：启动时把表里还没有的键补上默认值（按「键存不存在」判断，不覆盖用户清空过的值） |
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
2. **下拉一律用 `tools/popup_select.py`**，不要用 `ft.Dropdown`：Dropdown 的触发器是 Material TextField，`InputDecorator` 会在弹层之上再画一遍自己的框，把贴在它下面的面板盖住一半。现在用 `PopupMenuButton + menu_position=UNDER`。触发器的箭头跟着面板走：展开时 `EXPAND_LESS`（朝上）、点外面关掉或选了一项都回到 `EXPAND_MORE`（朝下）。例外是「数据」页的 年/月/周 和新增待办弹窗的分类：选项直接摊在卡片标题行 / 弹窗行里，用 `tools/segmented.py` 的横向胶囊开关，点一下就切，不必先点开面板。
3. **弹窗**统一 `shape=RoundedRectangleBorder(radius=DIALOG_RADIUS)` + `bgcolor=DIALOG_SURFACE` + `elevation=0`。
4. **键盘处理**：弹窗打开后调一次 `track_keyboard(page, dialog)`，它会挂在 `page.on_media_change` 上，按 `view_insets.bottom` 把弹窗挪到键盘上方 / 键盘落下时挪回正中（返回的函数在 `close` 里调一下，把 media 处理还原）。**别改用 `on_focus` / `on_blur` 去挪弹窗**：焦点事件比键盘动画早到一步，按它挪会先往屏幕底下一沉、键盘真的升起时再弹回来；而且点外面 / 按返回关掉时拿不到 blur，弹窗会留在底部。`on_focus` / `on_blur` 只管 `set_menu_visible`。
5. **列表底部留白**用 `BOTTOM_MENU_INSET`，否则最后一行会被浮动菜单栏压住。
6. 页面内容滚动一律 `scroll=ft.ScrollMode.HIDDEN` 隐藏滚动条。
7. **折线图的浮框是自绘的，触摸也自己接**（`tools/line_chart.py`）：fl_chart 的浮框是一个系列一行、每行只能一种颜色（`text_spans` 在 flet-charts 1.0.1 里传不到 Dart 侧，一用整个浮框都画不出来），做不出「灰色日期 + 彩点 + 黑色数值」。所以干脆**把控件自带的触摸整个关掉**（`LineChart(interactive=False)`）—— 自带那套除了浮框，还会在点到的位置画**一条竖直指示线**、把那颗点放大，这两样都不要；手势改由外面一层 `ft.GestureDetector` 自己接，浮框是挂在同一个 `ft.Stack` 上的自绘 `ft.Container`，位置按下标算（`spot_pixel` / `tip_placement`）。**线上的圆点也就得自己画**（`build_dots`）：`interactive=False` 时控件那颗点整个不出现，所以每条线的每个点都由我们摆一颗圆点（位置用同一个 `spot_pixel`）—— **没点的时候是实心圆**（填满自己的分类色 `DOT_DIAMETER = 8`、不画圈线；一眼看出这条线是哪个等级，也压得住底下的网格线），**点住那一格时换成空心、放大到 11、圈一圈 2px 的同色线**（`ACTIVE_DOT_DIAMETER` / `ACTIVE_DOT_STROKE_WIDTH`，圈里空着、露出来的是页面渐变）—— 两种样子都在 `style_dot` 里换（换的时候以自己中心重摆，位置不跳），和浮框一起指明「现在看的是哪一格」。点与点之间连的仍是折线本身（**实线**，`LINE_WIDTH = 2.5`；**没有**把折线画成虚线）；**点住那一列**另有一条**浅灰细虚线**（`build_guide`：`GUIDE_COLOR = #94A3B8`、1px 宽、3px 一段 + 3px 空 —— Flet 没有虚线边框，所以码一串 1×3 的小方块拼出来）把这一列的几颗圆点串起来，**从最上面那颗的下沿连到最下面那颗的上沿**（两头都让开圆点，别从圆里穿过去）；这一列的点全挤在一格里（都没待办、全在 0 线上）时没有地方画，不画。点多过 `POINT_LIMIT = 14` 的那一档（一个月 28-31 天）不画点，三十来个空心圆会连成一条链子。**手势用「横向拖动」而不是 pan**：竖直方向留给页面滚（pan 会和外面 `ListView` 抢手势）。行为：**点一下** → 浮框停在最近的那个点上（`on_tap_up`，再点同一点才收）；**横向拖动** → 沿着曲线看别的点，浮框一路跟过去（`on_horizontal_drag_update`），松手仍停在那儿；**悬停**（桌面鼠标）→ 跟着鼠标走、移开就收（`on_hover` / `on_exit`），但**点住的那一点不会被悬停带走**。所以触屏抬手之后**不会再收到 `pointerExit`**（自带触摸都关了），「点一下只闪一下」的问题从根上没有了；同一个点重复来不重画（`show_tip` 里 index 没变就直接返回）也不会闪。浮框是毛玻璃：半透明灰白底（`#CCF1F5F9`，`#AARRGGBB`）+ `blur=ft.Blur(12, 12, ft.BlurTileMode.CLAMP)`，与「+」按钮、底部菜单栏同一套写法。
8. **页面选择状态存在 `pages/navigation.py`**：切页时页面控件是重建的（待办数据要现从 db 读），但「在看哪个月 / 选了哪一档」这类选择必须留住，所以 `build_navigation` 里有一份按页面名索引的 `state_store`，由 `page_state(name)` 按名字取（没有就现建一个空的）；页面把它当自己的草稿本 —— 日历页存 `month` / `day`，数据页存三张卡各自的 年/月/周，只有热重载重跑 `main()` 才会回到初始值。
9. **日历弹窗的高度是「先估后量」**：正文的真高度由 `open_day_dialog` 里那层探针（`on_size_change`）量出来，量一次得等一帧（客户端是 post-frame 回调），所以第一帧先用 `estimate_day_height()` 把 `body.height` / `scroll` 定上。估算**估高不估矮**：估高了下一帧就收回，估矮了弹窗会先按全部内容撑高一下再弹回来 —— 就是「点日期先闪一下全部数据」的样子。
10. **`ft.Service`（`Clipboard`、`FilePicker` 这些）统一走 `tools/services.py`，而且必须由 `main.py` 的 `register_app_services(page)` 在**启动时**注册**（页面里只用 `ensure_service(page, 类型)` 取）。三个坑：① **`page.services.append(...)` 不算注册** —— `page.services` 拿到的是根 `View` 上那个**普通 list**（连 `register_service` 都没有），append 只是往清单里塞个对象，客户端什么都收不到。② **注册必须赶在页面首次发给客户端之前**：真正会把服务送出去的是注册表的 `register_service()`，可注册表是 `Page` 的一个字段、并不挂在控件树上，它的 `parent` 恒为 `None`，那段 `__internal_update()` 直接返回 —— 新增的服务只能等「随页面首次发出」。设置页这类二级页构建时页面早发过了，那时再注册客户端**永远**收不到，之后调用它的方法就是干等 10 秒然后抛 `TimeoutException: Timeout waiting for invoke method listener for Clipboard(xxx).set`。③ 改用 `ft.CopyToClipboard` 这类客户端动作**绕不过这一点**：它内部的 `shared_service(Clipboard)` 走的是同一个注册路径（它的好处只在 iOS/Safari 的手势时效上，跟注册无关）。
11. **`assets`（`src/assets`）：App 图标与启动图摆在**根目录**，其余按用途分两个文件夹**：
    ```
    src/assets/
    ├── icon.png              # App 图标 —— 只能在这儿，别挪
    ├── splash_android.png    # 启动图 —— 同上
    ├── icons/                # 三方图标（外面下载来的图：add / data / calendar / settings 四张都在这儿）
    └── images/               # App 内用到的图片
    ```
    - **`icon.png` / `splash_android.png` 不能挪进子文件夹**：`flet build` 只在 assets **根目录**找它们，而且没有参数可以改这个位置（`flet_cli/commands/build_base.py` 里就是 `glob("icon.*")` / `glob("splash.*")`，非递归；查了一圈也没有 `--icon` 这类选项，那个参数只属于 `flet pack`）。挪进去的后果是**悄无声息地回退成 Flet 模板自带的图标 / 启动图** —— 构建不报错，装到手机上才发现图标不对。它还认带平台后缀的近亲：`icon_<平台>.png`（`icon_android.png`、`icon_ios.png`…）优先于通用的 `icon.png`，启动图同理（`splash_<平台>.png` → `splash.png` → 最后退回用 App 图标当启动图）。
    - **图片在代码里的引用路径 = 相对 assets 目录**：`ft.Image(src="icons/settings.png")` —— **子目录照写**，但不带 `assets/` 前缀、也不带前导斜杠。Flet 把这个 assets 目录**挂在 App 的根路径上**，所以文件是 `/icons/settings.png`；写成 `assets/icons/settings.png` **会 404**（实测：`/icons/settings.png` → 200、`/assets/icons/settings.png` → 404，后者命中的是 Flet 自己那套 web 资源）。文件名里的空格不用管，客户端会把 URL 转义成 `%20`；中文名同理。
    - **目录要自己指到**：`flet run` 会自动认脚本目录下的 `assets`（`--assets` 默认值，导成 `FLET_ASSETS_DIR` 给 App），但 `ft.run()` 在没给 `assets_dir` 时是按**当前工作目录**拼默认的 `assets` —— 从项目根跑 `python src/main.py` 就拼到不存在的 `DailyList/assets`，图全白。所以 `main.py` 里写死 `ASSETS_DIR = Path(__file__).parent / "assets"` 传给 `ft.run`（`flet run` 的 `FLET_ASSETS_DIR` 会覆盖它，两边不冲突）。**想验证某张图到底通没通**：起一个 web 视图数一下状态码最快（`flet_web.fastapi.serve_fastapi_web_app` + `urllib`），比在真机上看图猜省事。
    - **路径常量集中在 `tools/layout.py`**：`ADD_ICON_SRC`（「+」按钮）、`DATA_ICON_SRC`（待办页右上角）、`CALENDAR_ICON_SRC`（倒数日卡片 + 待办页空态 + 日历弹窗空态，**三处共用，别在各页面各写一遍字符串**）、`SETTINGS_ICON_SRC`（日历页右上角）、`CHECK_ICON_SRC`（月历里「当天全做完」那枚对勾）。写 `ft.Image(src=..., width=..., height=..., fit=ft.BoxFit.CONTAIN)`，尺寸各页自己定（22 / 20 / 18 / 14 不等）。**底部菜单那一排是例外**：三个 Tab 都用内置图标（要「实心 / 空心」两态，图只有一张）。
    - **改引用时记得 `src` 里必须有这个文件** —— 路径写错**不报错**，只是那一格**什么都不画**（`ft.Image` 加载失败是静默的，可以给它 `error_content=` 兜一个占位）。`images/` 还空着（放一个 `.gitkeep`，否则 git 不会保留空目录）。
12. **页面的上下层关系只认 `navigation.py` 的 `nav_stack` + `page.views`**（`tools/swipe_back.py` 把左滑接到它上面）：进一层时把「上一层怎么画」压进 `nav_stack`（`render_data` / `render_preferences` 那类只重画、不动栈的函数），`go_back()` 只弹一层 —— 同时弹掉 `page.views` 顶上那层真 View。所以**别在页面里自己写 `show_page(0)` 当返回**，也别在栈里压一个会再压栈的 `show_xxx`；另外别把子页塞回 `content.content`（那样真机的返回就又没有层可弹、直接退出 App 了）。层数多深都按这个来。

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
- **通知只有配置，没有发送**：`tools/notifications.py` 只存「通知提醒」总开关、渠道名和地址，**没有任何真正发推送的逻辑** —— 所以那个开关现在只改自己那行小字、弹一句提示，将来接上发送时才是真开关。
- **云端数据是占位**：开关**状态会落库**（`cloud_enabled`，进设置页读回来的就是上次那档），但**不发任何请求**（代码注释里写明「先只做样子」）—— 它只负责弹提示、换小字说明，不做同步。
- **导入是「替换」不是「合并」**：导入会把待办与倒数日**整表**换成文件里的内容（有二次确认），想往现有数据里追加暂时做不到；文件也必须是本 App 导出的 JSON（认 `format` 标记），只支持 JSON 这一种格式。
- **两个 `dailylist.db`，查设置时别查错**：`flet run` 会给应用设 `FLET_APP_STORAGE_DATA`，于是 `db.py` 用的是 **`.flet/storage/data/dailylist.db`** —— 应用真正在读写的那个（六项设置、todos、countdowns 都在里面）；项目根那份 **`dailylist.db` 是过时的活数据文件**（只有 `todos`(204 行) / `settings`(2 行)，既没有 `countdowns` 表，`todos` 也缺 `due_time` / `end_time` —— 早于「倒数日 / 时间」功能），它跟着仓库走、改一次就是一次文件改动，但应用已经不写它了。
- **设置项集中在 `settings` 表**：通知提醒开关 / 通知渠道 / 通知地址 / 云端开关 / 邮箱 / 微信六种，键与默认值汇总在 `tools/app_settings.py`，启动时 `ensure_defaults()` 把缺的补上 —— 所以第一次跑完这几行就该都在表里。
- **多实例同时写库**：应用的 DB 路径固定在项目根，同时开多个实例（或一边跑 App 一边跑测试脚本）会互相覆盖数据，调试时注意先关掉旧实例。
- **一级页按返回会退出 App**：二级 / 三级页现在是真 View，系统返回弹的是它们；回到一级页（`page.views` 只剩一层）之后按返回就没有可弹的层了，客户端会结束 Activity、回到 Flet 首页 —— 这是系统返回的正常行为，不是 bug。想在首页也拦住返回，得自己接管客户端的返回事件，Flet 目前没给这层口子。
