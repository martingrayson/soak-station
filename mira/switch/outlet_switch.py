from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo


class SoakStationOutletSwitch(SwitchEntity):
    """Switch entity representing a soak station outlet's power state.
    
    This switch controls whether a specific outlet on a soak station device is powered
    on or off. It updates its state based on changes to the device's data model.
    
    Attributes:
        hass: Home Assistant instance
        _connection: Device connection handler
        _model: Device data model
        _metadata: Device metadata
        _outlet_number: Outlet number (1 or 2)
        _state: Current power state of the outlet
    """

    def __init__(self, hass, connection, model, metadata, outlet_number):
        """Initialize the outlet switch.
        
        Args:
            hass: Home Assistant instance
            connection: Device connection handler
            model: Device data model
            metadata: Device metadata
            outlet_number: Outlet number (1 or 2)
        """
        super().__init__()
        
        # Store instance variables
        self._hass = hass
        self._connection = connection
        self._model = model
        self._metadata = metadata
        self._outlet_number = outlet_number
        
        # Configure entity attributes
        self._attr_name = f"Outlet {outlet_number} ({metadata.name})"
        self._attr_unique_id = f"{metadata.device_address.replace(':', '')}_outlet_{outlet_number}"
        self._state = None
        
        # Subscribe to model updates
        self._model.subscribe(self._handle_model_update)

    def _handle_model_update(self):
        """Update switch state from the device data model.
        
        Gets the current power state for the tracked outlet and updates
        Home Assistant if the state has changed.
        """
        new_state = getattr(self._model, f"outlet_{self._outlet_number}_on", None)
        if new_state is not None and new_state != self._state:
            self._state = new_state
            self.async_write_ha_state()

    async def _update_outlet_state(self, new_state: bool):
        """Update the state of the controlled outlet while maintaining other outlet's state.
        
        Args:
            new_state: True to turn on, False to turn off
        """
        outlets = [self._model.outlet_1_on, self._model.outlet_2_on]
        outlets[self._outlet_number - 1] = new_state
        await self._connection.control_outlets(outlets[0], outlets[1], temperature=self._model.target_temp or 38)

    async def async_turn_on(self, **kwargs):
        """Turn the outlet on.
        
        Sets the appropriate outlet to on state while maintaining the other outlet's
        current state. Uses a default temperature of 38°C.
        """
        await self._update_outlet_state(True)

    async def async_turn_off(self, **kwargs):
        """Turn the outlet off.
        
        Sets the appropriate outlet to off state while maintaining the other outlet's
        current state. Uses a default temperature of 38°C.
        """
        await self._update_outlet_state(False)

    @property
    def is_on(self):
        """Get the current power state of the outlet.
        
        Returns:
            bool: True if the outlet is on, False if off
        """
        return self._state

    @property
    def device_info(self) -> DeviceInfo:
        """Get the device info for this entity.
        
        Returns:
            DeviceInfo: Device information for Home Assistant
        """
        return self._metadata.get_device_info()

    @property
    def icon(self):
        """Get the icon to display for this entity.
        
        Returns:
            str: Material Design Icon name:
                - "mdi:shower" when the outlet is on
                - "mdi:shower-head-off" when the outlet is off
        """
        if self.is_on:
            return "mdi:shower"
        else:
            return "mdi:shower-head-off"