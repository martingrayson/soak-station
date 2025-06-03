
from .mira.helpers.connection import Connection
from .const import DOMAIN

async def async_setup_entry(hass, config_entry):
    device_address = config_entry.data["device_address"]
    connection = Connection(hass, device_address)
    await hass.async_add_executor_job(connection.connect)

    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = {
        "connection": connection,
    }

    await hass.config_entries.async_forward_entry_setups(config_entry, ["binary_sensor", "sensor"])
    return True

async def async_unload_entry(hass, config_entry):
    unload_bin = await hass.config_entries.async_forward_entry_unload(config_entry, "binary_sensor")
    unload_sens = await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
    return unload_bin and unload_sens
