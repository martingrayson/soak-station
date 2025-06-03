from homeassistant.components.sensor import SensorEntity

class SoakStationTimerStateSensor(SensorEntity):
    def __init__(self, hass, connection, address, device_name):
        self._hass = hass
        self._connection = connection
        self._address = address
        self._device_name = device_name
        self._attr_name = f"Timer State ({device_name})"
        self._attr_unique_id = f"soakstation_timerstate_{address.replace(':', '')}"
        self._attr_icon = "mdi:timer-outline"
        self._state = None

    async def async_update(self):
        """ The state of the timer """
        self._state = "running"

    @property
    def native_value(self):
        return self._state
