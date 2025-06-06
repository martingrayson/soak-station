from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .mira.switch.outlet_switch import SoakStationOutletSwitch


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    connection = data["connection"]
    metadata = data["metadata"]
    model = data["data"]

    async_add_entities([
        SoakStationOutletSwitch(hass, connection, model, metadata, outlet_number=1),
        SoakStationOutletSwitch(hass, connection, model, metadata, outlet_number=2),
    ])
