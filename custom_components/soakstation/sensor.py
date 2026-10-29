"""Sensor platform for Mira Soak Station devices.

This module handles the setup of sensors that monitor temperature and timer
states for the Mira Soak Station device.
"""

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

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
    coordinator = config_entry.runtime_data
    address = config_entry.data["device_address"]
    device_name = config_entry.data["device_name"]

    # Create sensors for temperature and timer states
    sensors = [
        SoakStationTempSensor(coordinator, address, device_name, "target_temp", "Target Temperature"),
        SoakStationTempSensor(coordinator, address, device_name, "actual_temp", "Actual Temperature"),
        SoakStationTimerStateSensor(coordinator, address, device_name),
        SoakStationTimerRemainingSensor(coordinator, address, device_name),
    ]

    # Register sensors with Home Assistant
    async_add_entities(sensors)
