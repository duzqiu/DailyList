"""联系方式：通用设置那张卡片里一条一行、点一下复制走。

值取自**内存里的 mock 数据**（`tools/mock_settings.py`，目前不落库）而不是写死在代码里，
有两个好处：导出的那份 JSON 会把它一起带走（见 tools/data_export.py），换台机器恢复备份
时联系方式跟着回来；以后要做「改联系方式」也只是加一个输入框的事。
"""

from tools import mock_settings

EMAIL_SETTING = "contact_email"
WECHAT_SETTING = "contact_wechat"

# 默认值：(显示的名称, 键, 兜底值)
DEFAULTS = (
    ("邮箱", EMAIL_SETTING, "duzqiu@outlook.com"),
    ("微信", WECHAT_SETTING, "test001"),
)


def items() -> tuple[tuple[str, str], ...]:
    """要显示的联系方式：`(名称, 值)`；取不到就退回 `DEFAULTS` 里的兜底值。"""
    return tuple(
        (label, mock_settings.get_setting(name, default))
        for label, name, default in DEFAULTS
    )
