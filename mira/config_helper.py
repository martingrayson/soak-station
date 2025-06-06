"""Helper functions for device configuration and pairing.

This module provides utilities for pairing new clients with Mira devices
and generating client IDs. It handles the configuration flow process
used during device setup.
"""

import logging
import random
from typing import Tuple

from .helpers.connection import Connection 
from .helpers.notifications import Notifications

logger = logging.getLogger(__name__)

async def config_flow_pairing(
    hass,
    address: str,
    client_id: int = None,
    client_name: str = "homeassistant"
) -> Tuple[int, int]:
    """Pair a new client with the device.
    
    Establishes a connection to the device and performs the pairing process
    to register a new client. This assigns a client ID and slot that are 
    used for future communication.

    Args:
        hass: Home Assistant instance used for device discovery
        address: Bluetooth MAC address of the target device
        client_id: Optional client ID to use, will generate random ID if not provided
        client_name: Name to register the client under, defaults to "homeassistant"
        
    Returns:
        Tuple[int, int]: A tuple containing:
            - client_id (int): The client ID assigned/used for this client
            - client_slot (int): The slot number assigned by the device
            
    Raises:
        ConnectionError: If device connection fails
        ValueError: If pairing process fails
    """
    async with Connection(hass, address) as conn:
        notifications = Notifications(is_pairing=True)
        client_id_out, client_slot = await conn.pair_client(
            client_id or generate_client_id(),
            client_name,
            notifications
        )
        
    logger.debug(
        "Paired new client id: %s, client_slot: %s",
        client_id_out,
        client_slot
    )
    
    return client_id_out, client_slot

def generate_client_id() -> int:
    """Generate a random client ID.
    
    Creates a random client identifier between 10000 and 65535 (max 16-bit value).
    The minimum value of 10000 helps avoid conflicts with reserved IDs.
    
    Returns:
        int: A random integer ID between 10000 and 65535
    """
    max_client_id = (1 << 16) - 1  # 65535
    return random.randint(10000, max_client_id)
