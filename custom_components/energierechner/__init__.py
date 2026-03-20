"""Energierechner Home Assistant integration."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

DOMAIN = "energierechner"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    return True
