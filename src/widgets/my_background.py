"""「我的」页那段背景图：存在哪、怎么铺。

- **存**：跟头像一样**存后端**，按会员 ID 分目录
  （`data/uploads/backgrounds/{会员ID}/background_{会员ID}_{随机串}.{ext}`），
  改完立刻生效、换设备登录也还在。读取走资料接口出参的 `background_url`
  （见 api/member_profile.py、tools/my_profile.py）—— **本地不再存副本**
  （`tools/mock_settings.py` 里那个 `my_background` 键已经删掉）。
- **铺**：`ft.BoxFit.FILL`，也就是「均匀拉伸铺满」：不裁掉两边、也不留边，整块区域被这一
  张图填满（用户要的就是这个效果；想改成「裁满」用 COVER 即可）。
- **换**：「换背景图」那一页选图后**上传**到后端（pages/background.py），不再复制进
  App 目录 —— 原来那种本地存法重启还在，但换设备就没了，也占 App 自己的存储空间。
"""

import flet as ft

from tools.my_profile import background_path

__all__ = ["background_path", "background_image", "background_decoration"]


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
