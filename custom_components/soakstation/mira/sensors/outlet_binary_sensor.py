from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass

from ...entity import SoakStationEntity


class SoakStationOutletBinarySensor(SoakStationEntity, BinarySensorEntity):
    """Binary sensor representing a soak station outlet's running state.

    Attributes:
        _outlet_num: Outlet number (1 or 2)
    """

    def __init__(self, coordinator, device_name, address, outlet_num):
        """Initialize the outlet binary sensor.

        Args:
            coordinator: Coordinator for the device
            device_name: User-friendly device name
            address: Device MAC address
            outlet_num: Outlet number (1 or 2)
        """
        super().__init__(coordinator)
        self._outlet_num = outlet_num

        # Configure entity attributes
        self._attr_name = f"Outlet {outlet_num} ({device_name})"
        self._attr_unique_id = f"soakstation_outlet{outlet_num}_{address.replace(':', '')}"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        self._attr_icon = "mdi:shower-head"

    @property
    def is_on(self):
        """Whether the outlet is running."""
        return getattr(self._data, f"outlet_{self._outlet_num}_on")
