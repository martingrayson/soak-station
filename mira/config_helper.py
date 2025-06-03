import logging
import random
from .helpers.connection import Connection

logger = logging.getLogger(__name__)

async def config_flow_pairing(hass, address, client_id=None, client_name="homeassistant"):
    conn = Connection(hass, address)
    new_client_id = client_id
    if not new_client_id:
        new_client_id = generate_client_id()

    logger.warning(f"Pairing new client id: {new_client_id}, "
          f"name: {client_name}")

    await conn.connect()
    try:
        await conn.pair_client(new_client_id, client_name)
    finally:
        await conn.disconnect()

    return new_client_id


def generate_client_id():
    max_client_id = (1 << 16) - 1
    return random.randint(10000, max_client_id)
