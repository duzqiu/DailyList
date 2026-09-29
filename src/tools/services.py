"""页面级 Service 的统一注册（剪贴板、文件选择器都走它）。

Flet 里 `ft.Service`（`Clipboard`、`FilePicker` 这些都是）跟普通控件不一样：它得**注册
到页面上**，客户端才会为它建一个服务绑定。注册只有一条路 —— 注册表的
`register_service()`：它会把新服务推给客户端（或随页面一起发出去）。

两个踩过的坑：

1. **`page.services.append()` 不算注册**。`page.services` 拿的是根 `View` 上那个
   **普通 list**（`View().services`，连 `register_service` 方法都没有），往里 append
   只是把一个对象塞进清单，客户端那边什么也没发生。之后调这个服务的方法
   （`clipboard.set()`）就会一直等客户端回话，10 秒后抛：

       TimeoutException: Timeout waiting for invoke method listener for Clipboard(xxx).set

2. **服务在构建阶段构造**（不是事件回调里）时，往往没有页面上下文，框架的「构造即
   注册」帮不上忙 —— 得显式注册。

所以统一走 `ensure_service()`：注册表里有就复用，没有就建一个并注册上去。
"""

from typing import TypeVar

import flet as ft

T = TypeVar("T", bound=ft.Service)


def _registry(page: ft.Page):
    """页面上的服务注册表；拿不到就返回 None（旧版 Flet 没有它）。"""
    return getattr(page, "_services", None)


def register_app_services(page: ft.Page) -> None:
    """应用启动时（页面**首次发给客户端之前**）把要用的 Service 都注册好。

    **这是唯一稳妥的时机。** 服务注册到页面上，只有两条路能到达客户端：随页面首次
    发出，或者注册表自己推送（`register_service()` 里那段 `__internal_update()`）。

    而那段推送走不到：注册表是 `Page` 的一个字段、并不挂在控件树上，它的 `parent`
    恒为 `None`，函数会在 `if self.parent is None: return` 那里直接返回 —— 于是新增
    的服务只能等「随页面发出」。设置页这类二级页构建时，页面**早就发过了**，那时
    注册客户端永远收不到；之后调用它的方法就是干等 10 秒然后抛：

        TimeoutException: Timeout waiting for invoke method listener for Clipboard(xxx).set

    所以放到 `main()` 里、`build_navigation()` 之前注册 —— 服务会随首个页面一起
    送到客户端。各页面再通过 `ensure_service()` 取（取到的就是这里注册的那个）。
    """
    for service_type in (ft.Clipboard, ft.FilePicker):
        ensure_service(page, service_type)


def ensure_service(page: ft.Page, service_type: type[T]) -> T:
    """取页面上的某个 Service；没有就建一个并注册。

    `service_type` 得能无参构造（`ft.Clipboard`、`ft.FilePicker` 都是）。

    正常用法是在 `main()` 里先 `register_app_services()`（见上），页面里只负责取。
    在页面构建阶段临时补一个也能跑，但那个服务到不了客户端（原因见上）。
    """
    registry = _registry(page)
    if registry is not None:
        existing = next(
            (
                item
                for item in registry._services
                if isinstance(item, service_type)
            ),
            None,
        )
        if existing is not None:
            return existing

    service = service_type()
    # 构造时若正好有页面上下文，框架已经替我们注册过了，别再塞第二次。
    if registry is not None and not any(
        item is service for item in registry._services
    ):
        registry.register_service(service)
    return service
