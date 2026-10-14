# 每日清单（DailyList）

仿小红书的待办 / 倒数日 App，基于 Flet（Flutter + Python）一套代码跑 iOS / Android / 桌面 / Web；界面全中文、浅色配色（白 - 天蓝 - 靛蓝）。涵盖首页发现流、倒数日、消息、我的（含编辑资料与换背景图）、设置与登录 / 注册 / 忘记密码等页面，二级页走 `page.views` 真 View，带横向推拉与交叉淡入淡出过渡。

- 依赖：`flet>=1.0.1`，Python >= 3.10
- 运行：`uv run flet run`（桌面）/ `uv run flet run --web`（浏览器）/ `python src/main.py`
- 打包：`flet build apk|ipa|windows`，iOS 用 `scripts/build_ios.sh`

> **维护约定**：每次修改代码后，通读 README 全部内容，凡是对应功能的删除或修改，都要同步更新 README 的说明。

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
│  │  ├─ feed.py              首页发现流（关注 / 发现 / 上海 + 二级标签 + 瀑布流）
│  │  ├─ countdown.py         倒数日页（卡片从 countdown_store 读）
│  │  ├─ messages.py          消息页（快捷入口 + 列表 + 通知条）
│  │  ├─ my.py                「我的」页（账号卡片 + 内容板）
│  │  ├─ edit_profile.py      编辑资料页（本地资料见 my_profile.py）
│  │  ├─ background.py        换背景图页（预览 + 选图）
│  │  ├─ preferences.py       设置页（账号 / 通知 / 数据 / 通用）
│  │  ├─ login.py             登录页
│  │  ├─ register.py          注册页
│  │  └─ forgot_password.py   忘记密码页
│  ├─ tools/                  公共控件与工具
│  │  ├─ db.py                建表迁移与按设备隔离；待办 CRUD、循环展开
│  │  ├─ device.py            设备主键（各平台取唯一标识）
│  │  ├─ app_settings.py      settings 表键定义与启动补默认值
│  │  ├─ data_export.py       导出 JSON（整表替换）
│  │  ├─ data_import.py       导入 JSON（整表替换）
│  │  ├─ layout.py            全局配色 / 尺寸常量、assets 路径、弹窗键盘定位、is_attached / safe_update
│  │  ├─ auth_form.py         登录三页共用表单骨架（玻璃卡片 + 字段 + 主按钮 + 链接）
│  │  ├─ todo_form.py         新增 / 编辑待办弹窗
│  │  ├─ countdown_form.py    新增 / 编辑倒数日弹窗
│  │  ├─ my_background.py     背景图存取
│  │  ├─ my_profile.py        编辑资料本地资料（昵称 / 号 / 简介 / 性别 / 生日 / 头像）
│  │  ├─ countdown_card.py    倒数日卡片（三档状态色、过期置灰）
│  │  ├─ countdown_store.py   倒数日内存仓库（同步读 + 增删改 + 按 id 取色）
│  │  ├─ settings_card.py     设置卡片公共零件 + 账号卡片（设置页与「我的」页共用）
│  │  ├─ segmented.py         横胶囊开关
│  │  ├─ popup_select.py      统一下拉选择器
│  │  ├─ pickers.py           系统日期时间选择器
│  │  ├─ swipe_delete.py      左滑露出行内操作
│  │  ├─ swipe_back.py        整页左滑返回
│  │  ├─ toast.py             居中 toast
│  │  ├─ services.py          ft.Service（剪贴板 / 文件选择器）统一注册
│  │  ├─ lunar.py             农历换算（1900–2099 查表）
│  │  ├─ notifications.py     通知渠道配置
│  │  ├─ contacts.py          联系方式
│  │  ├─ version_check.py     检查新版本
│  │  └─ categories.py        待办分类与颜色
│  └─ assets/                 图标与背景图（根目录须有 icon.png / splash_android.png）
├─ scripts/
│  └─ build_ios.sh            一键打包签名好的 iOS .ipa
└─ tests/                     Flet 测试（当前已过期）
```
