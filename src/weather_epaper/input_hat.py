from __future__ import annotations

import logging
from contextlib import AbstractContextManager
from queue import SimpleQueue
from types import TracebackType
from typing import Any

from weather_epaper.config import Settings
from weather_epaper.ui.navigation import KeyId

logger = logging.getLogger(__name__)


class HatButtons(AbstractContextManager["HatButtons"]):
    """Register gpiozero buttons; enqueue KeyId on press. No hardware in mock mode."""

    def __init__(self, settings: Settings, queue: SimpleQueue[KeyId]) -> None:
        self._settings = settings
        self._queue = queue
        self._buttons: list[Any] = []

    def __enter__(self) -> HatButtons:
        if self._settings.mock:
            logger.info("Mock mode: HAT keys disabled")
            return self
        try:
            from gpiozero import Button
        except ImportError:
            logger.warning("gpiozero not installed; HAT keys disabled")
            return self

        pins = (
            (KeyId.K1, self._settings.key1_bcm),
            (KeyId.K2, self._settings.key2_bcm),
            (KeyId.K3, self._settings.key3_bcm),
            (KeyId.K4, self._settings.key4_bcm),
        )

        for kid, bcm in pins:
            try:
                b = Button(bcm, pull_up=True, bounce_time=0.05)

                def on_press(k: KeyId = kid) -> None:
                    self._queue.put(k)

                b.when_pressed = on_press
                self._buttons.append(b)
                logger.info("HAT key %s on GPIO %s", kid.name, bcm)
            except Exception:
                logger.exception("Failed to register key %s on GPIO %s", kid.name, bcm)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        for b in self._buttons:
            try:
                b.close()
            except Exception:
                logger.exception("Error closing button")
        self._buttons.clear()
