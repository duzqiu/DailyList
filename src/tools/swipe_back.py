"""Left-swipe anywhere on a 二级 / 三级页 to go back one level.

The page does not follow the finger: a swipe either counts as 「返回上一页」 or
is ignored, so nothing moves unless the gesture passes the thresholds below.
"""

import logging
from collections.abc import Callable

import flet as ft

logger = logging.getLogger(__name__)

# 左滑 = 手指往左走 = dx 为负。走够距离、或者甩得够快，都算一次「返回上一页」；
# 两个阈值跟首页切日期的横滑取同一档（见 pages/home.py 的 DATE_SWIPE_*），整台
# 机器的横滑手感一致。整页横滑的命中面积大，所以不跟手、也不画「滑到一半」的
# 中间态。
SWIPE_BACK_DISTANCE = 24.0
SWIPE_BACK_VELOCITY = 300.0
# 屏幕左右两条边是**系统**的手势区（Android 的返回手势就从边上往中间划）。从
# 那儿起手的横滑 App 管不着 —— 系统会先把它拿走，所以这一档干脆不接：既不必和
# 系统抢，也不会「系统回一层 + App 再回一层」一次划掉两层。
SWIPE_BACK_EDGE_INSET = 32.0


def build_swipe_back(
    content: ft.Control, go_back: Callable[[], None]
) -> ft.Control:
    """Wrap `content` so swiping left calls `go_back`.

    Only the horizontal-drag family is bound, never the pan family: a vertical
    drag still belongs to whatever the page scrolls, and the two never fight
    over the same gesture. A row's own left swipe (露出编辑 / 删除) sits deeper
    in the tree, so it wins the arena when the drag starts on it - the same
    arrangement the home page relies on.
    """
    swipe: dict[str, float] = {"dx": 0.0, "dy": 0.0}
    from_edge: dict[str, bool] = {"value": False}

    def starts_in_system_area(e: ft.DragStartEvent) -> bool:
        """起手点是否落在左右两侧的系统手势区里。

        量不到（控件还没挂到 page 上、屏宽还没报上来）就按「不是」处理：宁可
        接住这一划，也不要因为量不到就把返回丢掉。
        """
        try:
            position = e.global_position or e.local_position
            width = e.control.page.width
            if position is None or not width:
                return False
            return (
                position.x <= SWIPE_BACK_EDGE_INSET
                or position.x >= width - SWIPE_BACK_EDGE_INSET
            )
        except Exception:
            # 探这套东西只是为了不和系统抢边；量不出来（控件还没挂到 page 上、
            # 屏宽还没报上来）就按「不是边上」——宁可接住这一划，也不要在这里
            # 把异常抛出去。
            return False

    def on_start(e: ft.DragStartEvent) -> None:
        swipe["dx"] = 0.0
        swipe["dy"] = 0.0
        from_edge["value"] = starts_in_system_area(e)

    def on_update(e: ft.DragUpdateEvent) -> None:
        if e.local_delta:
            swipe["dx"] += e.local_delta.x
            swipe["dy"] += e.local_delta.y

    def on_end(e: ft.DragEndEvent) -> None:
        travelled = swipe["dx"]
        vertical = abs(swipe["dy"])
        blocked = from_edge["value"]
        swipe["dx"] = 0.0
        swipe["dy"] = 0.0
        from_edge["value"] = False
        # 竖着划的其实是页面在自己滚；起手落在边上那一划归系统 —— 两种都不算返回。
        if blocked or vertical > abs(travelled):
            return
        fling = e.velocity.x if e.velocity else 0.0
        if travelled <= -SWIPE_BACK_DISTANCE or fling <= -SWIPE_BACK_VELOCITY:
            try:
                go_back()
            except Exception:
                # 回调里漏出去的异常会顺着事件循环把整条会话带下去（客户端表现
                # 就是掉线回 Flet 首页）；返回失败最多让用户再点一次「‹ 返回」。
                logger.exception("swipe back failed")

    def on_cancel(_: ft.Event[ft.GestureDetector]) -> None:
        swipe["dx"] = 0.0
        swipe["dy"] = 0.0
        from_edge["value"] = False

    return ft.GestureDetector(
        expand=True,
        content=content,
        on_horizontal_drag_start=on_start,
        on_horizontal_drag_update=on_update,
        on_horizontal_drag_end=on_end,
        on_horizontal_drag_cancel=on_cancel,
    )
