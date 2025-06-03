from __future__ import annotations

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .mira.sensors.connection_binary_sensor import SoakStationConnectionSensor
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
    client_id = data["client_id"]
    client_slot = data["client_slot"]
    device_name = data["device_name"]

    connection = hass.data[DOMAIN][config_entry.entry_id]["connection"]

    sensors = [
        SoakStationOutletBinarySensor(hass, connection, device_name, address, client_id, client_slot, outlet_num=1),
        SoakStationOutletBinarySensor(hass, connection, device_name, address, client_id, client_slot, outlet_num=2),
        SoakStationConnectionSensor(hass, connection, device_name, address, client_id, client_slot),
    ]

    async_add_entities(sensors)
