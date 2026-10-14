"""「我的」页那段背景图：存在哪、怎么铺。

- **存**：一个设置项（`settings` 表，键 `my_background`，值是图片路径）—— 和主题、设备号
  一样跟着这台设备走，见 db.get_setting / set_setting。
- **铺**：`ft.BoxFit.FILL`，也就是「均匀拉伸铺满」：不裁掉两边、也不留边，整块区域被这一
  张图填满（用户要的就是这个效果；想改成「裁满」用 COVER 即可）。
"""

import flet as ft

from tools import db

SETTING_KEY = "my_background"


def background_path() -> str:
    """当前背景图的路径；没设过就是空串。"""
    return db.get_setting(SETTING_KEY, "").strip()


def set_background(path: str) -> None:
    """把背景图换成这一张（存路径）。"""
    db.set_setting(SETTING_KEY, path.strip())


def background_image(path: str | None = None) -> ft.Control | None:
    """铺满那块区域的背景图（均匀拉伸）；没设过图就返回 `None`（那就什么都不铺）。"""
    src = background_path() if path is None else path.strip()
    if not src:
        return None
    return ft.Image(src=src, fit=ft.BoxFit.FILL, expand=True)


def background_decoration(path: str | None = None) -> ft.DecorationImage | None:
    """同上，但给 `ft.Container(image=...)` 用 —— **推荐这个**。

    用容器的装饰图当背景，容器会**按内容自己撑高**：既不用写死高度（写小了内容溢出、
    把下面的东西盖住还滚不动；写大了和下面之间留一条白缝），整段也天然就是可点区域。
    之前用 `Stack` + 定高 + 绝对定位的背景层，那一堆毛病都出在「必须先知道高度」上。
    """
    src = background_path() if path is None else path.strip()
    if not src:
        return None
    return ft.DecorationImage(src=src, fit=ft.BoxFit.FILL)
