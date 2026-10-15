"""「我的资料」的**读取**层：昵称 / 会员号 / 简介 / 性别 / 生日 / 地区 / 头像。

**数据从哪来**：后端 `GET /member/profile`（见 api/member_profile.py）。登录成功后拉
一次、存进接口层的缓存；**本地不再存任何资料**（原来那份 mock 数据连同
`tools/mock_settings.py` 里的 `my_*` 几个键已经删掉）。改资料也不落本地：编辑资料页
直接调 `PUT /member/profile`（见 pages/edit_profile.py）。

**为什么还要这一层**：界面上要的是**中文性别**、**能直接喂给 `ft.Image(src=)` 的头像
绝对地址**、以及「没填过就摆占位」这种零碎规则 —— 这些不属于「发什么、收什么」，
放在这里，页面只管读。

**头像**：后端按**会员 ID** 存（`data/uploads/avatars/{会员ID}/`），出参 `avatar_url`
是 `/api/v1/static/...` 这种相对路径，`avatar_path()` 会拼成完整 URL；没上传过时后端
给的是系统默认头像地址，所以这一格永远有图可显示。不再往 App 目录里复制图片
（也就没有 `store_avatar` 了）。
"""

from api import member_profile

# 性别选项（编辑资料页点「性别」弹的就是它们）。
GENDERS = member_profile.GENDERS

# 简介没填过时那行浅灰占位（照小红书那版）。
INTRO_HINT = member_profile.INTRO_HINT


def current() -> dict:
    """当前资料（`MemberOut`）；没登录 / 还没拉到就是空字典。"""
    return member_profile.cached_profile() or {}


def _text(key: str) -> str:
    return str(current().get(key) or "").strip()


def name() -> str:
    """昵称。"""
    return _text("nickname")


def xhs_id() -> str:
    """会员号（后端叫 `member_no`，**不可改** —— 注册时生成的 6 位号）。"""
    return _text("member_no")


def intro() -> str:
    """简介（后端字段 `bio`）；没填过是空串。"""
    return _text("bio")


def gender() -> str:
    """性别（「男」/「女」/「保密」）；没选过是空串。"""
    raw = _text("gender")
    if not raw:
        return ""
    return member_profile.GENDER_FROM_API.get(raw, member_profile.DEFAULT_GENDER)


def birthday() -> str:
    """生日，`YYYY-MM-DD`；没选过是空串。"""
    return _text("birthday")


def region() -> str:
    """地区（后端字段 `region`）；没填过是空串。"""
    return _text("region")


def avatar_path() -> str:
    """头像的**绝对地址**（可直接给 `ft.Image(src=)`）；没有就是空串（页面摆图标）。"""
    return member_profile.avatar_url(current())


def background_path() -> str:
    """背景图的**绝对地址**；**没上传过就是空串** —— 与头像不同，背景没有默认图，
    空串时「我的」页按「不铺背景图」处理（浅蓝渐变兜底，见 widgets/my_background.py）。
    """
    return member_profile.background_url(current())


def account_name(account: dict | None = None) -> str:
    """名字这一行显示什么：资料里的昵称优先，其次账号里的显示名 / 昵称 / 邮箱。"""
    return (
        name()
        or str(
            (account or {}).get("display_name")
            or (account or {}).get("nickname")
            or (account or {}).get("email")
            or ""
        ).strip()
    )


def account_id(account: dict | None = None) -> str:
    """「小红书号」这一行：就是会员号（资料优先，其次账号里的）。"""
    return xhs_id() or str((account or {}).get("member_no") or "").strip()


def account_gender(account: dict | None = None) -> str:
    """昵称后面那枚符号用哪个性别：资料优先，其次账号里的。

    返回**中文**（「男」/「女」/「保密」）；资料和账号里都没有就是空串。
    后端将来加了新的取值也返回空串 —— 只会「不画符号」，不会画错（见
    widgets/gender_mark.py：只认「男」「女」）。
    """
    value = gender()
    if value:
        return value
    raw = str((account or {}).get("gender") or "").strip()
    return member_profile.GENDER_FROM_API.get(raw, "") if raw else ""
