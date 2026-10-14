"""本地文件的落点：App 自己的数据目录，以及「把选中的文件复制进来」。

打包后的 App 跑在只读包里，只有 `FLET_APP_STORAGE_DATA` 指的目录**可写**；源码运行时退回
项目根。（这套判断原先在本地数据层里算 `DB_PATH` 的父目录，那一层已经删掉了 —— 现在本地
文件只有这一套口径，换背景图 / 存头像都走它。）

为什么非得复制进来：相册 / 图库给回来的多半是**临时路径**（Android 上还可能是
`content://` 这类取不到的东西），过一会儿就失效，甚至根本渲染不出来 —— 表现就是「选完了
没反应、看不到图」（pages/background.py 里那段注释也在说这件事）。
"""

import os
import shutil
from pathlib import Path

_DATA_DIR = os.environ.get("FLET_APP_STORAGE_DATA")
APP_DIR = Path(_DATA_DIR) if _DATA_DIR else Path(__file__).resolve().parents[2]


def copy_into_app(source: str, name: str) -> str:
    """把 `source` 复制成 `APP_DIR/name.<后缀>`，返回新路径；复制不成就返回原路径。

    `name` 是**不带后缀**的文件名（后缀跟着源文件走，认不出来按 `.jpg`）。
    """
    try:
        suffix = Path(source).suffix.lower() or ".jpg"
        target = APP_DIR / f"{name}{suffix}"
        shutil.copyfile(source, target)
        return str(target)
    except Exception:  # noqa: BLE001 —— 复制不了就用原路径，总比什么都不做强
        return source
