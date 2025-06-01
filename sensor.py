from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfTemperature


async def async_setup_entry(hass, config_entry, async_add_entities):
    devices = config_entry.data.get("devices", [])
    sensors = []

    for address in devices:
        sensors.extend([
            SoakStationTempSensor(address, "target_temp", "Target Temperature"),
            SoakStationTempSensor(address, "actual_temp", "Actual Temperature"),
            SoakStationTimerStateSensor(address),
            SoakStationTimerRemainingSensor(address),
        ])
    
    async_add_entities(sensors)

class SoakStationTempSensor(SensorEntity):
    def __init__(self, address, kind, name):
        self._address = address
        self._kind = kind
        self._attr_name = f"{name} ({address})"
        self._attr_unique_id = f"soakstation_{kind}_{address.replace(':', '')}"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = "temperature"
        self._attr_icon = "mdi:thermometer"
        self._state = None

    async def async_update(self):
        self._state = 38.0

    @property
    def native_value(self):
        return self._state

class SoakStationTimerStateSensor(SensorEntity):
    def __init__(self, address):
        self._address = address
        self._attr_name = f"Timer State ({address})"
        self._attr_unique_id = f"soakstation_timerstate_{address.replace(':', '')}"
        self._attr_icon = "mdi:timer-outline"
        self._state = None

    async def async_update(self):
        self._state = "running" 

    @property
    def native_value(self):
        return self._state

class SoakStationTimerRemainingSensor(SensorEntity):
    def __init__(self, address):
        self._address = address
        self._attr_name = f"Timer Remaining ({address})"
        self._attr_unique_id = f"soakstation_timerremaining_{address.replace(':', '')}"
        self._attr_native_unit_of_measurement = "s"
        self._attr_device_class = "duration"
        self._attr_icon = "mdi:timer-sand"
        self._state = None

    async def async_update(self):
        self._state = 120 

    @property
    def native_value(self):
        return self._state
