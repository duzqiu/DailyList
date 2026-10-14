# 每日清单（DailyList）

仿小红书风格的「倒数日」App，基于 Flet（Flutter + Python）一套代码跑 iOS / Android / 桌面 / Web；界面全中文、浅色配色（白 - 天蓝 - 靛蓝）。涵盖首页发现流（当前是本地 mock 数据）、倒数日（接后端 `/member/countdowns`，按登录会员隔离）、消息、我的（含编辑资料与换背景图）、设置与登录 / 注册 / 忘记密码等页面，二级页走 `page.views` 真 View，带横向推拉与交叉淡入淡出过渡。

> **待办（todos）整块已删**：数据表、CRUD、循环展开、新增 / 编辑弹窗、分类色、底栏「新增待办」入口全没了；老库里遗留的 `todos` 表会在启动时由 `db.init_db()` 删掉。底栏中间那颗红「+」和「我的」页的「去发布」胶囊照旧留着，但点了只给一句提示。

- 依赖：`flet>=1.0.1`，Python >= 3.10
- 运行：`uv run flet run`（桌面）/ `uv run flet run --web`（浏览器）/ `python src/main.py`
- 打包：`flet build apk|ipa|windows`，iOS 用 `scripts/build_ios.sh`

## 开发约定

1. **改完代码就通读 README**：凡是对应功能的删除或修改，都要同步更新本文档的说明。
2. **与页面有关的都放 `src/widgets/`**：共享控件 / 卡片 / 弹窗（表单骨架、设置卡片、
   倒数日卡片与弹窗、下拉选择器、系统选择器、左滑行、左滑返回、toast）、页面配色与尺寸
   常量（`layout.py`）、页面级 Service 的注册（`services.py`）、「我的」页背景图
   （`my_background.py`）都在这里；只服务单个页面的也放这儿，别塞进页面。
   > 现状：原先散在 `tools/` 里的这一批**已经全部迁过来了**。页面与组件互相引用走
   > `widgets.*`；真正跟页面无关的东西（数据、设备、农历、版本检查……）仍从 `tools.*` 取。
3. **与页面无关的工具类放 `src/tools/`**：数据（`db` / `countdown_store` / `my_profile`
   / `mock_settings` / `contacts` / `cycles`）、设备、文件落点、导入导出、农历、通知、版本
   检查这些。判别标准：**和页面相关的一律进 `widgets/`**，`tools/` 只留跟界面无关的。
4. **图片资源放 `src/assets/`**，按用途分两个目录：`images/`（背景图、照片）与
   `icons/`（图标）。assets 根目录另放打包用的 `icon.png` / `splash_android.png`。
5. **引用 assets 的路径写「相对 assets 目录」的那一段**，不带 `assets/` 前缀、也不带
   前导斜杠 —— Flet 把 assets 目录挂在 App 的根路径下，写成 `assets/icons/xx.png`
   反而 404。路径常量集中在 `widgets/layout.py`。
6. **全局配色 / 尺寸常量集中放 `widgets/layout.py`**，别在各页面里手写十六进制。

## 文件夹结构与文件说明

```
DailyList/
├─ src/
│  ├─ main.py                 入口：建库 → 补默认设置 → 取设备 ID → 注册 Service → 装配导航
│  ├─ api/                    后端接口层
│  │  ├─ client.py            请求底座（基址 + urllib，浏览器 UA，错误转 ApiError）
│  │  ├─ session.py           登录态令牌存取（落库 settings）
│  │  ├─ member_auth.py       认证接口（验证码 / 注册 / 登录 / 当前会员 / 登出）
│  │  └─ member_countdowns.py 倒数日接口（增删改查 + 周期映射）
│  ├─ pages/                  各页面
│  │  ├─ navigation.py        底栏菜单、Tab 切换、二级页跳转与页面栈、主题
│  │  ├─ feed.py              首页发现流（关注 / 发现 / 上海 + 二级标签 + 瀑布流，本地 mock）
│  │  ├─ countdown.py         倒数日页（卡片从 countdown_store 读）
│  │  ├─ messages.py          消息页（快捷入口 + 列表 + 通知条）
│  │  ├─ my.py                「我的」页（账号卡片 + 内容板）
│  │  ├─ edit_profile.py      编辑资料页（本地资料见 my_profile.py）
│  │  ├─ background.py        换背景图页（预览 + 选图）
│  │  ├─ preferences.py       设置页（通知 / 数据 / 通用）
│  │  ├─ login.py             登录页
│  │  ├─ register.py          注册页
│  │  └─ forgot_password.py   忘记密码页
│  ├─ widgets/                **与页面有关**的都在这儿（见「开发约定」2、3）
│  │  ├─ layout.py            全局配色 / 尺寸常量、assets 路径、二级页顶栏、弹窗键盘定位、is_attached / safe_update
│  │  ├─ auth_form.py         登录 / 注册 / 忘记密码三页共用的表单骨架（玻璃卡片 + 字段 + 主按钮 + 链接）
│  │  ├─ settings_card.py     设置卡片零件 + 账号卡片（设置页与「我的」页共用）
│  │  ├─ countdown_card.py    倒数日卡片（三档状态色、过期置灰）
│  │  ├─ countdown_form.py    新增 / 编辑倒数日弹窗
│  │  ├─ popup_select.py      统一下拉选择器
│  │  ├─ pickers.py           系统日期 / 数值选择器
│  │  ├─ swipe_delete.py      左滑露出行内操作
│  │  ├─ swipe_back.py        整页左滑返回
│  │  ├─ my_background.py     「我的」页背景图（存路径 + 两个铺图的小工具函数）
│  │  ├─ services.py          ft.Service（剪贴板 / 文件选择器）注册与取用
│  │  └─ toast.py             居中 toast
│  ├─ tools/                  **与页面无关**的工具类（见「开发约定」3）
│  │  ├─ db.py                本地 SQLite：**只装登录令牌**；启动时清掉老表（todos / countdowns）与过期设置项
│  │  ├─ mock_settings.py     **临时**：设置项的内存 mock（云端开关 / 通知 / 联系方式 / 我的资料 / 背景图）
│  │  ├─ countdown_store.py   倒数日内存仓库（数据来自后端；同步读 + 增删改 + 按 id 取色）
│  │  ├─ cycles.py            倒数日周期：有哪几档、下一次是哪天（纯计算，原先在 db.py 里）
│  │  ├─ files.py             App 数据目录 + 「把选中的文件复制进来」（换背景图 / 存头像共用）
│  │  ├─ device.py            设备主键（各平台取唯一标识；本地数据不再按设备隔离，暂无调用方）
│  │  ├─ data_export.py       导出 JSON（倒数日来自后端缓存 + 设置来自内存 mock）
│  │  ├─ data_import.py       导入 JSON（设置写内存 mock；倒数日那段暂不落地）
│  │  ├─ my_profile.py        编辑资料本地资料（昵称 / 号 / 简介 / 性别 / 生日 / 头像；存内存 mock）
│  │  ├─ lunar.py             农历换算（1900–2099 查表）
│  │  ├─ notifications.py     通知渠道配置（渠道清单、图标、一句话摘要）
│  │  ├─ contacts.py          联系方式（值取自内存 mock）
│  │  └─ version_check.py     检查新版本
│  └─ assets/                 资源目录（见「开发约定」4、5）
│     ├─ icons/               图标（add.png / calendar.png / person.png / settings.png）
│     ├─ images/              背景图（auth_background.jpg）
│     ├─ icon.png             打包用 App 图标
│     └─ splash_android.png   打包用 Android 开屏图
├─ scripts/
│  └─ build_ios.sh            一键打包签名好的 iOS .ipa
└─ tests/                     （暂无测试；旧的 Flet 测试已随待办页一起删除）
```

## 待处理问题

_先这么办、以后要改的事记在这儿：写明现状 + 打算怎么改（最新在最上面）。_

- **本地数据一律不落库，只有登录令牌还写 SQLite**。原先存在本地 `settings` 表里的那些
  （云端开关、通知总开关 / 渠道 / 地址、联系方式、「我的」页资料与背景图路径）现在全部走
  `tools/mock_settings.py` 的内存表 —— 接口与 `tools/db.py` 那三个函数同名同形，示例值写在
  该文件里；界面照旧能读能改，**改完当次运行内有效、重启回到示例值**。连带几处：
  - 「清除缓存」清的是 `countdown_store` 的内存缓存（先前清的本地表早没人读了，还在谎报条数）；
  - **导入 JSON 只把 `settings` 写进内存 mock，`countdowns` 那段不落地**（页面数据在后端），
    提示语如实写「倒数日暂未落地」；
  - 老库里残留的 `countdowns` / `todos` 表和过期的设置项**由 `init_db()` 在启动时清掉**
    （见 `tools/db.py` 的 `LEGACY_TABLES` / `KEPT_SETTINGS`，后者是白名单：只有登录令牌两
    个键留下）；
  - 待定方向：这些设置接后端接口，或恢复落库；届时把对应的键加回 `KEPT_SETTINGS`，否则下次
    启动就会被清掉。
- **「我的」页没设背景图时那层浅蓝底是临时方案**。这块区域原本只按「压在背景图上」一种形态设计（文字 / 图标全白），没设图时白字落在页面的白底上，整块等于看不见（`background_decoration()` 返回 `None` 的那条分支）。现在**临时**给它垫了一层浅蓝渐变（`pages/my.py` 的 `NO_COVER_GRADIENT_COLORS`，取 `SKY_BLUE → DATE_SELECTED_BG` 两个已有色）并把文字换成深色 —— 能看清了，但这套配色是凑出来的，不是设计稿。**先维持现状**，待定方向：给「我的」页配一张默认封面图（放进 `src/assets/images/`，让 `background_decoration()` 无图时返回它），或者另出一版浅色版式。
