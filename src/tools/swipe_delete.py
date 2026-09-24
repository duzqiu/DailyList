"""Left-swipe row that reveals a delete button."""

from collections.abc import Callable
from typing import Any

import flet as ft

REVEAL_WIDTH = 72
SNAP_DURATION = 160
FLICK_VELOCITY = 300.0
CLOSE_SLOP = 8.0


def build_swipe_delete_row(
    card: ft.Container, on_delete: Callable[[ft.Event[ft.Container]], Any]
) -> ft.Control:
    """Wrap `card` so it can be swiped left to reveal a delete button.

    The card follows the finger while dragging and snaps open or closed on
    release; swiping right again closes the row, and the todo is only removed
    when the revealed button is clicked.
    """
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
        state["px"] = min(0.0, max(-REVEAL_WIDTH, state["start_px"] + delta))
        render(False)

    def settle(velocity: float) -> None:
        moved = state["px"] - state["start_px"]
        if velocity <= -FLICK_VELOCITY:
            snap(-REVEAL_WIDTH)
        elif velocity >= FLICK_VELOCITY:
            snap(0.0)
        elif state["start_px"] <= -REVEAL_WIDTH / 2:
            snap(0.0 if moved > CLOSE_SLOP else -REVEAL_WIDTH)
        else:
            snap(-REVEAL_WIDTH if state["px"] <= -REVEAL_WIDTH / 2 else 0.0)

    def on_pan_end(e: ft.DragEndEvent) -> None:
        settle(e.velocity.x if e.velocity else 0.0)

    def on_pan_cancel(_: ft.Event[ft.GestureDetector]) -> None:
        settle(0.0)

    delete_button = ft.Container(
        right=0,
        top=0,
        bottom=0,
        width=REVEAL_WIDTH,
        border_radius=ft.BorderRadius.all(10),
        bgcolor="#DC2626",
        alignment=ft.Alignment.CENTER,
        ink=True,
        on_click=on_delete,
        content=ft.Column(
            tight=True,
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.DELETE_OUTLINE, size=18, color="#FFFFFF"),
                ft.Text("删除", size=11, color="#FFFFFF"),
            ],
        ),
    )
    card.size_change_interval = 1
    card.on_size_change = on_size_change
    return ft.GestureDetector(
        content=ft.Stack(
            clip_behavior=ft.ClipBehavior.NONE,
            controls=[
                delete_button,
                card,
            ],
        ),
        on_pan_start=on_pan_start,
        on_pan_update=on_pan_update,
        on_pan_end=on_pan_end,
        on_pan_cancel=on_pan_cancel,
    )
