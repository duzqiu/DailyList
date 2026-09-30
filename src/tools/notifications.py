"""通知渠道: where a reminder is delivered.

Only the configuration lives here so far - the names of the `settings` rows it
owns, the channels the 通知渠道 picker offers, and the icon each channel wears
in that picker.
"""

import flet as ft

CHANNELS = ("Bark", "Pushdeer", "Server酱", "企业微信", "钉钉", "飞书", "Telegram", "Discord", "Slack")
DEFAULT_CHANNEL = CHANNELS[0]

# 每个渠道一枚图标。Telegram / Discord / 微信有官方品牌图标，直接用；其余几个没有，
# 就挑意思最近、彼此又不相撞的那一枚 —— 既别让他们空着，也别几项画成一模一样。
CHANNEL_ICONS = {
    "Bark": ft.Icons.NOTIFICATIONS,  # 它本身就是一个通知 App
    "Pushdeer": ft.Icons.SEND,  # 把消息推出去
    "Server酱": ft.Icons.WECHAT,  # 它是往微信推的
    "企业微信": ft.Icons.BUSINESS,  # 企业向（和上面那枚微信区分开）
    "钉钉": ft.Icons.CHAT,  # 工作沟通
    "飞书": ft.Icons.FORUM,  # 团队协作
    "Telegram": ft.Icons.TELEGRAM,  # 品牌图标
    "Discord": ft.Icons.DISCORD,  # 品牌图标
    "Slack": ft.Icons.TAG,  # Slack 的 # 频道
}

CHANNEL_SETTING = "notify_channel"
URL_SETTING = "notify_url"
# 通知提醒的总开关。和云端那个开关一样：值是字符串（这张表只有 name/value 两列），
# 默认**关**着 —— 通知是这个 App 唯一会「往外发东西」的能力，不该在用户还没表态时
# 替他打开（渠道和地址备好了也得他点一下才生效）。
ENABLED_SETTING = "notify_enabled"
ENABLED_ON = "1"
ENABLED_OFF = "0"


def channel_icon(name: str) -> ft.IconData:
    """渠道对应的图标；不认识的渠道给一枚通用铃铛（别让它空着）。"""
    return CHANNEL_ICONS.get(name, ft.Icons.NOTIFICATIONS)


def summary(channel: str, url: str) -> str:
    """One-line state of the configuration, shown under 通知渠道.

    只说这两项**自己**的状态（渠道 + 地址），**不看「通知提醒」那个总开关** ——
    开关是另一行的事，两处联动的话，关掉提醒会让这一行看不出渠道和地址配没配好。
    """
    if not url:
        return f"{channel} · 未设置通知地址"
    return f"{channel} · {url}"
