from homeassistant.components.sensor import SensorEntity


class SoakStationTimerStateSensor(SensorEntity):
    """Sensor for tracking timer state on a soak station device.
    
    This sensor tracks the current state of a soak station device's timer (running,
    paused, or stopped). It updates its state based on changes to the device's data model.
    
    Attributes:
        hass: Home Assistant instance
        _data: Device data model
        _meta: Device metadata
        _address: Device MAC address
        _device_name: User-friendly device name
    """

    def __init__(self, hass, data, meta, address, device_name):
        """Initialize the timer state sensor.
        
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
        self._attr_name = f"Timer State ({device_name})"
        self._attr_unique_id = f"soakstation_timerstate_{address.replace(':', '')}"
        self._attr_icon = "mdi:timer-outline"
        self._state = None
        self._attr_device_class = "enum"
        self._attr_options = ["running", "paused", "stopped"]
        self._attr_device_info = self._meta.get_device_info()
        
        # Subscribe to data model updates
        self._data.subscribe(self._update_from_model)

    def _update_from_model(self):
        """Update sensor state from the device data model.
        
        Gets the current timer state and updates Home Assistant if the state
        has changed.
        """
        new_state = self._data.timer_state
        
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
        """Get the current timer state value.
        
        Returns:
            str: Current timer state as lowercase string, or None if no state
        """
        return self._state.name.lower() if self._state else None
