"""Energierechner Home Assistant Integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.history import state_changes_during_period
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import EnergierechnerCoordinator

PLATFORMS = ["sensor"]
_LOGGER = logging.getLogger(__name__)


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

    # Debug-Service registrieren (nur einmal, beim ersten Entry)
    if not hass.services.has_service(DOMAIN, "debug_dump"):
        hass.services.async_register(DOMAIN, "debug_dump", _handle_debug_dump)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration sauber entladen."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Bei Optionsänderung neu laden."""
    await hass.config_entries.async_reload(entry.entry_id)


# ---------------------------------------------------------------------------
# Debug Service
# ---------------------------------------------------------------------------

async def _handle_debug_dump(call: ServiceCall) -> None:
    """Service-Handler: Schreibt detaillierten Debug-Bericht in den HA-Log."""
    hass: HomeAssistant = call.hass
    entries = hass.data.get(DOMAIN, {})

    if not entries:
        _LOGGER.warning("[Energierechner DEBUG] Keine aktiven Instanzen gefunden.")
        return

    for entry_id, coordinator in entries.items():
        await _dump_coordinator(hass, coordinator, entry_id)


async def _dump_coordinator(
    hass: HomeAssistant,
    coordinator: EnergierechnerCoordinator,
    entry_id: str,
) -> None:
    """Detaillierten Report für einen Coordinator schreiben."""
    cfg = coordinator._config
    source = cfg.get("source_entity", "?")
    periods = coordinator._periods
    now = dt_util.now()

    sep = "=" * 70
    _LOGGER.warning("\n%s", sep)
    _LOGGER.warning("  ENERGIERECHNER DEBUG DUMP – %s", now.strftime("%Y-%m-%d %H:%M:%S"))
    _LOGGER.warning("  Entry-ID : %s", entry_id)
    _LOGGER.warning("  Sensor   : %s", source)
    _LOGGER.warning("  Nachttar.: %s | Grundpreis: %s | Bilanz: %s",
                    cfg.get("night_rate"), cfg.get("add_base_price"), cfg.get("balance"))
    _LOGGER.warning("%s", sep)

    # ---- Aktueller Sensorwert -------------------------------------------
    current_state = hass.states.get(source)
    if current_state:
        _LOGGER.warning("  Aktueller Zählerstand : %s %s",
                        current_state.state,
                        current_state.attributes.get("unit_of_measurement", ""))
        _LOGGER.warning("  Letztes Update        : %s", current_state.last_updated)
    else:
        _LOGGER.warning("  ⚠️  Sensor '%s' nicht in HA gefunden!", source)

    # ---- Tarifperioden --------------------------------------------------
    _LOGGER.warning("\n  --- Konfigurierte Tarifperioden (%d) ---", len(periods))
    for i, p in enumerate(periods):
        _LOGGER.warning(
            "  [%d] ab %s | Tag: %.4f € | Nacht: %.4f € | Grundpr.: %.2f €/Jahr | Abschlag: %.2f €/Mon",
            i, p.get("start_date"), p.get("day_price", 0),
            p.get("night_price", p.get("day_price", 0)),
            p.get("base_price", 0), p.get("advance_payment", 0),
        )

    # ---- Recorder-Rohdaten für letzte 7 Tage + Perioden ----------------
    _LOGGER.warning("\n  --- Recorder-Rohdaten ---")

    checks = [
        ("Heute",            now.replace(hour=0, minute=0, second=0, microsecond=0), now),
        ("Gestern",          now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1),
                             now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)),
        ("Letzte 7 Tage",   now - timedelta(days=7), now),
        ("Aktueller Monat", now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), now),
    ]

    # Tarifperioden als Checks hinzufügen
    for i, p in enumerate(periods):
        from homeassistant.util.dt import parse_date
        begin = parse_date(p["start_date"])
        if begin:
            tz = now.tzinfo
            p_start = datetime.combine(begin, datetime.min.time()).replace(tzinfo=tz)
            if i + 1 < len(periods):
                next_begin = parse_date(periods[i + 1]["start_date"])
                p_end = datetime.combine(next_begin, datetime.min.time()).replace(tzinfo=tz) - timedelta(seconds=1)
            else:
                p_end = now
            checks.append((f"Tarifperiode ab {p['start_date']}", p_start, p_end))

    for label, start, end in checks:
        try:
            result: dict = await get_instance(hass).async_add_executor_job(
                state_changes_during_period,
                hass, start, end, source, False, None, True,
            )
            states = result.get(source, [])

            if len(states) < 2:
                _LOGGER.warning(
                    "  %-30s | ⚠️  Zu wenige States (%d) – Verbrauch = 0 kWh",
                    label, len(states)
                )
                continue

            def _val(s) -> float:
                try:
                    return float(s.state)
                except (TypeError, ValueError):
                    return 0.0

            first_val = _val(states[0])
            last_val  = _val(states[-1])
            diff      = max(0.0, last_val - first_val)
            first_ts  = getattr(states[0], "last_updated", None) or getattr(states[0], "last_changed", None)
            last_ts   = getattr(states[-1], "last_updated", None) or getattr(states[-1], "last_changed", None)

            warn = ""
            if diff > 500:
                warn = "  ⚠️  SEHR HOHER WERT – Zählerreset oder falscher Sensor?"
            if first_val > last_val:
                warn = "  ⚠️  Erster Wert > Letzter Wert – Zählerreset erkannt!"

            _LOGGER.warning(
                "  %-30s | States: %4d | Erster: %9.3f kWh (%s) | Letzter: %9.3f kWh (%s) | Diff: %9.3f kWh%s",
                label, len(states),
                first_val, first_ts.strftime("%d.%m %H:%M") if first_ts else "?",
                last_val,  last_ts.strftime("%d.%m %H:%M")  if last_ts  else "?",
                diff, warn,
            )

        except Exception as err:
            _LOGGER.warning("  %-30s | Fehler beim Abrufen: %s", label, err)

    # ---- Letzte berechnete Coordinator-Daten ----------------------------
    _LOGGER.warning("\n  --- Zuletzt berechnete Sensor-Werte ---")
    if coordinator.data:
        for key, val in sorted(coordinator.data.items()):
            _LOGGER.warning("  %-45s = %s", key, val)
    else:
        _LOGGER.warning("  (noch keine Daten berechnet)")

    _LOGGER.warning("%s\n", sep)
