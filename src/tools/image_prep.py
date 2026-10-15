"""上传前把图片压小一点 —— 手机照片动辄 3～8MB，直接传**又慢又容易撞 5MB 上限**。

做法：能拿到内容（或本地路径）就用 Pillow 把长边缩到 `MAX_EDGE`、转成 JPEG
（质量 `QUALITY`，还超上限就逐档降质量，保底 `QUALITY_FLOOR`）。

几条**故意保留的退路**（压缩只是优化，绝不能因为它把上传搞挂）：
- 没有 Pillow、图打不开、动图（GIF / 多帧）→ **原样返回**，让上传自己走原路；
- 压完反而更大（比如本来就是张很小的 PNG）→ 用原来那份；
- 压完还是超 `MAX_UPLOAD_BYTES` → 照样返回（后端会给出明确的错误提示，好过这里静默失败）。

返回值里的文件名会跟着变成 `.jpg` —— 后端靠**后缀**判断图片格式，转码了就得改名。
"""

import io
import logging
import os
from pathlib import Path
from typing import Any, Optional, Tuple

from api.client import MAX_UPLOAD_BYTES, resolve_local_path

logger = logging.getLogger(__name__)

# 选图器自己的压缩质量（传给 `FilePicker.pick_files(compression_quality=...)`）。
# ⚠️ **iOS 靠它把 HEIC 转成 JPEG**：iPhone 相机默认拍 HEIC，选图器带了这个值就会
# 直接给一份 JPEG（顺带压小），不用等后端转码，也省一次网络往返。
# 桌面端这个参数会被忽略（不影响）。
PICKER_QUALITY = 85
# 长边上限（像素）：1920 够「我的」页背景图铺满手机屏了，再大纯属浪费流量。
MAX_EDGE = 1920
# 起始 / 保底 JPEG 质量。
QUALITY = 85
QUALITY_FLOOR = 55
# 小于这个大小就不折腾了（已经是小图，转码可能还变大）。
SKIP_BELOW_BYTES = 240 * 1024


def _read_source(picked: Any) -> Tuple[Optional[bytes], str]:
    """把选择器给的东西读成 (内容, 文件名)；拿不到内容就是 (None, 文件名)。"""
    if isinstance(picked, str):
        target = resolve_local_path(picked)
        name = os.path.basename(picked)
        if target is None:
            return None, name
        try:
            return target.read_bytes(), target.name
        except OSError:
            return None, name

    name = str(getattr(picked, "name", "") or "")
    content = getattr(picked, "bytes", None)
    if content:
        return bytes(content), name or "upload.jpg"

    path = str(getattr(picked, "path", "") or "")
    name = name or os.path.basename(path)
    target = resolve_local_path(path) if path else None
    if target is None:
        return None, name
    try:
        return target.read_bytes(), name or target.name
    except OSError:
        return None, name


def _squeeze(raw: bytes) -> Optional[Tuple[bytes, str]]:
    """缩图 + 转 JPEG；不适合压 / 压不动就返回 `None`。"""
    try:
        from PIL import Image, ImageOps
    except ImportError:  # pragma: no cover - 没装 Pillow 的旧环境
        logger.info("没装 Pillow，跳过压缩直接上传")
        return None

    try:
        with Image.open(io.BytesIO(raw)) as image:
            # 动图（GIF / 多帧 WebP）别动：压完只剩第一帧，等于把用户的原图毁了。
            if getattr(image, "is_animated", False) or getattr(image, "format", "") == "GIF":
                return None
            # 手机照片靠 EXIF 记旋转，先正过来，否则压完可能是躺着的。
            image = ImageOps.exif_transpose(image)
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            image.thumbnail((MAX_EDGE, MAX_EDGE))  # 只缩不放，保持比例

            data = b""
            for quality in range(QUALITY, QUALITY_FLOOR - 1, -10):
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=quality, optimize=True)
                data = buffer.getvalue()
                if len(data) <= MAX_UPLOAD_BYTES:
                    break
            return data, "photo.jpg"
    except Exception as error:  # noqa: BLE001 - 任何解码/编码问题都退回原图
        logger.info("图片压缩失败，按原图上传: %s", error)
        return None


def prepare(picked: Any) -> Tuple[Optional[bytes], str]:
    """上传前处理：返回 **(要上传的内容, 文件名)**。

    - 内容为 `None`：没拿到文件内容（调用方回退成「按路径上传」）；
    - 文件名与内容配套（压过就是 `.jpg`），后端靠后缀判断格式。
    """
    raw, name = _read_source(picked)
    if raw is None:
        return None, name

    if len(raw) < SKIP_BELOW_BYTES:
        return raw, name or "upload"

    squeezed = _squeeze(raw)
    if squeezed is None:
        return raw, name or "upload"

    data, _ = squeezed
    if len(data) >= len(raw):
        # 压完更大（小的 PNG / 已经压过的图）就用原来那份，别白折腾。
        return raw, name or "upload"

    stem = Path(name).stem if name else "photo"
    logger.info(
        "图片已压缩后上传: %s -> %s.jpg（%.1fKB -> %.1fKB）",
        name or "（无名）",
        stem,
        len(raw) / 1024,
        len(data) / 1024,
    )
    return data, f"{stem}.jpg"


__all__ = ["prepare", "PICKER_QUALITY", "MAX_EDGE", "QUALITY"]
