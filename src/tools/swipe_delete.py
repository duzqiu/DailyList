"""Left-swipe row that reveals its actions - 编辑 and 删除."""

from collections.abc import Callable
from typing import Any

import flet as ft

# One action button; the swipe opens as wide as the number of actions needs.
BUTTON_WIDTH = 72
SNAP_DURATION = 160
FLICK_VELOCITY = 300.0
CLOSE_SLOP = 8.0
ACTION_RADIUS = 10


def build_swipe_delete_row(
    card: ft.Container,
    on_delete: Callable[[ft.Event[ft.Container]], Any],
    on_edit: Callable[[ft.Event[ft.Container]], Any] | None = None,
) -> ft.Control:
    """Wrap `card` so it can be swiped left to reveal 编辑 and/or 删除.

    The card follows the finger while dragging and snaps open or closed on
    release; swiping right again closes the row, and nothing happens to the row
    until one of the revealed buttons is clicked. `on_edit` is optional so the
    pages that have no editing UI keep the single 删除 button.
    """
    actions: list[tuple[str, str, str, Callable]] = []
    if on_edit is not None:
        actions.append(("编辑", ft.Icons.EDIT_OUTLINED, "#0EA5E9", on_edit))
    actions.append(("删除", ft.Icons.DELETE_OUTLINE, "#DC2626", on_delete))
    reveal = BUTTON_WIDTH * len(actions)
    state: dict[str, float] = {"px": 0.0, "start_px": 0.0, "width": 0.0}

    def render(animate: bool) -> None:
        width = state["width"]
        card.offset = ft.Offset(state["px"] / width if width else 0.0, 0)
        card.animate_offset = (
            ft.Animation(SNAP_DURATION, ft.AnimationCurve.EASE_OUT)
            if animate
            else None
        )
        card.update()

    def snap(px: float) -> None:
        state["px"] = px
        render(True)

    def on_size_change(e: ft.LayoutSizeChangeEvent) -> None:
        state["width"] = e.width
        if state["px"]:
            render(False)

    def on_pan_start(_: ft.DragStartEvent) -> None:
        state["start_px"] = state["px"]

    def on_pan_update(e: ft.DragUpdateEvent) -> None:
        delta = e.local_delta.x if e.local_delta else 0.0
        state["px"] = min(0.0, max(-reveal, state["start_px"] + delta))
        render(False)

    def settle(velocity: float) -> None:
        moved = state["px"] - state["start_px"]
        if velocity <= -FLICK_VELOCITY:
            snap(-reveal)
        elif velocity >= FLICK_VELOCITY:
            snap(0.0)
        elif state["start_px"] <= -reveal / 2:
            snap(0.0 if moved > CLOSE_SLOP else -reveal)
        else:
            snap(-reveal if state["px"] <= -reveal / 2 else 0.0)

    def on_pan_end(e: ft.DragEndEvent) -> None:
        settle(e.velocity.x if e.velocity else 0.0)

    def on_pan_cancel(_: ft.Event[ft.GestureDetector]) -> None:
        settle(0.0)

    # The buttons sit at the right edge: the last one (删除) flush with it, the
    # ones before it stacked to its left, in the order they are swiped open.
    buttons = [
        ft.Container(
            right=BUTTON_WIDTH * (len(actions) - 1 - index),
            top=0,
            bottom=0,
            width=BUTTON_WIDTH,
            border_radius=ft.BorderRadius.all(ACTION_RADIUS),
            bgcolor=color,
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=handler,
            content=ft.Column(
                tight=True,
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, size=18, color="#FFFFFF"),
                    ft.Text(label, size=11, color="#FFFFFF"),
                ],
            ),
        )
        for index, (label, icon, color, handler) in enumerate(actions)
    ]
    card.size_change_interval = 1
    card.on_size_change = on_size_change
    return ft.GestureDetector(
        content=ft.Stack(
            clip_behavior=ft.ClipBehavior.NONE,
            controls=[*buttons, card],
        ),
        on_pan_start=on_pan_start,
        on_pan_update=on_pan_update,
        on_pan_end=on_pan_end,
        on_pan_cancel=on_pan_cancel,
    )
