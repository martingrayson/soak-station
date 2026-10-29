"""Switch platform for Mira Soak Station devices.

This module handles the setup of switches that control individual outlets
on the Mira Soak Station device.
"""

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .mira.switch.outlet_switch import SoakStationOutletSwitch


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up switches for the Mira Soak Station device.
    
    Args:
        hass: Home Assistant instance
        config_entry: Configuration entry containing device details
        async_add_entities: Callback to add entities to Home Assistant
    """
    coordinator = config_entry.runtime_data

    # Create switches for each outlet
    switches = [
        SoakStationOutletSwitch(coordinator, outlet_number=1),
        SoakStationOutletSwitch(coordinator, outlet_number=2),
    ]

    # Register switches with Home Assistant
    async_add_entities(switches)
