"""登录态：access / refresh 令牌放这儿。

只做存取，不发请求（令牌怎么带上见 `client.request(token=...)`）。放在 api 包里是
因为它就是接口的凭据；落库走 `tools/db.py` 的 settings 表 —— 那张表本来就是"这台
设备的配置"（不带 owner，换设备就是另一份，和倒数日的归属规则一致）。

空串 = 没登录：后端是无状态 JWT，退出登录只要把本地令牌清掉，不用通知它。
"""

from tools import db

ACCESS_KEY = "member_access_token"
REFRESH_KEY = "member_refresh_token"


def save(token: dict | None) -> None:
    """登录 / 刷新成功后存下令牌（后端的 `Token`：access_token + refresh_token）。

    传 `None` 或空字典就是清空（`clear()` 走这条路），所以这里不假设一定有内容。
    """
    data = token if isinstance(token, dict) else {}
    db.set_setting(ACCESS_KEY, str(data.get("access_token") or ""))
    db.set_setting(REFRESH_KEY, str(data.get("refresh_token") or ""))


def clear() -> None:
    """退出登录：清掉本地令牌（存空串即可，settings 表不必删行）。"""
    save({})


def access_token() -> str:
    """当前 access_token；没登录是空串。"""
    return db.get_setting(ACCESS_KEY, "")


def refresh_token() -> str:
    """当前 refresh_token；没登录是空串。"""
    return db.get_setting(REFRESH_KEY, "")
