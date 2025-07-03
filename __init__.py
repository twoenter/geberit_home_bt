from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .bluetooth_processor import BluetoothProcessor

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    address = entry.data["address"]
    processor = BluetoothProcessor(address)
    await processor.connect()

    await processor.start_watchdog(retry_interval=5.0)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN][entry.entry_id] = processor

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    processor = hass.data[DOMAIN].pop(entry.entry_id, None)
    if processor:
        await processor.disconnect()
    return await hass.config_entries.async_unload_platforms(entry, ["sensor"])