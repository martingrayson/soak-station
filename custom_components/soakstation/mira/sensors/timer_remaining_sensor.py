from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import UnitOfTime

from ...entity import SoakStationEntity


class SoakStationTimerRemainingSensor(SoakStationEntity, SensorEntity):
    """Sensor for tracking remaining timer duration on a soak station device."""

    def __init__(self, coordinator, address, device_name):
        """Initialize the timer remaining sensor.

        Args:
            coordinator: Coordinator for the device
            address: Device MAC address
            device_name: User-friendly device name
        """
        super().__init__(coordinator)

        # Configure entity attributes
        self._attr_name = f"Timer Remaining ({device_name})"
        self._attr_unique_id = f"soakstation_timerremaining_{address.replace(':', '')}"
        # a duration, so Home Assistant shows it as minutes and seconds, not a bare count
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_icon = "mdi:timer-sand"

    @property
    def native_value(self):
        """Get the current remaining time value.

        Returns:
            int: Current remaining time in seconds
        """
        return self._data.remaining_seconds
