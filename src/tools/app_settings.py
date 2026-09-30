"""`settings` 表里都记着哪些设置项 —— 一张清单，启动时按它把缺的补上。

各项的键分散在各自的模块里（通知渠道 → `tools/notifications.py`，联系方式 →
`tools/contacts.py`，云端开关 → 这里），这里做的是**汇总**：`ensure_defaults()` 按清单
把表里还没有的键补上默认值，所以**第一次启动之后这几行就该都在表里** —— 而不是「等
用户拨过那个开关、填过那个地址才冒出来」。

要加设置项时，改这里（加一行）和对应模块，别再往 `main.py` 里多挂一次调用。
"""

from tools import contacts, db, notifications

# 云端数据开关的键。值是字符串 —— 这张表只有 name/value 两列。
CLOUD_SETTING = "cloud_enabled"
CLOUD_OFF = "0"
CLOUD_ON = "1"


def defaults() -> tuple[tuple[str, str], ...]:
    """当前该有的设置项与默认值：`(键, 默认值)`。"""
    return (
        # 通知渠道 + 推送地址 + 通知提醒总开关
        (notifications.ENABLED_SETTING, notifications.ENABLED_OFF),
        (notifications.CHANNEL_SETTING, notifications.DEFAULT_CHANNEL),
        (notifications.URL_SETTING, ""),
        # 云端数据开关：默认关着（云端同步是后加的能力，不在用户还没表态时就替他打开）
        (CLOUD_SETTING, CLOUD_OFF),
        # 联系方式（邮箱、微信）—— 键和默认值都在 tools/contacts.py 里
        *((name, default) for _, name, default in contacts.DEFAULTS),
    )


def ensure_defaults() -> None:
    """把表里**还没有**的设置项按清单补上（已有的一个都不动）。

    判断用的是「键存不存在」而不是「值空不空」：用户要是故意把通知地址清空，不该被
    这里悄悄填回默认值。
    """
    stored = db.list_settings()
    for name, default in defaults():
        if name not in stored:
            db.set_setting(name, default)
