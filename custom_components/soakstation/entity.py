"""Base entity for Mira Soak Station devices."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import SoakStationCoordinator


class SoakStationEntity(CoordinatorEntity[SoakStationCoordinator]):
    """An entity of a Mira device; unavailable while the device can't be reached.

    Attributes:
        _data: Device data model
        _meta: Device metadata
    """

    def __init__(self, coordinator: SoakStationCoordinator) -> None:
        """Initialize the entity.

        Args:
            coordinator: Coordinator for the device
        """
        super().__init__(coordinator)
        self._data = coordinator.model
        self._meta = coordinator.metadata

    @property
    def device_info(self) -> DeviceInfo:
        """Get the device info for this entity."""
        return self._meta.get_device_info()
