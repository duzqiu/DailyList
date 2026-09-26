import flet.testing as ftt


async def test_navigation(flet_app: ftt.FletTestApp):
    """The bottom menu switches between the Chinese-labeled pages."""
    tester = flet_app.tester

    await tester.pump_and_settle()

    assert (await tester.find_by_text("待办")).count == 2
    assert (await tester.find_by_text("日历")).count == 1
    assert (await tester.find_by_text("设置")).count == 1

    await tester.tap(await tester.find_by_key("calendar-tab"))
    await tester.pump_and_settle()

    assert (await tester.find_by_text("日历页面")).count == 1

    await tester.tap(await tester.find_by_key("settings-tab"))
    await tester.pump_and_settle()

    assert (await tester.find_by_text("设置页面")).count == 1
