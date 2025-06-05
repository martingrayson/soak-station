from homeassistant.components.sensor import SensorEntity

class SoakStationTimerStateSensor(SensorEntity):
    def __init__(self, hass, data, address, device_name):
        self._hass = hass
        self._data = data
        self._address = address
        self._device_name = device_name
        self._attr_name = f"Timer State ({device_name})"
        self._attr_unique_id = f"soakstation_timerstate_{address.replace(':', '')}"
        self._attr_icon = "mdi:timer-outline"
        self._state = None
        self._data.subscribe(self._update_from_model)

        #TODO
        # self._attr_options = ["running", "paused", "stopped"]

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
        return self._state

