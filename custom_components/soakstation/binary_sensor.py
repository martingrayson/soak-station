"""Binary sensor platform for Mira Soak Station devices.

This module handles the setup of binary sensors that monitor the state
of individual outlets on the Mira Soak Station device.
"""

from __future__ import annotations
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .mira.sensors.outlet_binary_sensor import SoakStationOutletBinarySensor

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
    coordinator = config_entry.runtime_data
    address = config_entry.data["device_address"]
    device_name = config_entry.data["device_name"]

    # Create binary sensors for each outlet
    sensors = [
        SoakStationOutletBinarySensor(coordinator, device_name, address, outlet_num=1),
        SoakStationOutletBinarySensor(coordinator, device_name, address, outlet_num=2),
    ]

    # Register sensors with Home Assistant
    async_add_entities(sensors)
