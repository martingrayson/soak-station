import logging
from datetime import timedelta

from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN
from .mira.helpers.connection import Connection
from .mira.helpers.data_model import SoakStationData
from .mira.helpers.notifications import Notifications


logger = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry):
    device_address = config_entry.data["device_address"]
    client_id = config_entry.data["client_id"]
    client_slot = config_entry.data["client_slot"]

    connection = Connection(hass, device_address, client_id, client_slot)
    await connection.connect()

    data_model = SoakStationData()
    notifications = Notifications(model=data_model)

    connection.subscribe(notifications)
    await connection.request_device_state()

    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = {
        "connection": connection,
        "data": data_model,
    }

    # Set up periodic polling every 10 seconds
    async def poll_device_state(now):
        try:
            await connection.request_device_state()
        except Exception as e:
            logger.warning(f"Failed to poll device state: {e}")

    async_track_time_interval(hass, poll_device_state, timedelta(seconds=20))


    await hass.config_entries.async_forward_entry_setups(config_entry, ["binary_sensor", "sensor"])
    return True

async def async_unload_entry(hass, config_entry):
    unload_bin = await hass.config_entries.async_forward_entry_unload(config_entry, "binary_sensor")
    unload_sens = await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")

    connection = hass.data[DOMAIN][config_entry.entry_id]["connection"]
    await connection.disconnect()

    hass.data[DOMAIN].pop(config_entry.entry_id)
    return unload_bin and unload_sens
