import logging
from datetime import timedelta

from bleak import BleakCharacteristicNotFoundError
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN
from .mira.helpers.connection import Connection
from .mira.helpers.data_model import SoakStationData, SoakStationMetadata
from .mira.helpers.notifications import Notifications


logger = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry):
    logger.debug("Setting up entry for device")
    device_address = config_entry.data["device_address"]
    client_id = config_entry.data["client_id"]
    client_slot = config_entry.data["client_slot"]
    logger.debug(f"Device address: {device_address}, client_id: {client_id}, client_slot: {client_slot}")

    connection = Connection(hass, device_address, client_id, client_slot)
    logger.debug("Connecting to device")
    await connection.connect()

    # Build the metadata wrapper and initialise it
    metadata = SoakStationMetadata()
    logger.debug("Getting device info")
    info = await connection.get_device_info()
    info['device_address'] = device_address
    metadata.update_device_identity(**info)
    logger.debug(f"Updated device metadata with info: {info}")

    # Build the data wrapper
    data_model = SoakStationData()
    logger.debug("Created data model")

    # Subscribe
    notifications = Notifications(model=data_model, metadata=metadata)
    connection.subscribe(notifications)
    logger.debug("Subscribed notifications handler")

    # Start requesting info
    logger.debug("Requesting technical info")
    await connection.request_technical_info()
    await metadata.wait_for_technical_info()
    logger.debug("Technical info received")

    logger.debug("Requesting initial device state")
    await connection.request_device_state()

    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = {
        "connection": connection,
        "data": data_model,
        "metadata": metadata,
    }
    logger.debug("Stored device data in hass.data")

    # Set up periodic polling every 10 seconds
    async def poll_device_state(now):
        logger.debug("Polling device state")
        try:
            await connection.request_device_state()
        except BleakCharacteristicNotFoundError as e:
            logger.warning("Characteristic not found, attempting reconnect")
            try:
                logger.debug("Attempting to reconnect")
                await connection.reconnect()
                await connection.request_device_state()
            except Exception as e:
                logger.error(f"Retry failed: {e}")
        except Exception as e:
            logger.warning(f"Failed to poll device state: {e}")

    logger.debug("Setting up periodic polling every 20 seconds")
    async_track_time_interval(hass, poll_device_state, timedelta(seconds=20))

    logger.debug("Setting up platform entries")
    await hass.config_entries.async_forward_entry_setups(config_entry, ["binary_sensor", "sensor", "switch"])
    return True

async def async_unload_entry(hass, config_entry):
    logger.debug("Unloading entry")
    unload_bin = await hass.config_entries.async_forward_entry_unload(config_entry, "binary_sensor")
    unload_sens = await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
    unload_sq = await hass.config_entries.async_forward_entry_unload(config_entry, "switch")
    logger.debug(f"Unloaded platforms - binary_sensor: {unload_bin}, sensor: {unload_sens}, switch: {unload_sq}")

    connection = hass.data[DOMAIN][config_entry.entry_id]["connection"]
    logger.debug("Disconnecting from device")
    await connection.disconnect()

    hass.data[DOMAIN].pop(config_entry.entry_id)
    logger.debug("Removed device data from hass.data")
    return unload_bin and unload_sens
