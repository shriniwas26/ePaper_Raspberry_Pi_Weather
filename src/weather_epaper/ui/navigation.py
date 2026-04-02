from __future__ import annotations

import logging
import subprocess
from enum import Enum, auto

from PIL import Image

from weather_epaper.ui.screens import RenderContext, ScreenId, render_screen

logger = logging.getLogger(__name__)

_SCREEN_ORDER: tuple[ScreenId, ...] = (
    ScreenId.WEATHER,
    ScreenId.SYSTEM,
    ScreenId.RESTART,
)


class KeyId(Enum):
    K1 = auto()
    K2 = auto()
    K3 = auto()
    K4 = auto()


class ScreenManager:
    """HAT key navigation and two-step reboot confirm on Restart screen."""

    def __init__(self) -> None:
        self.active = ScreenId.WEATHER
        self.reboot_armed = False

    def _idx(self) -> int:
        return _SCREEN_ORDER.index(self.active)

    def handle_key(self, key: KeyId) -> tuple[bool, bool]:
        """Handle physical key. Returns (should_redraw, reboot_command_sent)."""
        if key is KeyId.K1:
            self._cancel_reboot_if_on_restart()
            self.active = _SCREEN_ORDER[(self._idx() - 1) % len(_SCREEN_ORDER)]
            return True, False
        if key is KeyId.K2:
            self._cancel_reboot_if_on_restart()
            self.active = _SCREEN_ORDER[(self._idx() + 1) % len(_SCREEN_ORDER)]
            return True, False
        if key is KeyId.K3:
            self._cancel_reboot_if_on_restart()
            self.active = ScreenId.WEATHER
            return True, False
        if key is KeyId.K4:
            if self.active is ScreenId.RESTART:
                if self.reboot_armed:
                    self._request_reboot()
                    return True, True
                self.reboot_armed = True
                return True, False
            return False, False
        return False, False

    def _cancel_reboot_if_on_restart(self) -> None:
        if self.active is ScreenId.RESTART:
            self.reboot_armed = False

    def _request_reboot(self) -> None:
        logger.warning("Reboot confirmed (K4 x2 on restart screen); calling systemctl reboot")
        try:
            result = subprocess.run(
                ["sudo", "-n", "systemctl", "reboot"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.error(
                    "systemctl reboot failed (exit %s): %s",
                    result.returncode,
                    (result.stderr or result.stdout or "").strip(),
                )
        except subprocess.TimeoutExpired:
            logger.exception("systemctl reboot timed out")
        except OSError:
            logger.exception("Could not execute systemctl reboot")

    def render(self, ctx: RenderContext) -> Image.Image:
        full_ctx = RenderContext(
            settings=ctx.settings,
            weather=ctx.weather,
            reboot_armed=self.reboot_armed,
        )
        return render_screen(self.active, full_ctx)
