from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass


class SoakStationOutletBinarySensor(BinarySensorEntity):
    def __init__(self, hass, connection, device_name, address, client_id, client_slot, outlet_num):
        self.hass = hass
        self._connection = connection
        self._address = address
        self._device_name = device_name
        self._client_id = client_id
        self._client_slot = client_slot
        self._outlet_num = outlet_num

        self._attr_name = f"Outlet {outlet_num} ({device_name})"
        self._attr_unique_id = f"soakstation_outlet{outlet_num}_{address.replace(':', '')}"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        self._attr_icon = "mdi:shower-head"

    async def async_update(self):
        """Update state from Mira device."""
        self._attr_is_on = True
