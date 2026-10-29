from homeassistant.components.sensor import SensorEntity, SensorDeviceClass

from ...entity import SoakStationEntity


class SoakStationTimerStateSensor(SoakStationEntity, SensorEntity):
    """Sensor for tracking timer state on a soak station device.

    This sensor tracks the current state of a soak station device's timer (running,
    paused, or stopped).
    """

    def __init__(self, coordinator, address, device_name):
        """Initialize the timer state sensor.

        Args:
            coordinator: Coordinator for the device
            address: Device MAC address
            device_name: User-friendly device name
        """
        super().__init__(coordinator)

        # Configure entity attributes
        self._attr_name = f"Timer State ({device_name})"
        self._attr_unique_id = f"soakstation_timerstate_{address.replace(':', '')}"
        self._attr_icon = "mdi:timer-outline"
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["running", "paused", "stopped"]

    @property
    def native_value(self):
        """Get the current timer state value.

        Returns:
            str: Current timer state as lowercase string, or None if no state
        """
        state = self._data.timer_state
        return state.name.lower() if state else None
