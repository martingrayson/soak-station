import logging
import random
from .helpers.connection import Connection

logger = logging.getLogger(__name__)

async def config_flow_pairing(hass, address, client_id=None, client_name="homeassistant"):
    conn = Connection(hass, address)
    new_client_id = client_id
    if not new_client_id:
        new_client_id = generate_client_id()


    await conn.connect()
    try:
        client_slot = await conn.pair_client(new_client_id, client_name)
    finally:
        await conn.disconnect()

    logger.warning(f"Pairing new client id: {new_client_id}, "
          f"client_slot: {client_slot}")

    return new_client_id, client_slot


def generate_client_id():
    max_client_id = (1 << 16) - 1
    return random.randint(10000, max_client_id)
