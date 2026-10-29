from homeassistant.const import UnitOfTemperature
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass

from ...entity import SoakStationEntity


class SoakStationTempSensor(SoakStationEntity, SensorEntity):
    """Temperature sensor for a soak station device.

    This sensor tracks either the target or actual temperature of a soak station device.

    Attributes:
        _kind: Type of temperature being tracked ("target_temp" or "actual_temp")
    """

    def __init__(self, coordinator, address, device_name, kind, name):
        """Initialize the temperature sensor.

        Args:
            coordinator: Coordinator for the device
            address: Device MAC address
            device_name: User-friendly device name
            kind: Type of temperature being tracked ("target_temp" or "actual_temp")
            name: Display name for the sensor
        """
        super().__init__(coordinator)
        self._kind = kind

        # Configure entity attributes
        self._attr_name = f"{name} ({device_name})"
        self._attr_unique_id = f"soakstation_{kind}_{address.replace(':', '')}"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_icon = "mdi:thermometer"

    @property
    def native_value(self):
        """Get the current temperature value.

        Returns:
            float: Current temperature in Celsius
        """
        return getattr(self._data, self._kind)
