"""Flet service wrapping the Flutter ``simple_pip_mode`` plugin (Android only)."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import flet as ft
from flet.controls.base_control import control
from flet.controls.control_event import Event, EventHandler
from flet.controls.services.service import Service

__all__ = [
    "PipAction",
    "PipActionsLayout",
    "PipActionEvent",
    "PipStateEvent",
    "SimplePipMode",
]


class PipAction(Enum):
    """Actions shown in the PiP overlay."""

    PLAY = "play"
    PAUSE = "pause"
    PREVIOUS = "previous"
    NEXT = "next"
    LIVE = "live"
    REWIND = "rewind"
    FORWARD = "forward"

    @classmethod
    def _missing_(cls, value):
        # Dart sends upper-case Enum.name by default; accept it as a fallback.
        if isinstance(value, str):
            lowered = value.lower()
            for member in cls:
                if member.value == lowered:
                    return member
        return None


class PipActionsLayout(Enum):
    """Preset action layouts for the PiP overlay."""

    NONE = "none"
    MEDIA = "media"
    MEDIA_ONLY_PAUSE = "mediaOnlyPause"
    MEDIA_LIVE = "mediaLive"
    MEDIA_WITH_SEEK_10 = "mediaWithSeek10"


@dataclass
class PipStateEvent(Event["SimplePipMode"]):
    """Fired when the app enters or exits PiP mode."""

    active: bool


@dataclass
class PipActionEvent(Event["SimplePipMode"]):
    """Fired when the user taps a PiP action button."""

    action: PipAction


@control("SimplePipMode")
class SimplePipMode(Service):
    """Android Picture-in-Picture controller.

    Add one instance to the page (services auto-register), then call its
    async methods. All methods are safe to call on non-Android platforms:
    unsupported features return ``False`` instead of raising.
    """

    on_pip_entered: Optional[EventHandler[PipStateEvent]] = None
    """Fired when the app enters PiP mode."""

    on_pip_exited: Optional[EventHandler[PipStateEvent]] = None
    """Fired when the app exits PiP mode."""

    on_pip_action: Optional[EventHandler[PipActionEvent]] = None
    """Fired when the user taps an action in the PiP overlay."""

    async def is_pip_available(self) -> bool:
        """Whether the device supports PiP (Android O / API 26+)."""
        return bool(await self._invoke_method("is_pip_available"))

    async def is_auto_pip_available(self) -> bool:
        """Whether auto-enter PiP is supported (Android 12 / API 31+)."""
        return bool(await self._invoke_method("is_auto_pip_available"))

    async def is_pip_activated(self) -> bool:
        """Whether the app is currently in PiP mode."""
        return bool(await self._invoke_method("is_pip_activated"))

    async def enter_pip_mode(
        self,
        aspect_ratio: tuple[int, int] = (16, 9),
        auto_enter: bool = False,
        seamless_resize: bool = False,
    ) -> bool:
        """Request PiP mode.

        Args:
            aspect_ratio: PiP window width:height ratio.
            auto_enter: Enter PiP automatically when the user leaves the app
                (API 31+).
            seamless_resize: Resize without black bars.
        """
        return bool(
            await self._invoke_method(
                "enter_pip_mode",
                {
                    "aspect_ratio": list(aspect_ratio),
                    "auto_enter": auto_enter,
                    "seamless_resize": seamless_resize,
                },
            )
        )

    async def set_auto_pip_mode(
        self,
        aspect_ratio: tuple[int, int] = (16, 9),
        seamless_resize: bool = False,
        auto_enter: bool = True,
    ) -> bool:
        """Configure automatic PiP on leaving the app (API 31+)."""
        return bool(
            await self._invoke_method(
                "set_auto_pip_mode",
                {
                    "aspect_ratio": list(aspect_ratio),
                    "auto_enter": auto_enter,
                    "seamless_resize": seamless_resize,
                },
            )
        )

    async def set_pip_actions_layout(self, layout: PipActionsLayout) -> bool:
        """Set the action buttons preset shown in the PiP overlay."""
        return bool(
            await self._invoke_method(
                "set_pip_actions_layout", {"layout": layout.value}
            )
        )

    async def set_is_playing(self, is_playing: bool) -> bool:
        """Update the play/pause action icon after an external player change."""
        return bool(
            await self._invoke_method(
                "set_is_playing", {"is_playing": is_playing}
            )
        )
