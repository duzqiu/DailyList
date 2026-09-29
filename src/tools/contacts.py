"""联系方式：存在 `settings` 表里，通用设置那张卡片里一条一行、点一下复制走。

值放表里而不是写死在代码里有两个好处：导出的那份 JSON 会连 `settings` 一起带走，
换台机器恢复备份时联系方式跟着回来；以后要做「改联系方式」也只是加一个输入框的事。
"""

from tools import db

EMAIL_SETTING = "contact_email"
WECHAT_SETTING = "contact_wechat"

# 默认值：(显示的名称, `settings` 里的键, 默认值)
DEFAULTS = (
    ("邮箱", EMAIL_SETTING, "duzqiu@outlook.com"),
    ("微信", WECHAT_SETTING, "test001"),
)


def items() -> tuple[tuple[str, str], ...]:
    """要显示的联系方式：`(名称, 值)`；值从 `settings` 读，表里没有就退回默认值。"""
    return tuple(
        (label, db.get_setting(name, default))
        for label, name, default in DEFAULTS
    )
