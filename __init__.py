from .const import DOMAIN

async def async_setup_entry(hass, config_entry):
    await hass.config_entries.async_forward_entry_setup(config_entry, "binary_sensor")
    await hass.config_entries.async_forward_entry_setup(config_entry, "sensor")
    return True

async def async_unload_entry(hass, config_entry):
    unload_bin = await hass.config_entries.async_forward_entry_unload(config_entry, "binary_sensor")
    unload_sens = await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
    return unload_bin and unload_sens
