from homeassistant.components.sensor import SensorEntity

class SoakStationTimerStateSensor(SensorEntity):
    def __init__(self, hass, data, meta, address, device_name):
        self._hass = hass
        self._data = data
        self._meta = meta
        self._address = address
        self._device_name = device_name
        self._attr_name = f"Timer State ({device_name})"
        self._attr_unique_id = f"soakstation_timerstate_{address.replace(':', '')}"
        self._attr_icon = "mdi:timer-outline"
        self._state = None
        self._attr_device_class = "enum"
        self._attr_options = ["running", "paused", "stopped"]
        self._data.subscribe(self._update_from_model)
        self._attr_device_info = self._meta.get_device_info()

    def _update_from_model(self):
        new_state = self._data.timer_state
        # Only update HA state if it changed
        if self._state != new_state:
            self._state = new_state
            self.async_write_ha_state()

    async def async_update(self):
        # This is only used when HA explicitly polls
        self._update_from_model()

    @property
    def native_value(self):
        return self._state.name.lower() if self._state else None

