from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass


class SoakStationOutletBinarySensor(BinarySensorEntity):
    def __init__(self, hass, data, device_name, address, outlet_num):
        self.hass = hass
        self._data = data
        self._address = address
        self._device_name = device_name
        self._outlet_num = outlet_num

        self._attr_name = f"Outlet {outlet_num} ({device_name})"
        self._attr_unique_id = f"soakstation_outlet{outlet_num}_{address.replace(':', '')}"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        self._attr_icon = "mdi:shower-head"
        self._attr_is_on = None

        self._data.subscribe(self._update_from_model)

    def _update_from_model(self):
        # Decide which outlet state to track
        new_state = (
            self._data.outlet_1_on if self._outlet_num == 1
            else self._data.outlet_2_on
        )

        # Only update HA state if it changed
        if self._attr_is_on != new_state:
            self._attr_is_on = new_state
            self.async_write_ha_state()

    async def async_update(self):
        # This is only used when HA explicitly polls
        self._update_from_model()