from homeassistant.components.sensor import SensorEntity, SensorDeviceClass

class SoakStationTimerRemainingSensor(SensorEntity):
    def __init__(self, hass, data, meta, address, device_name):
        self._hass = hass
        self._data = data
        self._meta = meta
        self._address = address
        self._device_name = device_name
        self._attr_name = f"Timer Remaining ({device_name})"
        self._attr_unique_id = f"soakstation_timerremaining_{address.replace(':', '')}"
        self._attr_native_unit_of_measurement = "s"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_icon = "mdi:timer-sand"
        self._state = None
        self._data.subscribe(self._update_from_model)
        self._attr_device_info = self._meta.get_device_info()

    def _update_from_model(self):
        new_state = self._data.remaining_seconds
        # Only update HA state if it changed
        if self._state != new_state:
            self._state = new_state
            self.async_write_ha_state()

    async def async_update(self):
        # This is only used when HA explicitly polls
        self._update_from_model()

    @property
    def native_value(self):
        return self._state
