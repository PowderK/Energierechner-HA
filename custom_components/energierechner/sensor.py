"""Sensor-Plattform für Energierechner (Config Entry basiert)."""
from __future__ import annotations

import logging
from datetime import datetime, date, time, timedelta
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.history import state_changes_during_period
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ACTIVE,
    CONF_ADD_BASE_PRICE,
    CONF_BALANCE,
    CONF_CURRENT_MONTH,
    CONF_CURRENT_YEAR,
    CONF_CURRENT_WEEK,
    CONF_DAILY,
    CONF_DAILY_CONSUMPTION,
    CONF_LAST_MONTH,
    CONF_LAST_YEAR,
    CONF_NAME,
    CONF_NIGHTLY_CONSUMPTION,
    CONF_NIGHT_RATE,
    CONF_PERIODS,
    CONF_PERIODS_CALCULATION,
    CONF_PREVIOUS_DAY,
    CONF_PREVIOUS_WEEK,
    CONF_SOURCE_ENTITY,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Sensor über Config Entry einrichten."""
    # Basisdaten + eventuelle Options zusammenführen
    data = {**entry.data}
    if entry.options:
        data.update(entry.options)

    sensor = EnergierechnerSensor(hass, data, entry.entry_id)
    async_add_entities([sensor], update_before_add=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(iso_date: str) -> date:
    return dt_util.parse_date(iso_date)


def _is_night(timestamp: datetime, night_start: time, night_end: time) -> bool:
    """Gibt True zurück wenn der Zeitpunkt in der Nachtzeit liegt."""
    t = timestamp.time().replace(second=0, microsecond=0)
    if night_start < night_end:
        return night_start <= t < night_end
    # Mitternacht übergreifend
    return t >= night_start or t < night_end


def _time_from_str(val) -> time:
    """Konvertiert 'HH:MM'-String oder time-Objekt."""
    if isinstance(val, time):
        return val
    if isinstance(val, str):
        parts = val.split(":")
        return time(int(parts[0]), int(parts[1]))
    return time(22, 0)


def _get_period_start_end(keyword: str) -> tuple[datetime, datetime]:
    today = dt_util.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if keyword == "today":
        return today, today + timedelta(days=1) - timedelta(seconds=1)
    elif keyword == "previous_day":
        start = today - timedelta(days=1)
        return start, today - timedelta(seconds=1)
    elif keyword == "current_week":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=7) - timedelta(seconds=1)
    elif keyword == "previous_week":
        start = today - timedelta(days=today.weekday() + 7)
        return start, start + timedelta(days=7) - timedelta(seconds=1)
    elif keyword == "current_month":
        start = today.replace(day=1)
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        return start, next_month - timedelta(seconds=1)
    elif keyword == "last_month":
        start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        return start, today.replace(day=1) - timedelta(seconds=1)
    elif keyword == "current_year":
        start = today.replace(month=1, day=1)
        return start, today.replace(month=12, day=31, hour=23, minute=59, second=59)
    elif keyword == "last_year":
        start = today.replace(year=today.year - 1, month=1, day=1)
        end = today.replace(year=today.year - 1, month=12, day=31, hour=23, minute=59, second=59)
        return start, end
    raise ValueError(f"Unbekanntes Zeitraum-Schlüsselwort: {keyword}")


# ---------------------------------------------------------------------------
# Sensor
# ---------------------------------------------------------------------------

class EnergierechnerSensor(SensorEntity):
    """Stromkosten-Sensor auf Basis von Recorder-Daten."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_native_unit_of_measurement = "€"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:lightning-bolt-circle"

    def __init__(self, hass: HomeAssistant, config: dict, entry_id: str) -> None:
        self.hass = hass
        self._name = config.get(CONF_NAME, DEFAULT_NAME)
        self._source_entity_id = config[CONF_SOURCE_ENTITY]
        self._periods = sorted(
            config.get(CONF_PERIODS, []),
            key=lambda p: _parse_date(p["start_date"])
        )
        self._night_rate = config.get(CONF_NIGHT_RATE, False)
        self._daily_consumption = config.get(CONF_DAILY_CONSUMPTION, False)
        self._nightly_consumption = config.get(CONF_NIGHTLY_CONSUMPTION, False)
        self._periods_calculation = config.get(CONF_PERIODS_CALCULATION, True)
        self._balance = config.get(CONF_BALANCE, False)
        self._daily = config.get(CONF_DAILY, True)
        self._previous_day = config.get(CONF_PREVIOUS_DAY, True)
        self._current_week = config.get(CONF_CURRENT_WEEK, True)
        self._previous_week = config.get(CONF_PREVIOUS_WEEK, False)
        self._current_month = config.get(CONF_CURRENT_MONTH, True)
        self._last_month = config.get(CONF_LAST_MONTH, False)
        self._current_year = config.get(CONF_CURRENT_YEAR, True)
        self._last_year = config.get(CONF_LAST_YEAR, False)
        self._add_base_price = config.get(CONF_ADD_BASE_PRICE, False)
        self._scan_interval = timedelta(seconds=int(config.get("scan_interval", DEFAULT_SCAN_INTERVAL)))

        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_sensor"
        self._state: float = 0.0
        self._data: dict[str, Any] = {}
        self._remove_listener = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def native_value(self) -> float:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._data

    async def async_added_to_hass(self) -> None:
        self._remove_listener = async_track_time_interval(
            self.hass, self._async_update_data, self._scan_interval
        )
        await self._async_update_data(None)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener is not None:
            self._remove_listener()

    # ------------------------------------------------------------------ Recorder
    async def _async_get_states(self, start: datetime, end: datetime) -> list:
        """Liest Zustandsänderungen aus dem Recorder."""
        try:
            states_dict: dict = await get_instance(self.hass).async_add_executor_job(
                state_changes_during_period,
                self.hass,
                start,
                end,
                self._source_entity_id,
                False,   # no_attributes
                None,    # limit
                True,    # include_start_time_state
            )
            return states_dict.get(self._source_entity_id, [])
        except Exception as err:
            _LOGGER.warning("Recorder-Fehler beim Lesen des Verlaufs: %s", err)
            return []

    async def _async_get_consumption_split(
        self, start: datetime, end: datetime
    ) -> dict[str, float]:
        """Berechnet Gesamt-, Tag- und Nachtverbrauch für einen Zeitraum."""
        states = await self._async_get_states(start, end)
        if len(states) < 2:
            return {"consumption": 0.0, "day": 0.0, "night": 0.0}

        def _val(state) -> float:
            try:
                return float(state.state)
            except (TypeError, ValueError):
                return 0.0

        total_consumption = max(0.0, _val(states[-1]) - _val(states[0]))
        day_consumption = 0.0
        night_consumption = 0.0

        if not self._night_rate or not self._periods:
            return {"consumption": total_consumption, "day": total_consumption, "night": 0.0}

        prev_value = _val(states[0])
        prev_ts = states[0].last_updated or states[0].last_changed

        for state in states[1:]:
            cur_value = _val(state)
            cur_ts = state.last_updated or state.last_changed
            delta = cur_value - prev_value
            if delta > 0 and cur_ts and prev_ts:
                midpoint = prev_ts + (cur_ts - prev_ts) / 2
                tariff = self._get_tariff_for_timestamp(midpoint)
                ns = _time_from_str(tariff.get("night_start", "22:00")) if tariff else time(22, 0)
                ne = _time_from_str(tariff.get("night_end", "06:00")) if tariff else time(6, 0)
                if _is_night(midpoint, ns, ne):
                    night_consumption += delta
                else:
                    day_consumption += delta
            prev_value = cur_value
            prev_ts = cur_ts

        return {
            "consumption": round(total_consumption, 3),
            "day": round(day_consumption, 3),
            "night": round(night_consumption, 3),
        }

    # ------------------------------------------------------------------ Tariff
    def _get_tariff_for_timestamp(self, timestamp: datetime) -> dict[str, Any] | None:
        if not self._periods:
            return None
        current = self._periods[0]
        for p in self._periods:
            if _parse_date(p["start_date"]) <= timestamp.date():
                current = p
        # night_price darf nicht fehlen
        if not current.get("night_price"):
            current = {**current, "night_price": current["day_price"]}
        return current

    # ------------------------------------------------------------------ Update
    async def _async_update_data(self, _now) -> None:
        """Hauptberechnungsroutine."""
        has_any_period = (
            self._daily or self._previous_day or self._current_week
            or self._previous_week or self._current_month or self._last_month
            or self._current_year or self._last_year or self._periods_calculation
        )
        if not self._periods or not has_any_period:
            self._state = 0.0
            self._data = {}
            self.async_write_ha_state()
            return

        total_costs = 0.0
        total_consumption = 0.0
        attributes: dict[str, Any] = {}

        # ------------------------------------------------ Zeitraum berechnen
        async def _calc(keyword: str, label: str) -> None:
            nonlocal total_costs, total_consumption
            start, end = _get_period_start_end(keyword)
            split = await self._async_get_consumption_split(start, end)
            consumption = split["consumption"]
            tariff = self._get_tariff_for_timestamp(start)
            day_p = float(tariff["day_price"]) if tariff else 0.0
            night_p = float(tariff.get("night_price") or day_p) if tariff else 0.0

            if self._night_rate:
                costs = split["day"] * day_p + split["night"] * night_p
            else:
                costs = consumption * day_p

            if self._add_base_price and tariff:
                base = float(tariff.get("base_price", 0.0))
                if base > 0:
                    days = (end.date() - start.date()).days + 1
                    costs += base / 365 * days

            attributes[f"{label}_consumption"] = round(consumption, 3)
            attributes[f"{label}_costs"] = round(costs, 3)
            if self._daily_consumption:
                attributes[f"{label}_day_consumption"] = round(split["day"], 3)
            if self._nightly_consumption:
                attributes[f"{label}_night_consumption"] = round(split["night"], 3)

            nonlocal total_costs, total_consumption
            total_costs += costs
            total_consumption += consumption

        if self._daily:
            await _calc("today", "today")
        if self._previous_day:
            await _calc("previous_day", "previous_day")
        if self._current_week:
            await _calc("current_week", "current_week")
        if self._previous_week:
            await _calc("previous_week", "previous_week")
        if self._current_month:
            await _calc("current_month", "current_month")
        if self._last_month:
            await _calc("last_month", "last_month")
        if self._current_year:
            await _calc("current_year", "current_year")
        if self._last_year:
            await _calc("last_year", "last_year")

        # ------------------------------------------------ Periodenberechnung
        if self._periods_calculation:
            sorted_periods = sorted(self._periods, key=lambda p: _parse_date(p["start_date"]))
            for i, period in enumerate(sorted_periods):
                begin = _parse_date(period["start_date"])
                if begin is None:
                    continue
                p_start = datetime.combine(begin, time.min, tzinfo=dt_util.now().tzinfo)

                if i + 1 < len(sorted_periods):
                    next_begin = _parse_date(sorted_periods[i + 1]["start_date"])
                    p_end = datetime.combine(next_begin, time.min, tzinfo=dt_util.now().tzinfo) - timedelta(seconds=1)
                else:
                    p_end = dt_util.now()

                split = await self._async_get_consumption_split(p_start, p_end)
                consumption = split["consumption"]
                day_p = float(period["day_price"])
                night_p = float(period.get("night_price") or day_p)

                if self._night_rate:
                    costs = split["day"] * day_p + split["night"] * night_p
                else:
                    costs = consumption * day_p

                if self._add_base_price:
                    base = float(period.get("base_price", 0.0))
                    if base > 0:
                        days = (p_end.date() - p_start.date()).days + 1
                        costs += base / 365 * days

                key = f"period_{begin.isoformat()}"
                attributes[f"{key}_consumption"] = round(consumption, 3)
                attributes[f"{key}_costs"] = round(costs, 3)
                total_costs += costs
                total_consumption += consumption

                if self._balance:
                    # Bilanz = Summe aller Abschläge im Zeitraum – tatsächliche Kosten
                    months = (p_end.date() - p_start.date()).days / 30.44
                    advance_total = float(period.get("advance_payment", 0.0)) * months
                    attributes[f"{key}_balance"] = round(advance_total - costs, 2)

        self._state = round(total_costs, 2)
        attributes["total_consumption"] = round(total_consumption, 3)
        attributes["total_costs"] = round(total_costs, 2)
        self._data = attributes
        self.async_write_ha_state()
        _LOGGER.debug("Energierechner aktualisiert: %.2f €", self._state)
