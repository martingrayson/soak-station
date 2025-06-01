from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.components.bluetooth import async_ble_device_from_address
from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    devices = config_entry.data.get("devices", [])
    entities = []

    for address in devices:
        ble_device = async_ble_device_from_address(hass, address)
        name = ble_device.name if ble_device else address
        entities.append(SoakStationConnectionSensor(config_entry.entry_id, address, name))
        entities.append(SoakStationOutletSensor(config_entry.entry_id, address, name, outlet=1))
        entities.append(SoakStationOutletSensor(config_entry.entry_id, address, name, outlet=2))

    async_add_entities(entities)

class SoakStationConnectionSensor(BinarySensorEntity):
    def __init__(self, entry_id, address, name):
        self._address = address
        self._state = True
        self._attr_name = f"{name} Connected"
        self._attr_unique_id = f"{entry_id}_connected_{address.replace(':', '')}"
        self._attr_device_class = "connectivity"
        self._attr_icon = "mdi:bluetooth-connect"

    async def async_update(self):
        self._state = True  # Simulate always connected

    @property
    def is_on(self):
        return self._state

class SoakStationOutletSensor(BinarySensorEntity):
    def __init__(self, entry_id, address, name, outlet=1):
        self._address = address
        self._outlet = outlet
        self._state = False
        self._attr_name = f"{name} Outlet {outlet}"
        self._attr_unique_id = f"{entry_id}_outlet{outlet}_{address.replace(':', '')}"
        self._attr_device_class = "power"
        self._attr_icon = "mdi:shower-head"

    async def async_update(self):
        self._state = self._outlet == 1  # Simulate outlet 1 ON, outlet 2 OFF

    @property
    def is_on(self):
        return self._state
