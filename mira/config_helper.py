import logging
import random

from .helpers.connection import Connection
from .helpers.notifications import Notifications

logger = logging.getLogger(__name__)

async def config_flow_pairing(hass, address, client_id=None, client_name="homeassistant"):
    conn = Connection(hass, address)
    new_client_id = client_id
    if not new_client_id:
        new_client_id = generate_client_id()


    await conn.connect()
    try:
        notifications = Notifications(is_pairing=True)
        client_id_out, client_slot = await conn.pair_client(new_client_id, client_name, notifications)

    finally:
        await conn.disconnect()

    logger.warning(f"Pairing new client id: {client_id_out}, "
          f"client_slot: {client_slot}")

    return client_id_out, client_slot


def generate_client_id():
    max_client_id = (1 << 16) - 1
    return random.randint(10000, max_client_id)
