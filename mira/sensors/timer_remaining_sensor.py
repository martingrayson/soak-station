from homeassistant.components.sensor import SensorEntity

class SoakStationTimerRemainingSensor(SensorEntity):
    def __init__(self, hass, connection, address, device_name):
        self._hass = hass
        self._connection = connection
        self._address = address
        self._device_name = device_name
        self._attr_name = f"Timer Remaining ({device_name})"
        self._attr_unique_id = f"soakstation_timerremaining_{address.replace(':', '')}"
        self._attr_native_unit_of_measurement = "s"
        self._attr_device_class = "duration"
        self._attr_icon = "mdi:timer-sand"
        self._state = None

    async def async_update(self):
        """ The time remaining on the timer """
        self._state = 120

    @property
    def native_value(self):
        return self._state
