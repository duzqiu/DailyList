"""**临时**：这些设置项先放**内存**里，不落库、也不写磁盘。

覆盖范围：云端开关、通知总开关 / 渠道 / 地址、联系方式与**背景图路径**。本地 SQLite
那一层已经整个删掉了；还留在磁盘上的只有**登录令牌**，它现在由 api/session.py 存进
**客户端存储**（Flet 的 SharedPreferences）。

⚠️ 「我的」页资料（昵称 / 简介 / 性别 / 生日 / 地区 / 头像）**不在这里**：那部分改走
后端 `GET|PUT /member/profile`（见 api/member_profile.py、tools/my_profile.py），
本地不再存副本。

接口刻意保持 `get_setting` / `set_setting` / `list_settings` 这套名字：将来接后端返回、或
重新落盘时，把调用点里的模块名换掉就行，参数和返回值都不用动。

值是**示例数据**：界面照旧能读能改（改动只留在内存里），重启后回到下面这一份。

⚠️ 临时方案，见 README「待处理问题」。键的定义分散在各自的模块里（通知 →
tools/notifications.py，联系方式 → tools/contacts.py，「我的」页资料 →
tools/my_profile.py），这里按字面量列出来是为了不产生 import 环。
"""

from tools import notifications

# 云端数据开关的键。（原来在 tools/app_settings.py，那个模块已随这次改动删掉。）
CLOUD_SETTING = "cloud_enabled"
CLOUD_OFF = "0"
CLOUD_ON = "1"

# 开关 / 单选的通用取值（这张表里所有东西都是字符串）。
SWITCH_OFF = "0"
SWITCH_ON = "1"

# 「是否公开展示」那几枚开关的键 —— 用在**编辑性别页**（pages/edit_gender.py）与
# **编辑生日页**（pages/edit_birthday.py）上。
# ⚠️ 后端**没有**这几个字段（`MemberProfileUpdate` 只有昵称 / 头像 / 背景 / 性别 /
# 生日 / 电话 / 简介 / 地区），所以和云端那个开关一个做法：拨一下先写内存，
# 当次运行内记得住、重启回到默认，见下面 `_VALUES` 里那三行。
SHOW_GENDER_SETTING = "profile_show_gender"
SHOW_BIRTHDAY_SETTING = "profile_show_birthday"
# 「展示年龄 / 展示星座」**二选一**（那两张图里只有一项带勾）。
BIRTHDAY_DISPLAY_SETTING = "profile_birthday_display"
BIRTHDAY_AGE = "age"
BIRTHDAY_ZODIAC = "zodiac"

# 内存表：键 → 值。值一律是字符串，和原来 `settings` 表那两列（name / value）一致，
# 这样导出的 JSON 与旧备份长得一样。
_VALUES: dict[str, str] = {
    CLOUD_SETTING: CLOUD_OFF,
    notifications.ENABLED_SETTING: notifications.ENABLED_OFF,
    notifications.CHANNEL_SETTING: notifications.DEFAULT_CHANNEL,
    # 地址给一条示例：填上之后设置页那行摘要才看得出「配好了」的样子。
    notifications.URL_SETTING: "https://api.day.app/xxxxxxxx",
    # 联系方式两条（键见 tools/contacts.py）。
    "contact_email": "duzqiu@outlook.com",
    "contact_wechat": "test001",
    # 「是否公开展示」三枚开关的默认值，照那三张图：生日标签**开**着、性别标签**关**着、
    # 生日展示选「年龄」。
    SHOW_BIRTHDAY_SETTING: SWITCH_ON,
    SHOW_GENDER_SETTING: SWITCH_OFF,
    BIRTHDAY_DISPLAY_SETTING: BIRTHDAY_AGE,
    # ⚠️ 「我的」页背景图**不在这里**：它和头像一样存后端（按会员 ID 分目录），
    # 见 api/member_profile.py 的 `upload_background` 与 tools/my_profile.py。
}


def get_setting(name: str, default: str = "") -> str:
    """取一项；没有就返回 `default`。"""
    return _VALUES.get(name, default)


def set_setting(name: str, value: str) -> None:
    """改一项 —— **只改内存**，重启就回到上面那份示例数据。"""
    _VALUES[name] = "" if value is None else str(value)


def list_settings() -> dict[str, str]:
    """当前全部设置项的副本（导出 JSON 用）。"""
    return dict(_VALUES)
