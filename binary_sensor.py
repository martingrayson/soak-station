"""Binary sensor platform for Mira Soak Station devices.

This module handles the setup of binary sensors that monitor the state
of individual outlets on the Mira Soak Station device.
"""

from __future__ import annotations
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .mira.sensors.outlet_binary_sensor import SoakStationOutletBinarySensor
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up binary sensors for the Mira Soak Station device.
    
    Args:
        hass: Home Assistant instance
        config_entry: Configuration entry containing device details
        async_add_entities: Callback to add entities to Home Assistant
    """
    # Extract device configuration
    data = config_entry.data
    address = data["device_address"]
    device_name = data["device_name"]

    # Get device data and metadata from hass storage
    config_data = hass.data[DOMAIN][config_entry.entry_id]["data"]
    meta = hass.data[DOMAIN][config_entry.entry_id]["metadata"]

    # Create binary sensors for each outlet
    sensors = [
        SoakStationOutletBinarySensor(
            hass, config_data, meta, device_name, address, outlet_num=1
        ),
        SoakStationOutletBinarySensor(
            hass, config_data, meta, device_name, address, outlet_num=2
        )
    ]

    # Register sensors with Home Assistant
    async_add_entities(sensors)
