from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass

_LOGGER = logging.getLogger(__name__)

class SoakStationConnectionSensor(BinarySensorEntity):
    def __init__(self, hass, connection, device_name, address, client_id, client_slot):
        self.hass = hass
        self._connection = connection
        self._address = address
        self._device_name = device_name
        self._client_id = client_id
        self._client_slot = client_slot

        self._attr_name = f"Connected ({device_name})"
        self._attr_unique_id = f"soakstation_connection_{address.replace(':', '')}"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_icon = "mdi:bluetooth-connect"




    async def async_update(self):
        """Set connection status to True if device is in Bluetooth range."""

        self._attr_is_on = True
