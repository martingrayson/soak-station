import random
import threading

from . import Connection, NotificationsBase


class PairingNotifications(NotificationsBase):
    def __init__(self, event):
        self.client_slot = None
        self._event = event

    def success_or_failure(self, client_slot, status):
        self.client_slot = status
        self._event.set()


def pair_client(address: str, client_name: str, client_id: int = None) -> tuple[int, int]:
    """Pair a new client to a Mira device and return the assigned client slot."""
    if not client_id:
        max_client_id = (1 << 16) - 1
        client_id = random.randint(10000, max_client_id)

    event = threading.Event()
    notifications = PairingNotifications(event)

    with Connection(address) as conn:
        conn.subscribe(notifications)
        conn.pair_client(client_id, client_name)
        event.wait()

    if notifications.client_slot is None:
        raise RuntimeError("Pairing failed or timed out")

    return client_id, notifications.client_slot
