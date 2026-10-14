"""登录态：令牌存**客户端存储**（Flet 的 `SharedPreferences`），内存里留一份镜像。

**为什么要有镜像**：读写客户端存储都是协程（得往客户端跑一趟才拿得到），而调用方 —— 页面
构建、`countdown_store.logged_in()`、每次请求拼 `token=` —— 全是**同步**的。所以：

- 启动时 `await restore()` 读一次，填进镜像（见 main.py）；
- `access_token()` / `refresh_token()` 同步读镜像 —— 一个字典，不碰 IO；
- `save()` / `clear()` 同步改镜像，再让页面把新值异步写回去。

**存哪儿**：Flet 的 `SharedPreferences`（Web 上是浏览器 localStorage，桌面 / 移动上是各平台
自己的偏好存储）—— 跟着客户端走：同一个浏览器 / 同一台设备还在，登录态就在；清了 App 数据
就没了。这张表不带 owner，设备之间不共享。

空串 = 没登录：后端是无状态 JWT，退出登录只要把本地令牌清掉，不用通知它。令牌怎么带上见
`client.request(token=...)`。
"""

from __future__ import annotations

import asyncio
import logging

import flet as ft

logger = logging.getLogger(__name__)

ACCESS_KEY = "member_access_token"
REFRESH_KEY = "member_refresh_token"
# 启动时读客户端存储的等待上限：客户端要是迟迟没连上，别把首帧一直拖住 ——
# 读不到就当没登录（下次进出页面时各请求自然会 401，用户重新登录即可）。
RESTORE_TIMEOUT = 5.0

# 内存镜像：这两个键的当前值。没登录就是两个空串。
_cache: dict[str, str] = {ACCESS_KEY: "", REFRESH_KEY: ""}
_page: ft.Page | None = None
_prefs: ft.SharedPreferences | None = None


async def restore(page: ft.Page, prefs: ft.SharedPreferences) -> None:
    """把客户端存储里的令牌读进内存镜像（启动时调一次）。

    读失败 / 超时都**不抛**：当作没登录继续跑，首帧不能被这一步卡住。
    """
    global _page, _prefs
    _page = page
    _prefs = prefs
    try:
        stored = await asyncio.wait_for(_read_all(), timeout=RESTORE_TIMEOUT)
    except Exception as error:  # noqa: BLE001 —— 读不到不是错误，是"这次没登录"
        logger.warning("读客户端存储里的令牌失败（按未登录处理）：%s", error)
        return
    _cache.update(stored)
    logger.debug(
        "登录态已恢复：%s", "有令牌" if _cache[ACCESS_KEY] else "没有令牌"
    )


async def _read_all() -> dict[str, str]:
    """一次把两个键都读回来（`assert` 只是让类型检查闭嘴，restore 里必然已赋值）。"""
    assert _prefs is not None
    return {
        ACCESS_KEY: str(await _prefs.get(ACCESS_KEY) or ""),
        REFRESH_KEY: str(await _prefs.get(REFRESH_KEY) or ""),
    }


def save(token: dict | None) -> None:
    """登录 / 刷新成功后存下令牌（后端的 `Token`：access_token + refresh_token）。

    传 `None` 或空字典就是清空（`clear()` 走这条路），所以这里不假设一定有内容。
    """
    data = token if isinstance(token, dict) else {}
    _cache[ACCESS_KEY] = str(data.get("access_token") or "")
    _cache[REFRESH_KEY] = str(data.get("refresh_token") or "")
    _persist()


def clear() -> None:
    """退出登录：清掉本地令牌（存空串即可，不必把键删掉）。"""
    save({})


def access_token() -> str:
    """当前 access_token；没登录是空串。"""
    return _cache[ACCESS_KEY]


def refresh_token() -> str:
    """当前 refresh_token；没登录是空串。"""
    return _cache[REFRESH_KEY]


def _persist() -> None:
    """把镜像里的两个键写回客户端存储：交给页面跑（`run_task`），失败只记日志。

    刻意不阻塞调用方 —— `save()` 是在登录回调里同步调的，写盘慢不该拖着界面走。真写失败
    （客户端已经断开之类）就只剩内存里那份，重启后需要重新登录，日志里留个痕。
    """
    if _page is None:
        logger.warning("还没有页面上下文，令牌只留在内存里（重启后要重新登录）")
        return
    try:
        _page.run_task(_write_all, _cache[ACCESS_KEY], _cache[REFRESH_KEY])
    except Exception as error:  # noqa: BLE001
        logger.warning("写令牌到客户端存储失败：%s", error)


async def _write_all(access: str, refresh: str) -> None:
    assert _prefs is not None
    try:
        await _prefs.set(ACCESS_KEY, access)
        await _prefs.set(REFRESH_KEY, refresh)
    except Exception as error:  # noqa: BLE001
        logger.warning("写令牌到客户端存储失败：%s", error)
