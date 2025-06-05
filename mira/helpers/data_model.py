from typing import Callable

import logging
_LOGGER = logging.getLogger(__name__)

class SoakStationData:
    def __init__(self):
        self.slots = []
        self.client_slot = None
        self.outlet_1_on = None
        self.outlet_2_on = None

        self.target_temp = None
        self.actual_temp = None

        self.timer_state = None
        self.remaining_seconds = None
        self.subscribers: list[Callable[[], None]] = []

    def update_state(
        self,
        *,
        slots=None,
        client_slot=None,
        outlet_1_on=None,
        outlet_2_on=None,
        target_temp=None,
        actual_temp=None,
        timer_state=None,
        remaining_seconds=None
    ):
        # _LOGGER.warning(f"Updating state!")

        # Update each field only if provided (not None)
        if slots is not None:
            self.slots = slots
        if client_slot is not None:
            self.client_slot = client_slot
        if outlet_1_on is not None:
            self.outlet_1_on = outlet_1_on
        if outlet_2_on is not None:
            self.outlet_2_on = outlet_2_on
        if target_temp is not None:
            self.target_temp = target_temp
        if actual_temp is not None:
            self.actual_temp = actual_temp
        if timer_state is not None:
            self.timer_state = timer_state
        if remaining_seconds is not None:
            self.remaining_seconds = remaining_seconds

        # Notify subscribers
        for callback in self.subscribers:
            callback()

    def subscribe(self, callback: Callable[[], None]):
        self.subscribers.append(callback)