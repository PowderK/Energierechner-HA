"""Energierechner Home Assistant Integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import EnergierechnerCoordinator

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration über Config Entry einrichten."""
    hass.data.setdefault(DOMAIN, {})

    config = {**entry.data}
    if entry.options:
        config.update(entry.options)

    coordinator = EnergierechnerCoordinator(hass, config, entry.entry_id)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration sauber entladen."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Bei Optionsänderung neu laden."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
