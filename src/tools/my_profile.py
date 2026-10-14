"""本地「我的资料」：昵称 / 小红书号 / 简介 / 性别 / 生日 / 头像。

**存哪儿**：**内存里的 mock 数据**（`tools/mock_settings.py`，目前不落库）—— 改完当次运行
内有效，重启回到那份示例值。

**为什么是本地**：后端 `GET /member/auth/me` 只回 `email` / `display_name` / `nickname` /
`member_no` 这几个字段，**没有头像、性别、简介**这些，也没有更新资料的接口（见
api/member_auth.py）。所以这些先自己存着；`name()` / `xhs_id()` 会**优先用本地改过的值**，
没改过才回落到账号里的值 —— 于是「在编辑资料页改完名字，`我的` 页立刻跟着变」。

**图片**（头像）**先复制进 App 自己的目录**再存路径：相册 / 图库给回来的多半是临时路径，
过一会儿就失效，甚至根本渲染不出来（同 pages/background.py 里那段注释）。
"""

from tools import files, mock_settings

NAME_KEY = "my_name"
XHS_ID_KEY = "my_xhs_id"
INTRO_KEY = "my_intro"
GENDER_KEY = "my_gender"
BIRTHDAY_KEY = "my_birthday"
AVATAR_KEY = "my_avatar"

# 「性别」那三个选项（编辑资料页点「性别」弹的就是它们）。
GENDERS = ("男", "女", "保密")

# 简介没填过时那行浅灰占位（照小红书那版）。
INTRO_HINT = "介绍一下自己"


def _read(key: str) -> str:
    return (mock_settings.get_setting(key, "") or "").strip()


def _write(key: str, value: str) -> None:
    mock_settings.set_setting(key, (value or "").strip())


def name() -> str:
    """本地改过的名字；没改过是空串（那就用账号里的昵称）。"""
    return _read(NAME_KEY)


def set_name(value: str) -> None:
    _write(NAME_KEY, value)


def xhs_id() -> str:
    """本地改过的小红书号；没改过是空串（那就用账号里的会员号）。"""
    return _read(XHS_ID_KEY)


def set_xhs_id(value: str) -> None:
    _write(XHS_ID_KEY, value)


def intro() -> str:
    """简介；没填过是空串。"""
    return _read(INTRO_KEY)


def set_intro(value: str) -> None:
    _write(INTRO_KEY, value)


def gender() -> str:
    """性别（「男」/「女」/「保密」）；没选过是空串。"""
    return _read(GENDER_KEY)


def set_gender(value: str) -> None:
    _write(GENDER_KEY, value)


def birthday() -> str:
    """生日，`YYYY-MM-DD`；没选过是空串。"""
    return _read(BIRTHDAY_KEY)


def set_birthday(value: str) -> None:
    _write(BIRTHDAY_KEY, value)


def avatar_path() -> str:
    """头像的路径；没设过就是空串。"""
    return _read(AVATAR_KEY)


def set_avatar(path: str) -> None:
    _write(AVATAR_KEY, path)


def store_avatar(source: str) -> str:
    """把选中那张图复制进 App 自己的目录，返回可以长期用的路径。

    复制不了就用原路径 —— 总比什么都不做强（同 background.py 的选图那条路）。
    """
    return files.copy_into_app(source, "my_avatar")


def account_name(account: dict | None) -> str:
    """名字这一行显示什么：本地改过的优先，其次账号里的昵称 / 显示名 / 邮箱。"""
    local = name()
    if local:
        return local
    if not account:
        return ""
    return str(
        account.get("display_name")
        or account.get("nickname")
        or account.get("email")
        or ""
    ).strip()


def account_id(account: dict | None) -> str:
    """小红书号这一行：本地改过的优先，其次账号里的会员号。"""
    local = xhs_id()
    if local:
        return local
    if not account:
        return ""
    return str(account.get("member_no") or "").strip()
