import random
import threading
from .helpers.connection import Connection

def pair_client(client_id, client_name, address, hass):
    with Connection(hass, address) as conn:

        event = threading.Event()
        # notifications = Notifications(event, is_pairing=True)
        # conn.subscribe(notifications)

        new_client_id = client_id
        if not new_client_id:
            max_client_id = (1 << 16) - 1
            new_client_id = random.randint(10000, max_client_id)

        print(f"Pairing new client id: {new_client_id}, "
              f"name: {client_name}")

        conn.pair_client(new_client_id, client_name)
        event.wait()
        event.clear()