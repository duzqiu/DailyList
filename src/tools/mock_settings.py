"""**临时**：这些设置项先放**内存**里，不落库、也不写磁盘。

覆盖范围：云端开关、通知总开关 / 渠道 / 地址、联系方式、「我的」页资料（昵称 / 号 / 简介 /
性别 / 生日 / 头像）与**背景图路径**。本地 SQLite 那一层已经整个删掉了；还留在磁盘上的只有
**登录令牌**，它现在由 api/session.py 存进**客户端存储**（Flet 的 SharedPreferences）。

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
    # 「我的」页背景图（键见 widgets/my_background.py）：默认空串 = 不铺图，那一页用
    # 浅蓝渐变兜底（见 README「待处理问题」里那条）。
    "my_background": "",
    # 「我的」页资料（键见 tools/my_profile.py）。
    "my_name": "每日清单",
    "my_xhs_id": "dailylist_001",
    "my_intro": "记下每一个重要的日子",
    "my_gender": "保密",
    "my_birthday": "2000-01-01",
    "my_avatar": "",
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
