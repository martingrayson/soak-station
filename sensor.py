from homeassistant.components.sensor import SensorEntity
from homeassistant.const import TEMP_CELSIUS

async def async_setup_entry(hass, config_entry, async_add_entities):
    devices = config_entry.data.get("devices", [])
    sensors = []

    for address in devices:
        sensors.extend([
            SoakStationSensor(address, "target_temp", "Target Temperature", TEMP_CELSIUS),
            SoakStationSensor(address, "actual_temp", "Actual Temperature", TEMP_CELSIUS),
            SoakStationSensor(address, "timer_state", "Timer State", None),
            SoakStationSensor(address, "timer_remaining", "Timer Remaining", "s"),
        ])

    async_add_entities(sensors)

class SoakStationSensor(SensorEntity):
    def __init__(self, address, kind, name, unit):
        self._address = address
        self._kind = kind
        self._attr_name = f"{name} ({address})"
        self._attr_unique_id = f"soakstation_{kind}_{address.replace(':', '')}"
        self._attr_native_unit_of_measurement = unit
        self._state = None

    async def async_update(self):
        # Placeholder simulated data
        if self._kind == "target_temp":
            self._state = 38.0
        elif self._kind == "actual_temp":
            self._state = 36.5
        elif self._kind == "timer_state":
            self._state = "running"
        elif self._kind == "timer_remaining":
            self._state = 120

    @property
    def native_value(self):
        return self._state
