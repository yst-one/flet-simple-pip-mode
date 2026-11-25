"""Flet port of the official simple_pip_mode Flutter example.

Layout mirrors upstream example/lib/main.dart:
- AppBar title "PiP Plugin example app"
- centered body: PiP Available / Activated, aspect ratio, auto-enter switch,
  enter-PiP button, divider, "PIP Actions:", actions layout, simulated player
- pip_child is a separate centered "Pip Mode" screen

Covers every upstream API: isPipAvailable / isAutoPipAvailable /
isPipActivated, enterPipMode, setAutoPipMode, setPipActionsLayout (all 5),
setIsPlaying, onPipEntered / onPipExited / onPipAction (7 actions), and
PipWidget child / pip_child.

Two verification-only extras, kept visually subtle: a small callback log at
the bottom and a live random number inside PiP (to show real-time repaint).
"""

from __future__ import annotations

import asyncio
import random

import flet as ft

from flet_simple_pip_mode import (
    PipAction,
    PipActionsLayout,
    PipWidget,
    SimplePipMode,
)

ASPECT_RATIOS: dict[str, tuple[int, int]] = {
    "1:1": (1, 1),
    "2:3": (2, 3),
    "3:2": (3, 2),
    "16:9": (16, 9),
    "9:16": (9, 16),
}

ACTION_RESPONSES = {
    PipAction.PLAY: "Playing",
    PipAction.PAUSE: "Paused",
    PipAction.LIVE: "Go to live view",
    PipAction.NEXT: "Next",
    PipAction.PREVIOUS: "Previous",
    PipAction.REWIND: "Rewind",
    PipAction.FORWARD: "Forward",
}


class ExampleHub:
    """Carries service callbacks into declarative component state."""

    MAX_LOGS = 12

    def __init__(self) -> None:
        self.value = "等待操作"
        self.logs: list[str] = [self.value]
        self.in_pip = False
        self.pip_available = False
        self.auto_pip_available = False
        self.activated = False
        self.is_playing = True
        self.action_response = ""
        self._listeners = []

    def subscribe(self, listener):
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def _record(self, value: str) -> None:
        self.value = value
        self.logs = [value] + self.logs[: self.MAX_LOGS - 1]

    def set(self, value: str) -> None:
        self._record(value)
        self._notify()

    def set_pip(self, active: bool, value: str | None = None) -> None:
        self.in_pip = active
        self.activated = active
        if value is not None:
            self._record(value)
        self._notify()

    def set_capabilities(self, available, auto_available, activated) -> None:
        self.pip_available = bool(available)
        self.auto_pip_available = bool(auto_available)
        self.activated = bool(activated)
        self._notify()

    def set_action(self, action: PipAction) -> None:
        self.action_response = ACTION_RESPONSES.get(action, str(action))
        if action == PipAction.PLAY:
            self.is_playing = True
        elif action == PipAction.PAUSE:
            self.is_playing = False
        self._record(f"回调：PiP 动作 {action.value} → {self.action_response}")
        self._notify()

    def set_playing(self, playing: bool) -> None:
        self.is_playing = playing
        self.action_response = ""
        self._record(f"模拟播放器：{'播放' if playing else '暂停'}")
        self._notify()

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener(self)


@ft.component
def ExampleApp(page: ft.Page, pip: SimplePipMode, hub: ExampleHub):
    status, set_status = ft.use_state(hub.value)
    logs, set_logs = ft.use_state(hub.logs)
    in_pip, set_in_pip = ft.use_state(hub.in_pip)
    pip_available, set_pip_available = ft.use_state(hub.pip_available)
    auto_available, set_auto_available = ft.use_state(hub.auto_pip_available)
    activated, set_activated = ft.use_state(hub.activated)
    aspect_key, set_aspect_key = ft.use_state("16:9")
    auto_switch, set_auto_switch = ft.use_state(False)
    layout_value, set_layout_value = ft.use_state(PipActionsLayout.NONE.value)
    is_playing, set_is_playing = ft.use_state(hub.is_playing)
    action_response, set_action_response = ft.use_state(hub.action_response)
    tick, set_tick = ft.use_state(0)

    def mount():
        def on_hub(h):
            set_status(h.value)
            set_logs(h.logs)
            set_in_pip(h.in_pip)
            set_pip_available(h.pip_available)
            set_auto_available(h.auto_pip_available)
            set_activated(h.activated)
            set_is_playing(h.is_playing)
            set_action_response(h.action_response)

        unsubscribe = hub.subscribe(on_hub)

        async def detect():
            available = await pip.is_pip_available()
            auto = await pip.is_auto_pip_available()
            active = await pip.is_pip_activated()
            hub.set_capabilities(available, auto, active)

        page.run_task(detect)

        stop = {"flag": False}

        async def ticker():
            while not stop["flag"]:
                await asyncio.sleep(0.5)
                set_tick(random.randint(0, 999999))

        page.run_task(ticker)
        return lambda: (stop.update(flag=True), unsubscribe())

    ft.use_effect(mount, [])

    async def enter_pip():
        try:
            # Push active=True immediately. The Dart service waits for the
            # pip_child frame to be painted before asking the system for PiP,
            # so no hard-coded sleep is needed here.
            hub.set_pip(True, "切换内容：画中画布局")
            page.update()
            ok = await pip.enter_pip_mode(
                aspect_ratio=ASPECT_RATIOS[aspect_key],
                auto_enter=auto_switch,
                seamless_resize=auto_switch,
            )
            hub.set(f"进入 PiP 请求: {ok}")
        except Exception as exc:  # noqa: BLE001 - 示例需要展示异常原因
            hub.set_pip(False, f"进入 PiP 异常: {exc!r}")

    async def apply_auto(aspect, auto, seamless):
        try:
            ok = await pip.set_auto_pip_mode(
                aspect_ratio=aspect,
                auto_enter=auto,
                seamless_resize=seamless,
            )
            hub.set(f"自动 PiP 设置: {ok}（aspect={aspect}, auto={auto}）")
        except Exception as exc:  # noqa: BLE001
            hub.set(f"自动 PiP 异常: {exc!r}")

    async def apply_layout(layout: PipActionsLayout):
        try:
            ok = await pip.set_pip_actions_layout(layout)
            hub.set(f"动作布局: {layout.value} → {ok}")
        except Exception as exc:  # noqa: BLE001
            hub.set(f"动作布局异常: {exc!r}")

    async def apply_playing(playing: bool):
        try:
            ok = await pip.set_is_playing(playing)
            hub.set(f"播放状态设置: {playing} → {ok}")
        except Exception as exc:  # noqa: BLE001
            hub.set(f"播放状态异常: {exc!r}")

    def on_enter():
        # enter_pip is a real coroutine function, so run_task accepts it.
        page.run_task(enter_pip)

    # Flet 1.1.x _trigger_event awaits a handler's returned coroutine, so async
    # handlers can await directly. Do NOT wrap them in page.run_task(lambda: ...).
    async def on_aspect_select():
        new_key = aspect_dd.value
        if not new_key or new_key == aspect_key:
            return
        set_aspect_key(new_key)
        hub.set(f"宽高比: {new_key}")
        await apply_auto(ASPECT_RATIOS[new_key], auto_switch, auto_switch)

    async def on_auto_change():
        new_value = bool(auto_sw.value)
        set_auto_switch(new_value)
        hub.set(f"自动进入: {new_value}")
        await apply_auto(ASPECT_RATIOS[aspect_key], new_value, new_value)

    async def on_layout_select():
        new_value = layout_dd.value
        if not new_value or new_value == layout_value:
            return
        set_layout_value(new_value)
        layout = PipActionsLayout(new_value)
        hub.set_playing(True)
        await apply_layout(layout)

    async def on_player():
        new_value = not is_playing
        hub.set_playing(new_value)
        await apply_playing(new_value)

    aspect_dd = ft.Dropdown(
        value=aspect_key,
        options=[ft.DropdownOption(key=k, text=k) for k in ASPECT_RATIOS],
        label="Aspect ratio",
        width=170,
        on_select=on_aspect_select,
    )
    auto_sw = ft.Switch(
        value=auto_switch,
        label="Auto Enter (Android S)",
        disabled=not auto_available,
        on_change=on_auto_change,
    )
    layout_dd = ft.Dropdown(
        value=layout_value,
        options=[
            ft.DropdownOption(key=layout.value, text=layout.name)
            for layout in PipActionsLayout
        ],
        label="Current actions layout",
        width=240,
        on_select=on_layout_select,
    )

    # Upstream uses a check/close Icon for each capability row.
    pip_available_row = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            ft.Text("PiP Available: ", size=15),
            ft.Icon(
                ft.Icons.CHECK if pip_available else ft.Icons.CLOSE,
                size=18,
                color=ft.Colors.GREEN_700 if pip_available else ft.Colors.RED_700,
                semantics_label="PiP Available check",
            ),
        ],
    )
    activated_row = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            ft.Text("PiP Activated: ", size=15),
            ft.Icon(
                ft.Icons.CHECK if activated else ft.Icons.CLOSE,
                size=18,
                color=ft.Colors.GREEN_700 if activated else ft.Colors.RED_700,
                semantics_label="PiP Activated check",
            ),
        ],
    )

    normal_controls = [
        ft.Text("PiP Plugin example app", size=20, weight=ft.FontWeight.BOLD),
        pip_available_row,
        activated_row,
        ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[ft.Text("Aspect ratio: ", size=15), aspect_dd],
        ),
        auto_sw,
        ft.IconButton(
            icon=ft.Icons.PICTURE_IN_PICTURE,
            tooltip="进入 PiP",
            on_click=on_enter,
        ),
        ft.Divider(thickness=1),
        ft.Text("PIP Actions:", size=15, weight=ft.FontWeight.BOLD),
        ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[ft.Text("Current actions layout: ", size=14), layout_dd],
        ),
    ]

    # Upstream shows the simulated player only for non-none layouts.
    if layout_value != PipActionsLayout.NONE.value:
        normal_controls.extend(
            [
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Text("Simulated player: ", size=14),
                        ft.IconButton(
                            icon=(
                                ft.Icons.PLAY_ARROW
                                if not is_playing
                                else ft.Icons.PAUSE
                            ),
                            tooltip="切换模拟播放状态",
                            on_click=on_player,
                        ),
                    ],
                ),
                ft.Text(
                    "Obs.: Tap the simulated player button to see the PIP actions "
                    "update in PIP mode; tapping PIP actions there reflects here too.",
                    size=10,
                    text_align=ft.TextAlign.CENTER,
                    color=ft.Colors.BLUE_GREY_600,
                ),
            ]
        )

    # Verification-only: a small log strip at the bottom (subtle, scroll-free).
    normal_controls.extend(
        [
            ft.Divider(thickness=1),
            ft.Text(status, size=11, color=ft.Colors.PURPLE_800),
            ft.Text(
                "\n".join(logs[:4]),
                size=10,
                color=ft.Colors.BLUE_GREY_600,
                text_align=ft.TextAlign.CENTER,
            ),
        ]
    )

    # PiP screen: mirrors upstream pipChild (title "Pip Mode" + centered state).
    pip_controls = [
        ft.Text("Pip Mode", size=18, weight=ft.FontWeight.BOLD),
        ft.Text("PiP activated", size=14),
    ]
    if layout_value != PipActionsLayout.NONE.value:
        pip_controls.extend(
            [
                ft.Icon(ft.Icons.PAUSE if is_playing else ft.Icons.PLAY_ARROW, size=22),
                ft.Text(action_response, size=12),
            ]
        )
    pip_controls.extend(
        [
            ft.Text(
                f"随机数: {tick:06d}",
                size=12,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(status, size=10),
        ]
    )

    pip_view = PipWidget(
        active=in_pip,
        child=ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=ft.Padding.all(16),
                content=ft.Column(
                    expand=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=6,
                    scroll=ft.ScrollMode.AUTO,
                    controls=normal_controls,
                ),
            ),
        ),
        pip_child=ft.Container(
            expand=True,
            bgcolor=ft.Colors.GREEN_300,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
                controls=pip_controls,
            ),
        ),
    )

    # PiP 期间只保留 pip_child，避免系统截取旧表头；退出后完整界面自动恢复。
    return pip_view


def main(page: ft.Page) -> None:
    page.title = "PiP Plugin example app"
    hub = ExampleHub()
    pip = SimplePipMode(
        on_pip_entered=lambda e: hub.set_pip(True, "回调：已进入 PiP"),
        on_pip_exited=lambda e: hub.set_pip(False, "回调：已退出 PiP"),
        on_pip_action=lambda e: hub.set_action(e.action),
    )
    page.render(lambda: ExampleApp(page, pip, hub))


if __name__ == "__main__":
    ft.run(main)
