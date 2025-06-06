"""Sensor platform for Mira Soak Station devices.

This module handles the setup of sensors that monitor temperature and timer
states for the Mira Soak Station device.
"""

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .mira.sensors.temp_sensor import SoakStationTempSensor
from .mira.sensors.timer_remaining_sensor import SoakStationTimerRemainingSensor
from .mira.sensors.timer_state_sensor import SoakStationTimerStateSensor


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up sensors for the Mira Soak Station device.
    
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

    # Create sensors for temperature and timer states
    sensors = [
        SoakStationTempSensor(
            hass, config_data, meta, address, device_name, 
            "target_temp", "Target Temperature"
        ),
        SoakStationTempSensor(
            hass, config_data, meta, address, device_name,
            "actual_temp", "Actual Temperature"
        ),
        SoakStationTimerStateSensor(
            hass, config_data, meta, address, device_name
        ),
        SoakStationTimerRemainingSensor(
            hass, config_data, meta, address, device_name
        ),
    ]

    # Register sensors with Home Assistant
    async_add_entities(sensors)
