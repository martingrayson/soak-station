import threading
from . import Connection, NotificationsBase
import logging

_LOGGER = logging.getLogger(__name__)


def get_device_state(address, client_id, client_slot):
    """Fetch the current device state from the shower unit."""
    state = {}

    with Connection(address, client_id, client_slot) as conn:
        event = threading.Event()

        class Listener(NotificationsBase):
            def device_state(
                self, client_slot_inner, timer_state, target_temperature,
                actual_temperature, outlet_state_1, outlet_state_2,
                remaining_seconds, successful_update_command_counter
            ):
                state.update({
                    "outlet1": outlet_state_1,
                    "outlet2": outlet_state_2,
                    "target_temp": target_temperature,
                    "actual_temp": actual_temperature,
                    "timer_state": timer_state,
                    "remaining_seconds": remaining_seconds
                })
                event.set()

        listener = Listener()
        conn.subscribe(listener)
        conn.request_device_state()
        event.wait(timeout=5)

    if not state:
        _LOGGER.warning("Timeout or failure retrieving device state from %s", address)
    return state


def update_outlet_state_from_device(address, client_id, client_slot, outlet_num=1):
    """Get the current state of a specific outlet (1 or 2)."""
    state = get_device_state(address, client_id, client_slot)
    if not state:
        return None

    return state.get(f"outlet{outlet_num}", None)
