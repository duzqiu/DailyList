"""「当前位置」（「选择你的地区」页最上面那行「定位到的位置」用）。

⚠️ **先说清楚能力边界：flet 1.x 拿不到系统定位。**

- 它没有地理位置 Service —— 老版本那个 `ft.Geolocator` 在 flet 1.0 里已经不在
  （`flet/controls/services/` 下只有剪贴板 / 文件选择器 / 客户端存储 / 传感器这些）；
- 也没有能执行 JS 的口子，浏览器那套 `navigator.geolocation`（真正会弹「允许获取
  位置信息」权限框的那个）从 Python 这一侧够不着。

所以**弹不出系统的定位权限框、也拿不到经纬度**。这里退一步用 **IP 定位**：拿到的就是
本机出网 IP 对应的省 / 市 / 区（国内接口多数给到市级、个别能到区级），不需要任何权限。
给到哪一级就显示哪一级 —— 有区就「中国 上海市 浦东新区」，只有省市就「中国 上海市」。

**将来要换成真 GPS**：让后端加一个接口（收经纬度、回行政区划名），把 `_resolve()` 换成
打那个接口即可 —— 页面只认 `locate()` 返回的 `Location`（字段不变）。

公网接口未必每次都通，所以：**成功的结果缓存一会儿**（同一台设备的位置不会一秒一变），
失败**不缓存** —— 用户点一下还能重试。
"""

import asyncio
import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 单次请求超时（秒）：定位是「顺手的事」，不能让用户干等。
TIMEOUT = 6
# 成功结果的缓存时长（秒）。失败不缓存。
CACHE_TTL = 300
# 接口会按 UA 过滤（和 api/client.py 一个道理），给个浏览器样子的。
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 国内那两个接口都要走一遍才好在公司 / 家宽下都拿得到结果：
#   1. 哔哩哔哩的 zone：中文，**大陆 IP 能到区**（拿不到区就退到市）；
#   2. 太平洋网络的 whois：中文省 / 市，覆盖面更稳（返回体是 **GBK**）。
BILIBILI_URL = "https://api.bilibili.com/x/web-interface/zone"
PCONLINE_URL = "https://whois.pconline.com.cn/ipJson.jsp?json=true"


@dataclass(frozen=True)
class Location:
    """定位结果。各级都可能为空（接口给到哪一级是哪一级）。"""

    country: str = ""
    province: str = ""
    city: str = ""
    district: str = ""

    @property
    def empty(self) -> bool:
        return not (self.country or self.province or self.city or self.district)


# (取到的时间, 结果)。整个 App 一份 —— 位置按设备算，和设备上的账号无关。
_CACHE: tuple[float, Location] | None = None


def cached() -> Location | None:
    """**同步**看一眼缓存（进页面时先拿它把行摆上，别等网络）。"""
    if _CACHE is None:
        return None
    saved_at, spot = _CACHE
    if time.monotonic() - saved_at >= CACHE_TTL:
        return None
    return spot


def forget() -> None:
    """丢掉缓存（用户点「重试」时用）。"""
    global _CACHE
    _CACHE = None


async def locate(use_cache: bool = True) -> Location | None:
    """拿到当前大致位置；全都失败给 `None`。

    真正的网络调用丢进线程（`asyncio.to_thread`）—— Flet 的事件处理跑在事件循环上，
    在里面直接阻塞会把整个界面冻住（api/client.py 的 `request` 也是这么处理的）。
    """
    if use_cache:
        hit = cached()
        if hit is not None:
            return hit
    global _CACHE
    try:
        spot = await asyncio.to_thread(_resolve)
    except Exception as error:  # noqa: BLE001
        # 定位失败只是那一行没内容，不该把页面炸掉。
        logger.warning("定位失败: %s", error)
        return None
    if spot is None:
        return None
    _CACHE = (time.monotonic(), spot)
    return spot


def _resolve() -> Location | None:
    """逐个试接口，第一个拿得出东西的就是答案。"""
    for provider in (_bilibili, _pconline):
        try:
            spot = provider()
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            logger.warning("%s 定位失败: %s", provider.__name__, error)
            continue
        except (ValueError, KeyError, TypeError) as error:
            # 接口改版 / 返回体不是预期形状：换下一个，别让页面报错。
            logger.warning("%s 返回体不认识: %s", provider.__name__, error)
            continue
        if spot is not None and not spot.empty:
            return spot
    return None


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers=DEFAULT_HEADERS)
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def _text(raw: bytes) -> str:
    """把响应体解成文本：先按 UTF-8，再退到 GBK（太平洋网络那个就是 GBK）。"""
    for encoding in ("utf-8", "gbk"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def _bilibili() -> Location | None:
    """哔哩哔哩的 zone：中文，大陆 IP 能给到区。"""
    payload = json.loads(_text(_get(BILIBILI_URL)))
    data = payload.get("data") or {}
    return Location(
        country=_name(data.get("country")),
        province=_name(data.get("province")),
        city=_name(data.get("city")),
        district=_name(data.get("district")),
    )


def _pconline() -> Location | None:
    """太平洋网络的 whois：中文省 / 市。"""
    payload = json.loads(_text(_get(PCONLINE_URL)))
    province = _name(payload.get("pro"))
    if not province:
        return None
    # 「未分配或者内网IP」这类不是地名，`match_location` 认不出来也无所谓 ——
    # 这里只把明显不是地名的挡掉。
    return Location(province=province, city=_name(payload.get("city")))


def _name(value: object) -> str:
    """接口字段统一处理成去空白的字符串（可能是 None / 数字 / 带「市」的串）。"""
    if value is None:
        return ""
    return str(value).strip()
