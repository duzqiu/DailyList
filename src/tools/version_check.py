"""查新版本：跟 GitHub 仓库上的最新 tag / Release 比一比。

App 是纯本地的、没有服务端，「有没有新版本」只能去仓库问：先看 `releases/latest`
（发过 Release 就有 `tag_name`），没发过就退一步看 `tags` 列表。两个请求都走标准库
`urllib`（**阻塞**，调用方扔线程里跑）—— 为一个 GET 引入 HTTP 依赖不值当。
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

# 当前版本：和 pyproject.toml 里的 `version` 是一对，改版本号得两处一起改 ——
# 打包之后那份 pyproject 并不在包里，运行时读不到，所以这里只能是手写的常量。
# 界面上显示成带 `v` 的样子；和仓库 tag 比较时两边都会先规范化（见 parse_version）。
APP_VERSION = "v0.1.0"

GITHUB_REPO = "duzqiu/DailyList"
# HTTP 头只能是 ASCII：这个**不能**拿中文的应用名去拼，否则 `urllib` 在发请求之前
# 就先抛 `UnicodeEncodeError: 'latin-1' codec can't encode characters`（GitHub 的
# API 又要求必须带 User-Agent）。踩过一次，别改回中文。
USER_AGENT = "DailyList"
RELEASES_LATEST_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
TAGS_URL = f"https://api.github.com/repos/{GITHUB_REPO}/tags"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases/latest"
REQUEST_TIMEOUT_SECONDS = 6


def parse_version(text: str) -> tuple[int, ...]:
    """`v1.2.3` / `1.2.3` 都解析成 `(1, 2, 3)`；后面认不出就不管了。"""
    parts: list[int] = []
    for chunk in (text or "").strip().lstrip("vV").split("."):
        digits = ""
        for char in chunk:
            if not char.isdigit():
                break
            digits += char
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def is_newer(latest: str, current: str = APP_VERSION) -> bool:
    """仓库上那个版本比当前这份新吗。"""
    return parse_version(latest) > parse_version(current)


def _fetch_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(
        request, timeout=REQUEST_TIMEOUT_SECONDS
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def latest_version() -> str | None:
    """仓库上最新的版本号原文（形如 `v0.2.0`）。

    返回值分三种，页面据此说不同的话：
    - 拿到版本号 -> 返回它；
    - 两个请求都没打通（断网、被墙、超时）-> `None`；
    - 请求通了、但仓库**还没打过版本**（既没 Release 也没 tag）-> 空串。

    **这是阻塞调用**，页面里记得扔线程：`await asyncio.to_thread(latest_version)`。
    """
    try:
        tag = _fetch_json(RELEASES_LATEST_URL).get("tag_name")
        if tag:
            return str(tag)
    except Exception:
        # 没发过 Release 时 GitHub 直接回 404 —— 静默退到 tags 就好。
        logger.debug("读 releases/latest 失败，改看 tags", exc_info=True)
    try:
        tags = _fetch_json(TAGS_URL)
    except Exception:
        logger.debug("读 tags 失败", exc_info=True)
        return None
    if isinstance(tags, list):
        for item in tags:
            name = item.get("name") if isinstance(item, dict) else None
            if name:
                return str(name)
    # 请求通了，只是仓库里还没有 Release / tag。
    return ""
