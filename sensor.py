from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    data = config_entry.data
    address = data["device_address"]
    client_id = data["client_id"]
    client_slot = data["client_slot"]
    device_name = data["device_name"]

    sensors = [
        SoakStationTempSensor(address, device_name, "target_temp", "Target Temperature"),
        SoakStationTempSensor(address, device_name, "actual_temp", "Actual Temperature"),
        SoakStationTimerStateSensor(address, device_name),
        SoakStationTimerRemainingSensor(address, device_name),
    ]
    async_add_entities(sensors)


class SoakStationTempSensor(SensorEntity):
    def __init__(self, address, device_name, kind, name):
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
        self._state = 38.0

    @property
    def native_value(self):
        return self._state


class SoakStationTimerStateSensor(SensorEntity):
    def __init__(self, address, device_name):
        self._address = address
        self._device_name = device_name
        self._attr_name = f"Timer State ({device_name})"
        self._attr_unique_id = f"soakstation_timerstate_{address.replace(':', '')}"
        self._attr_icon = "mdi:timer-outline"
        self._state = None

    async def async_update(self):
        self._state = "running"

    @property
    def native_value(self):
        return self._state


class SoakStationTimerRemainingSensor(SensorEntity):
    def __init__(self, address, device_name):
        self._address = address
        self._device_name = device_name
        self._attr_name = f"Timer Remaining ({device_name})"
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
