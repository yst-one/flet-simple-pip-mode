"""Widget that switches its content according to PiP mode."""

from __future__ import annotations

from typing import Optional

import flet as ft
from flet.controls.base_control import control

__all__ = ["PipWidget"]


@control("PipWidget")
class PipWidget(ft.LayoutControl):
    """Shows ``child`` normally and ``pip_child`` while in PiP mode.

    Requires a ``SimplePipMode`` service instance on the page so that the
    native PiP callbacks are wired up.
    """

    active: bool = False
    """Whether to show ``pip_child`` instead of ``child``.

    Set this from your PiP callbacks (or before calling ``enter_pip_mode``)
    so the Flutter side swaps content before the system takes the PiP snapshot.
    """

    child: Optional[ft.Control] = None
    """Content displayed outside PiP mode."""

    pip_child: Optional[ft.Control] = None
    """Content displayed inside PiP mode; defaults to ``child``."""
