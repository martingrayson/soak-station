from homeassistant.components.switch import SwitchEntity

from ...entity import SoakStationEntity


class SoakStationOutletSwitch(SoakStationEntity, SwitchEntity):
    """Switch entity representing a soak station outlet's power state.

    Turning it on or off waits for the device to confirm, and raises an error
    in Home Assistant if the device can't be reached.

    Attributes:
        _outlet_number: Outlet number (1 or 2)
    """

    def __init__(self, coordinator, outlet_number):
        """Initialize the outlet switch.

        Args:
            coordinator: Coordinator for the device
            outlet_number: Outlet number (1 or 2)
        """
        super().__init__(coordinator)
        self._outlet_number = outlet_number

        # Configure entity attributes
        metadata = coordinator.metadata
        self._attr_name = f"Outlet {outlet_number} ({metadata.name})"
        self._attr_unique_id = f"{metadata.device_address.replace(':', '')}_outlet_{outlet_number}"
        self._attr_icon = "mdi:shower-head"

    async def _update_outlet_state(self, new_state: bool):
        """Update the state of the controlled outlet while maintaining other outlet's state.

        Args:
            new_state: True to turn on, False to turn off
        """
        outlets = [bool(self._data.outlet_1_on), bool(self._data.outlet_2_on)]
        outlets[self._outlet_number - 1] = new_state
        await self.coordinator.async_control_outlets(outlets[0], outlets[1])

    async def async_turn_on(self, **kwargs):
        """Turn the outlet on, keeping the other outlet's state."""
        await self._update_outlet_state(True)

    async def async_turn_off(self, **kwargs):
        """Turn the outlet off, keeping the other outlet's state."""
        await self._update_outlet_state(False)

    @property
    def is_on(self):
        """Get the current power state of the outlet.

        Returns:
            bool: True if the outlet is on, False if off
        """
        return getattr(self._data, f"outlet_{self._outlet_number}_on")
