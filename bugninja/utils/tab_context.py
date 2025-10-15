from __future__ import annotations

from typing import Callable, List


class TabContext:
    """
    Lightweight tab context to track the active tab and notify listeners on changes.
    """

    def __init__(self) -> None:
        self.active_tab_id: int = 0
        self._listeners: List[Callable[[int], None]] = []

    def set_active(self, tab_id: int) -> None:
        if tab_id == self.active_tab_id:
            return

        old_tab_id = self.active_tab_id
        self.active_tab_id = tab_id

        from bugninja.utils.logging_config import logger

        logger.bugninja_log(f"📋 TabContext: Active tab changed from {old_tab_id} to {tab_id}")

        # Notify listeners with enhanced error handling
        for cb in list(self._listeners):
            try:
                cb(tab_id)
            except Exception as e:
                logger.warning(f"⚠️ TabContext listener failed: {e}")
                # Continue with other listeners despite failures

    def on_change(self, cb: Callable[[int], None]) -> None:
        self._listeners.append(cb)

    def remove_listener(self, cb: Callable[[int], None]) -> None:
        try:
            self._listeners.remove(cb)
        except ValueError:
            pass

    def __len__(self) -> int:
        """Return the number of available tabs.

        Note: This is a compatibility method for code that expects tabs to be a sequence.
        We return 1 as a fallback since we always have at least one active tab.
        """
        return 1  # Fallback: assume at least one tab exists
