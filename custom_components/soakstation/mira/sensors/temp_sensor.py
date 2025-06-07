from homeassistant.const import UnitOfTemperature
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.device_registry import DeviceInfo


class SoakStationTempSensor(SensorEntity):
    """Temperature sensor for a soak station device.
    
    This sensor tracks either the target or actual temperature of a soak station device.
    It updates its state based on changes to the device's data model.
    
    Attributes:
        hass: Home Assistant instance
        _data: Device data model
        _meta: Device metadata
        _address: Device MAC address
        _kind: Type of temperature being tracked ("target_temp" or "actual_temp")
        _device_name: User-friendly device name
    """

    def __init__(self, hass, data, meta, address, device_name, kind, name):
        """Initialize the temperature sensor.
        
        Args:
            hass: Home Assistant instance
            data: Device data model
            meta: Device metadata
            address: Device MAC address
            device_name: User-friendly device name
            kind: Type of temperature being tracked ("target_temp" or "actual_temp")
            name: Display name for the sensor
        """
        super().__init__()
        
        # Store instance variables
        self._hass = hass
        self._data = data
        self._meta = meta
        self._address = address
        self._kind = kind
        self._device_name = device_name
        
        # Configure entity attributes
        self._attr_name = f"{name} ({device_name})"
        self._attr_unique_id = f"soakstation_{kind}_{address.replace(':', '')}"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_icon = "mdi:thermometer"
        self._state = None
        self._attr_device_info = self._meta.get_device_info()
        
        # Subscribe to data model updates
        self._data.subscribe(self._update_from_model)

    def _update_from_model(self):
        """Update sensor state from the device data model.
        
        Gets the current temperature value based on the sensor kind and updates
        Home Assistant if the state has changed.
        """
        # Get new state based on sensor kind
        new_state = self._state
        if self._kind == "target_temp":
            new_state = self._data.target_temp
        elif self._kind == "actual_temp":
            new_state = self._data.actual_temp

        # Update HA state if changed
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
        """Get the current temperature value.
        
        Returns:
            float: Current temperature in Celsius
        """
        return self._state
