"""半圆完成率环（数据页用）：一把**由浅到深的刻度弧 + 一个圆点**。

用 `flet_charts` 的官方 `PieChart` 画**上半圈**：扇区加起来正好 180°，起笔落在**九点钟**
（`start_degree_offset = 180` —— fl_chart 的 0° 在三点钟、顺时针为正），顺时针扫到三点钟，
画出来的就是上半圈。下半圈压根没画，所以不必裁剪。

**进度不填色**：整条弧本身就是刻度 —— 切成 `TRACK_SEGMENTS` 小段，每段插一个从
`TRACK_LIGHT` 到 `TRACK_DARK` 的实色，看着就是一条由浅到深的弧。进度由**一个圆点**
指示：圆点走到完成率对应的角度上，颜色取那一档的深浅（所以越靠右越深、圆点也跟着深）。

> 为什么不用 `PieChartSection.gradient`：fl_chart 是按**扇区自己的包围盒**算渐变的，而
> 半圆那一段的包围盒中心在圆心上方半个半径处，渐变会绕着错的地方转。切成小段拼，落在
> 哪一段、什么色都是算得准的。

圆点用 `left`/`top` 摆（弧上某个角度的坐标算出来），所以进度由调用方一步步喂（见
`pages/data.py` 的 `sweep`）：每步挪一点，看着就是「滑过去」而不是「跳过去」。
"""

from __future__ import annotations

import math

import flet as ft
import flet_charts as fch

# 一整圈是 360°，这里只画上半圈。
SWEEP_DEGREES = 180
# 起笔的角度：0° 在三点钟、顺时针为正，所以 180° 就是九点钟 —— 从最左边起画。
START_DEGREE = 180
# 刻度切成几段：越多越顺，太多则控件变大（32 段在百来像素的弧上已经看不出台阶）。
TRACK_SEGMENTS = 32
# 刻度两端的颜色：左边最浅、右边最深（都是天蓝那一族，和 App 的主色系一致）。
TRACK_LIGHT = "#BAE6FD"
TRACK_DARK = "#0369A1"
# 圆点：白边把它从弧上托出来。直径**取环厚**（见 HalfRing.__init__）—— 再大一点它
# 停在弧两端就会探出画布外（两端正好压在画布左右边上）。
DOT_BORDER_WIDTH = 2
DOT_BORDER_COLOR = "#FFFFFF"
# 圆心那块内容离平边的距离：抬起来一点，别贴在环的内沿上。
CENTER_BOTTOM_PAD = 4


def mix_colors(start: str, end: str, amount: float) -> str:
    """在两色之间插一段（`amount` 0 = `start`、1 = `end`）；两色都是 `#RRGGBB`。"""
    amount = max(0.0, min(1.0, amount))
    start_rgb = tuple(int(start[i : i + 2], 16) for i in (1, 3, 5))
    end_rgb = tuple(int(end[i : i + 2], 16) for i in (1, 3, 5))
    blended = (
        round(begin + (finish - begin) * amount)
        for begin, finish in zip(start_rgb, end_rgb)
    )
    return "#" + "".join(f"{value:02X}" for value in blended)


def track_color(fraction: float) -> str:
    """刻度上 `fraction`（0..1）处的颜色 —— 圆点也用它。"""
    return mix_colors(TRACK_LIGHT, TRACK_DARK, fraction)


class HalfRing:
    """半圆刻度弧 + 圆点（＋圆心那块交给调用方的内容）。

    `control` 是整块；进度用 `set_value()` 喂，0..1，不带动画。
    """

    def __init__(
        self, center: ft.Control, size: float, thickness: float
    ) -> None:
        self.size = size
        self.thickness = thickness
        # 圆点直径取环厚：这样它停在弧两端时正好压着画布左右边（圆心离边的距离就是
        # 环厚的一半），不会探出去。
        self.dot_size = thickness
        # 当前圆点停在哪：动画要从它接着走（第一次是 0）。
        self.value = 0.0
        # 刻度：一段一个实色，颜色从浅到深挨着排，合起来正好半圈。
        self._chart = fch.PieChart(
            width=size,
            height=size,
            sections=[
                fch.PieChartSection(
                    value=SWEEP_DEGREES / TRACK_SEGMENTS,
                    radius=thickness,
                    color=track_color(index / (TRACK_SEGMENTS - 1)),
                )
                for index in range(TRACK_SEGMENTS)
            ],
            # 一段挨一段，不留缝：这是一条刻度，断开看着像虚线。
            sections_space=0,
            # 圆孔半径 = 外半径 − 环厚，刻度正好贴着画布边。
            center_space_radius=size / 2 - thickness,
            # 圆孔是空的（透明）：底下没有底色可填，露出来的就是卡片的灰。
            center_space_color="#00000000",
            start_degree_offset=START_DEGREE,
            # 进度由圆点表示，弧本身不动，客户端插值没有意义。
            animation=0,
        )
        self._dot = ft.Container(
            width=self.dot_size,
            height=self.dot_size,
            border_radius=ft.BorderRadius.all(self.dot_size / 2),
            border=ft.Border.all(DOT_BORDER_WIDTH, DOT_BORDER_COLOR),
            bgcolor=track_color(0.0),
        )
        # 画布按**定位子**摆进 Stack：只给 left/top，它就拿得到自己的整块画布（非定位
        # 子会被 Stack 的高度约束住、压成半圆饼）。Stack 自己只有半格高，下半块本来
        # 就没内容，露出去也无所谓。
        self.control = ft.Stack(
            width=size,
            height=size / 2,
            controls=[
                ft.Container(
                    left=0,
                    top=0,
                    width=size,
                    height=size,
                    content=self._chart,
                ),
                ft.Container(
                    # 左右都顶到边、贴着平边居中：圆心那块就是「半圆的中间」。
                    left=0,
                    right=0,
                    bottom=CENTER_BOTTOM_PAD,
                    alignment=ft.Alignment.BOTTOM_CENTER,
                    content=center,
                ),
                # 圆点最后摆，压在弧上面（见 set_value）。
                self._dot,
            ],
        )
        self.set_value(0.0)

    def set_value(self, fraction: float) -> None:
        """把圆点挪到 `fraction`（0..1）处，颜色取那一档的深浅。"""
        self.value = max(0.0, min(1.0, fraction))
        # 角度：0 在九点钟、1 在三点钟 —— 顺时针正好走完上半圈。
        angle = math.radians(SWEEP_DEGREES * (1 - self.value))
        # 弧的中线：圆点踩在环的正中间，不偏内也不偏外。
        radius = self.size / 2 - self.thickness / 2
        center_x = self.size / 2
        # 圆心落在这个盒子的下边线上（盒子只有半格高）。
        center_y = self.size / 2
        half_dot = self.dot_size / 2
        self._dot.left = center_x + radius * math.cos(angle) - half_dot
        self._dot.top = center_y - radius * math.sin(angle) - half_dot
        self._dot.bgcolor = track_color(self.value)


def build_half_ring(
    center: ft.Control, size: float, thickness: float
) -> HalfRing:
    """一枚半圆刻度弧：画布边长 `size`、弧厚 `thickness`，圆心摆 `center`。"""
    return HalfRing(center, size, thickness)
