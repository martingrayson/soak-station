from homeassistant.const import UnitOfTemperature
from homeassistant.components.sensor import SensorEntity


class SoakStationTempSensor(SensorEntity):
    def __init__(self, hass, connection, address, device_name, kind, name):
        self._hass = hass
        self._connection = connection
        self._address = address
        self._kind = kind
        self._device_name = device_name
        self._attr_name = f"{name} ({device_name})"
        self._attr_unique_id = f"soakstation_{kind}_{address.replace(':', '')}"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = "temperature"
        self._attr_icon = "mdi:thermometer"
        self._state = None


    async def async_update(self):
        """ Update state from Mira device, this is either the target or current state."""
        self._state = 38.0

    @property
    def native_value(self):
        return self._state
