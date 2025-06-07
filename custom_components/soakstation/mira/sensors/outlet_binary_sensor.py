from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass


class SoakStationOutletBinarySensor(BinarySensorEntity):
    """Binary sensor representing a soak station outlet's running state.
    
    This sensor tracks whether a specific outlet on a soak station device is currently
    running or not. It updates its state based on changes to the device's data model.
    
    Attributes:
        hass: Home Assistant instance
        _data: Device data model
        _meta: Device metadata
        _address: Device MAC address
        _device_name: User-friendly device name
        _outlet_num: Outlet number (1 or 2)
    """

    def __init__(self, hass, data, meta, device_name, address, outlet_num):
        """Initialize the outlet binary sensor.
        
        Args:
            hass: Home Assistant instance
            data: Device data model
            meta: Device metadata
            device_name: User-friendly device name
            address: Device MAC address
            outlet_num: Outlet number (1 or 2)
        """
        # Store instance variables
        self.hass = hass
        self._data = data
        self._meta = meta
        self._address = address
        self._device_name = device_name
        self._outlet_num = outlet_num

        # Configure entity attributes
        self._attr_name = f"Outlet {outlet_num} ({device_name})"
        self._attr_unique_id = f"soakstation_outlet{outlet_num}_{address.replace(':', '')}"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        self._attr_icon = "mdi:shower-head"
        self._attr_is_on = None
        self._attr_device_info = self._meta.get_device_info()

        # Subscribe to data model updates
        self._data.subscribe(self._update_from_model)

    def _update_from_model(self):
        """Update sensor state from the device data model.
        
        Gets the current running state for the tracked outlet and updates
        Home Assistant if the state has changed.
        """
        # Get state for the appropriate outlet
        new_state = (
            self._data.outlet_1_on if self._outlet_num == 1
            else self._data.outlet_2_on
        )

        # Update HA state if changed
        if self._attr_is_on != new_state:
            self._attr_is_on = new_state
            self.async_write_ha_state()

    async def async_update(self):
        """Update sensor state when Home Assistant polls.
        
        This method is called when Home Assistant explicitly polls the sensor.
        It delegates to _update_from_model to maintain consistent state handling.
        """
        self._update_from_model()
