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
    data = config_entry.data
    address = data["device_address"]
    device_name = data["device_name"]

    config_data = hass.data[DOMAIN][config_entry.entry_id]["data"]
    meta = hass.data[DOMAIN][config_entry.entry_id]["metadata"]

    sensors = [
        SoakStationOutletBinarySensor(hass, config_data, meta, device_name, address, outlet_num=1),
        SoakStationOutletBinarySensor(hass, config_data, meta, device_name, address, outlet_num=2)
    ]

    async_add_entities(sensors)
