from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo

class SoakStationOutletSwitch(SwitchEntity):
    def __init__(self, hass, connection, model, metadata, outlet_number):
        self._hass = hass
        self._connection = connection
        self._model = model
        self._metadata = metadata
        self._outlet_number = outlet_number

        self._attr_name = f"Outlet {outlet_number} ({metadata.name})"
        self._attr_unique_id = f"{metadata.device_address.replace(':', '')}_outlet_{outlet_number}"
        self._state = None

        # Subscribe to model updates
        self._model.subscribe(self._handle_model_update)

    def _handle_model_update(self):
        new_state = getattr(self._model, f"outlet_{self._outlet_number}_on", None)
        if new_state is not None and new_state != self._state:
            self._state = new_state
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        outlet_1 = self._outlet_number == 1
        outlet_2 = self._outlet_number == 2

        await self._connection.control_outlets(outlet_1, outlet_2, temperature=38)

    async def async_turn_off(self, **kwargs):
        if self._outlet_number == 1:
            outlet_1 = False
        elif self._outlet_number == 1:
            outlet_2 = False

        await self._connection.control_outlets(outlet_1, outlet_2, temperature=38)

    @property
    def is_on(self):
        return self._state

    @property
    def device_info(self) -> DeviceInfo:
        return self._metadata.get_device_info()
