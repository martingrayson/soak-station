from homeassistant.const import UnitOfTemperature
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass


class SoakStationTempSensor(SensorEntity):
    def __init__(self, hass, data, address, device_name, kind, name):
        super().__init__()
        self._hass = hass
        self._data = data
        self._address = address
        self._kind = kind
        self._device_name = device_name
        self._attr_name = f"{name} ({device_name})"
        self._attr_unique_id = f"soakstation_{kind}_{address.replace(':', '')}"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_icon = "mdi:thermometer"
        self._state = None


        self._data.subscribe(self._update_from_model)

    def _update_from_model(self):
        new_state = self._state
        if self._kind == "target_temp":
            new_state = self._data.target_temp
        elif self._kind == "actual_temp":
            new_state = self._data.actual_temp

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
