import logging

logger = logging.getLogger(__name__)
async def async_setup_entry(hass, config_entry):
    from .const import DOMAIN
    from .mira.helpers.connection import Connection
    from .mira.helpers.data_model import SoakStationData
    from .mira.helpers.notifications import Notifications



    device_address = config_entry.data["device_address"]
    client_id = config_entry.data["client_id"]
    client_slot = config_entry.data["client_slot"]

    connection = Connection(hass, device_address, client_id, client_slot)
    await connection.connect()

    data_model = SoakStationData()  # shared state for entities

    # Subscribe BLE notifications, populate model, etc.
    notifications = Notifications(model=data_model)
    connection.subscribe(notifications)
    await connection.request_device_state()

    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = {
        "connection": connection,
        "data": data_model,
    }

    await hass.config_entries.async_forward_entry_setups(config_entry, ["binary_sensor", "sensor"])
    return True

async def async_unload_entry(hass, config_entry):
    unload_bin = await hass.config_entries.async_forward_entry_unload(config_entry, "binary_sensor")
    unload_sens = await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
    return unload_bin and unload_sens
