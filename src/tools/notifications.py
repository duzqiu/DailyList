"""通知渠道: where a reminder is delivered.

Only the configuration lives here so far - the names of the `settings` rows it
owns and the channels the 通知渠道 picker offers.
"""

CHANNELS = ("Bark", "Pushdeer", "Server酱", "企业微信", "钉钉", "飞书", "Telegram", "Discord", "Slack")
DEFAULT_CHANNEL = CHANNELS[0]

CHANNEL_SETTING = "notify_channel"
URL_SETTING = "notify_url"


def summary(channel: str, url: str) -> str:
    """One-line state of the configuration, shown under 通知渠道."""
    if not url:
        return f"{channel} · 未设置通知地址"
    return f"{channel} · {url}"
