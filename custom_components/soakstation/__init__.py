"""The Mira Soak Station integration."""

import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import SoakStationCoordinator
from .mira.helpers.connection import Connection
from .mira.helpers.data_model import SoakStationData, SoakStationMetadata
from .mira.helpers.notifications import Notifications

logger = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up a Mira device.

    Raises ConfigEntryNotReady (via the first refresh) when the device can't be
    reached, so Home Assistant keeps retrying instead of giving up.
    """
    device_address = config_entry.data["device_address"]
    logger.debug(f"Setting up entry for device {device_address}")

    connection = Connection(
        hass, device_address, config_entry.data["client_id"], config_entry.data["client_slot"]
    )
    data_model = SoakStationData()
    metadata = SoakStationMetadata()
    # Identity until the device has been read; replaced on the first connection
    metadata.update_device_identity(
        name=config_entry.data.get("device_name", config_entry.title),
        manufacturer="Mira",
        model=None,
        device_address=device_address,
    )
    await connection.subscribe(Notifications(model=data_model, metadata=metadata))

    coordinator = SoakStationCoordinator(hass, config_entry, connection, data_model, metadata)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await connection.disconnect()
        raise
    config_entry.runtime_data = coordinator

    # Reconnect promptly when an unreachable device starts advertising again
    config_entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            coordinator.handle_advertisement,
            bluetooth.BluetoothCallbackMatcher(address=device_address, connectable=True),
            bluetooth.BluetoothScanningMode.PASSIVE,
        )
    )

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a Mira device and disconnect from it."""
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    if unload_ok:
        await config_entry.runtime_data.async_shutdown()
    return unload_ok
