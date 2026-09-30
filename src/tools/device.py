"""设备主键：数据按「这台设备」隔开。

待办和倒数日在库里都带一列 `owner`（见 tools/db.py），值就是这里的设备主键 —— 换一台
设备就是另一份清单，同一台设备上永远认回自己那份。

主键从 `page.get_device_info()` 回的那份设备信息里取，**各平台的字段不一样**：

- iOS     `identifier_for_vendor`（IDFV）—— 本模块唯一一个真正"唯一"的标识
- macOS   `system_guid`
- Windows `device_id`
- Linux   `machine_id`
- Android **没有**：`id` 是 `Build.ID`（构建号，同型号同系统版本全都一样），
          `fingerprint` 也是同机型共享，而 `device_info_plus` 并没有暴露 `ANDROID_ID`
          或序列号。所以这一档一律返回空串 —— 等于所有 Android 共用"默认那一份"，
          先用着（真要区分得另想办法）。
- Web     **没有**：浏览器不给，同样返回空串。

拿到的标识会拼成 `平台:标识`（如 `ios:9F3A…-…`）：跨平台的标识格式本来就不同，明着
写个前缀更省心，也不会出现"两个平台恰好同值"这种事。
"""

from __future__ import annotations

import logging

import flet as ft

logger = logging.getLogger(__name__)


def _compose(platform: str, identifier: str | None) -> str:
    """把平台名和标识拼成主键；标识是空的（平台没给）就返回空串。"""
    value = (identifier or "").strip()
    return f"{platform}:{value}" if value else ""


def key_from(info: ft.DeviceInfo | None) -> str:
    """从一份设备信息里取出主键；这一档拿不到稳定标识就返回空串。

    纯函数、不碰页面 —— 直接喂假数据就能把每个平台的分支都试一遍。
    """
    if isinstance(info, ft.IosDeviceInfo):
        return _compose("ios", info.identifier_for_vendor)
    if isinstance(info, ft.MacOsDeviceInfo):
        return _compose("macos", info.system_guid)
    if isinstance(info, ft.WindowsDeviceInfo):
        return _compose("windows", info.device_id)
    if isinstance(info, ft.LinuxDeviceInfo):
        return _compose("linux", info.machine_id)
    # Android / Web：上面说的原因，没有稳定标识可用。
    return ""


async def read_key(page: ft.Page) -> str:
    """问一次设备信息，取出主键。

    `get_device_info()` 是协程（Flet 这个接口要往客户端跑一趟），所以只在启动时问
    一次、结果交给 `db.set_data_owner()` 存着，之后数据层的每次读写都用那份。
    客户端不认这个接口时它会抛，这里兜住 —— 拿不到就当"默认那一份"。
    """
    try:
        info = await page.get_device_info()
    except Exception:
        logger.exception("读取设备信息失败，数据将按默认那一份存取")
        return ""
    key = key_from(info)
    logger.debug("设备主键 = %r（%s）", key, type(info).__name__)
    return key
