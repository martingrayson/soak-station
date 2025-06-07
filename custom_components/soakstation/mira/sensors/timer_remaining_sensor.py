from homeassistant.components.sensor import SensorEntity, SensorDeviceClass


class SoakStationTimerRemainingSensor(SensorEntity):
    """Sensor for tracking remaining timer duration on a soak station device.
    
    This sensor tracks the remaining time on a soak station device's timer.
    It updates its state based on changes to the device's data model.
    
    Attributes:
        hass: Home Assistant instance
        _data: Device data model
        _meta: Device metadata
        _address: Device MAC address
        _device_name: User-friendly device name
    """

    def __init__(self, hass, data, meta, address, device_name):
        """Initialize the timer remaining sensor.
        
        Args:
            hass: Home Assistant instance
            data: Device data model
            meta: Device metadata
            address: Device MAC address
            device_name: User-friendly device name
        """
        super().__init__()
        
        # Store instance variables
        self._hass = hass
        self._data = data
        self._meta = meta
        self._address = address
        self._device_name = device_name
        
        # Configure entity attributes
        self._attr_name = f"Timer Remaining ({device_name})"
        self._attr_unique_id = f"soakstation_timerremaining_{address.replace(':', '')}"
        self._attr_native_unit_of_measurement = "s"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_icon = "mdi:timer-sand"
        self._state = None
        self._attr_device_info = self._meta.get_device_info()
        
        # Subscribe to data model updates
        self._data.subscribe(self._update_from_model)

    def _update_from_model(self):
        """Update sensor state from the device data model.
        
        Gets the current remaining seconds value and updates Home Assistant
        if the state has changed.
        """
        new_state = self._data.remaining_seconds
        
        # Only update HA state if it changed
        if self._state != new_state:
            self._state = new_state
            self.async_write_ha_state()

    async def async_update(self):
        """Update sensor state when Home Assistant polls.
        
        This method is called when Home Assistant explicitly polls the sensor.
        It delegates to _update_from_model to maintain consistent state handling.
        """
        self._update_from_model()

    @property
    def native_value(self):
        """Get the current remaining time value.
        
        Returns:
            int: Current remaining time in seconds
        """
        return self._state
