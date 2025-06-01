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
        entities.append(SoakStationConnectionSensor(address, name))
        entities.append(SoakStationOutletSensor(address, name, outlet=1))
        entities.append(SoakStationOutletSensor(address, name, outlet=2))

    async_add_entities(entities)

class SoakStationConnectionSensor(BinarySensorEntity):
    def __init__(self, address, name):
        self._address = address
        self._state = True  # Simulated connected
        self._attr_name = f"{name} Connected"
        self._attr_unique_id = f"soakstation_connected_{address.replace(':', '')}"
        self._attr_device_class = "connectivity"

    async def async_update(self):
        self._state = True  # Simulate always connected

    @property
    def is_on(self):
        return self._state

class SoakStationOutletSensor(BinarySensorEntity):
    def __init__(self, address, name, outlet=1):
        self._address = address
        self._outlet = outlet
        self._state = False
        self._attr_name = f"{name} Outlet {outlet}"
        self._attr_unique_id = f"soakstation_outlet{outlet}_{address.replace(':', '')}"
        self._attr_device_class = "power"

    async def async_update(self):
        # Simulate outlet 1 ON, outlet 2 OFF
        self._state = self._outlet == 1

    @property
    def is_on(self):
        return self._state
