"""Sensor platform for Energierechner."""
from __future__ import annotations

import logging
from datetime import datetime, date, time, timedelta
from typing import Any

import voluptuous as vol
from homeassistant.components import history
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import (ATTR_FRIENDLY_NAME, CONF_ENTITY_ID, CONF_NAME,
                                 CONF_SCAN_INTERVAL, ENERGY_KILO_WATT_HOUR)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import config_validation as cv
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
)

_LOGGER = logging.getLogger(__name__)

PERIOD_SCHEMA = vol.Schema({
    vol.Required("start_date"): cv.string,
    vol.Required("day_price"): vol.Coerce(float),
    vol.Optional("night_price"): vol.Coerce(float),
    vol.Optional("base_price", default=0.0): vol.Coerce(float),
    vol.Optional("advance_payment", default=0.0): vol.Coerce(float),
    vol.Optional("deductions_per_year", default=0.0): vol.Coerce(float),
    vol.Optional("night_start", default="22:00"): cv.time,
    vol.Optional("night_end", default="06:00"): cv.time,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_SOURCE_ENTITY): cv.entity_id,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PERIODS, default=[]): vol.All(cv.ensure_list, [PERIOD_SCHEMA]),
    vol.Optional(CONF_ACTIVE, default=True): cv.boolean,
    vol.Optional(CONF_NIGHT_RATE, default=False): cv.boolean,
    vol.Optional(CONF_DAILY_CONSUMPTION, default=False): cv.boolean,
    vol.Optional(CONF_NIGHTLY_CONSUMPTION, default=False): cv.boolean,
    vol.Optional(CONF_PERIODS_CALCULATION, default=False): cv.boolean,
    vol.Optional(CONF_BALANCE, default=False): cv.boolean,
    vol.Optional(CONF_DAILY, default=False): cv.boolean,
    vol.Optional(CONF_PREVIOUS_DAY, default=False): cv.boolean,
    vol.Optional(CONF_CURRENT_WEEK, default=False): cv.boolean,
    vol.Optional(CONF_PREVIOUS_WEEK, default=False): cv.boolean,
    vol.Optional(CONF_CURRENT_MONTH, default=False): cv.boolean,
    vol.Optional(CONF_LAST_MONTH, default=False): cv.boolean,
    vol.Optional(CONF_CURRENT_YEAR, default=False): cv.boolean,
    vol.Optional(CONF_LAST_YEAR, default=False): cv.boolean,
    vol.Optional(CONF_ADD_BASE_PRICE, default=False): cv.boolean,
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.positive_int,
})


def _parse_date(iso_date: str) -> date:
    return dt_util.parse_date(iso_date)


def _is_night(timestamp: datetime, night_start: time, night_end: time) -> bool:
    if night_start < night_end:
        return night_start <= timestamp.time() < night_end
    return timestamp.time() >= night_start or timestamp.time() < night_end


def _to_datetime(val: str | datetime) -> datetime:
    if isinstance(val, datetime):
        return val
    return dt_util.parse_datetime(val)


def _get_period_start_end(period_keyword: str) -> tuple[datetime, datetime]:
    today = dt_util.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if period_keyword == "today":
        start = today
        end = today + timedelta(days=1) - timedelta(seconds=1)
    elif period_keyword == "previous_day":
        start = today - timedelta(days=1)
        end = today - timedelta(seconds=1)
    elif period_keyword == "current_week":
        start = (today - timedelta(days=today.weekday()))
        end = start + timedelta(days=7) - timedelta(seconds=1)
    elif period_keyword == "previous_week":
        start = (today - timedelta(days=today.weekday() + 7))
        end = start + timedelta(days=7) - timedelta(seconds=1)
    elif period_keyword == "current_month":
        start = today.replace(day=1)
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        end = next_month - timedelta(seconds=1)
    elif period_keyword == "last_month":
        start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        next_month = today.replace(day=1)
        end = next_month - timedelta(seconds=1)
    elif period_keyword == "current_year":
        start = today.replace(month=1, day=1)
        end = today.replace(month=12, day=31, hour=23, minute=59, second=59)
    elif period_keyword == "last_year":
        start = today.replace(year=today.year - 1, month=1, day=1)
        end = today.replace(year=today.year - 1, month=12, day=31, hour=23, minute=59, second=59)
    else:
        raise ValueError("invalid period keyword")
    return start, end


async def async_setup_platform(hass: HomeAssistant, config: dict, async_add_entities, discovery_info=None):
    if not config[CONF_ACTIVE]:
        _LOGGER.debug("Energierechner is disabled by configuration")
        return

    entity = EnergierechnerSensor(config)
    async_add_entities([entity], True)


class EnergierechnerSensor(SensorEntity):
    """Energierechner sensor entity."""

    _attr_should_poll = False

    def __init__(self, config: dict):
        self._name = config[CONF_NAME]
        self._source_entity_id = config[CONF_SOURCE_ENTITY]
        self._periods = sorted(config[CONF_PERIODS], key=lambda p: _parse_date(p["start_date"]))
        self._night_rate = config[CONF_NIGHT_RATE]
        self._daily_consumption = config[CONF_DAILY_CONSUMPTION]
        self._nightly_consumption = config[CONF_NIGHTLY_CONSUMPTION]
        self._periods_calculation = config[CONF_PERIODS_CALCULATION]
        self._balance = config[CONF_BALANCE]
        self._daily = config[CONF_DAILY]
        self._previous_day = config[CONF_PREVIOUS_DAY]
        self._current_week = config[CONF_CURRENT_WEEK]
        self._previous_week = config[CONF_PREVIOUS_WEEK]
        self._current_month = config[CONF_CURRENT_MONTH]
        self._last_month = config[CONF_LAST_MONTH]
        self._current_year = config[CONF_CURRENT_YEAR]
        self._last_year = config[CONF_LAST_YEAR]
        self._add_base_price = config[CONF_ADD_BASE_PRICE]
        self._scan_interval = timedelta(seconds=config[CONF_SCAN_INTERVAL])

        self._state = 0.0
        self._attr_native_unit_of_measurement = "€"
        self._attr_icon = "mdi:calculator"
        self._data = {}
        self._remove_listener = None

    async def async_added_to_hass(self):
        self._remove_listener = async_track_time_interval(
            self.hass, self._async_update_data, self._scan_interval
        )
        await self._async_update_data(None)

    async def async_will_remove_from_hass(self):
        if self._remove_listener is not None:
            self._remove_listener()

    @property
    def name(self) -> str:
        return self._name

    @property
    def native_value(self) -> float:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._data

    async def _async_get_consumption_split(self, start: datetime, end: datetime) -> dict[str, float]:
        states = await history.get_state_changes(self.hass, start, end, self._source_entity_id)
        if not states:
            return {"consumption": 0.0, "day": 0.0, "night": 0.0}

        # Take first and last to get total consumption
        def _safe_state_value(state: State) -> float:
            try:
                return float(state.state)
            except (TypeError, ValueError):
                return 0.0

        total_consumption = max(0.0, _safe_state_value(states[-1]) - _safe_state_value(states[0]))
        day_consumption = 0.0
        night_consumption = 0.0

        if not self._periods or not self._night_rate:
            return {"consumption": total_consumption, "day": total_consumption, "night": 0.0}

        # split by averaged interval midpoint
        prev_state = states[0]
        prev_value = _safe_state_value(prev_state)
        prev_timestamp = prev_state.last_updated or prev_state.last_changed

        for state in states[1:]:
            now_value = _safe_state_value(state)
            now_timestamp = state.last_updated or state.last_changed
            delta = now_value - prev_value
            if delta > 0 and now_timestamp and prev_timestamp:
                midpoint = prev_timestamp + (now_timestamp - prev_timestamp) / 2
                period = self._get_tariff_for_timestamp(midpoint)
                night_start = period.get("night_start") if period else time(22, 0)
                night_end = period.get("night_end") if period else time(6, 0)
                if _is_night(midpoint, night_start, night_end):
                    night_consumption += delta
                else:
                    day_consumption += delta
            prev_state = state
            prev_value = now_value
            prev_timestamp = now_timestamp

        if not self._night_rate:
            day_consumption = total_consumption
            night_consumption = 0.0

        return {
            "consumption": total_consumption,
            "day": round(day_consumption, 3),
            "night": round(night_consumption, 3),
        }

    def _get_tariff_for_timestamp(self, timestamp: datetime) -> dict[str, Any] | None:
        if not self._periods:
            return None

        sorted_periods = sorted(self._periods, key=lambda p: _parse_date(p["start_date"]))

        current_period = sorted_periods[0]
        for p in sorted_periods:
            if _parse_date(p["start_date"]) <= timestamp.date():
                current_period = p
            else:
                break
        if current_period.get("night_price", 0.0) == 0.0:
            current_period["night_price"] = current_period["day_price"]
        return current_period

    async def _async_update_data(self, now):
        if not self._periods or not self._daily and not self._previous_day and not self._current_week and not self._previous_week and not self._current_month and not self._last_month and not self._current_year and not self._last_year and not self._periods_calculation:
            self._state = 0.0
            self._data = {}
            return

        total_costs = 0.0
        total_consumption = 0.0
        attributes: dict[str, Any] = {}

        async def calculate_for_period(keyword: str, label: str):
            nonlocal total_costs, total_consumption
            start, end = _get_period_start_end(keyword)
            consumption_block = await self._async_get_consumption_split(start, end)
            period_costs, period_consumption = 0.0, consumption_block["consumption"]

            # price by midpoint of period
            if self._periods:
                period_tariff = self._get_tariff_for_timestamp(start)
                if period_tariff:
                    day_price = float(period_tariff["day_price"])
                    night_price = float(period_tariff.get("night_price", day_price))
                else:
                    day_price = 0.0
                    night_price = 0.0
            else:
                day_price = 0.0
                night_price = 0.0

            if self._night_rate:
                period_costs = (consumption_block["day"] * day_price) + (consumption_block["night"] * night_price)
            else:
                period_costs = period_consumption * day_price

            if self._add_base_price and self._periods:
                if period_tariff:
                    base_price = float(period_tariff.get("base_price", 0.0))
                    if base_price > 0:
                        daycount = (end.date() - start.date()).days + 1
                        period_costs += base_price / 365 * daycount

            attributes[f"{label}_consumption"] = round(period_consumption, 3)
            attributes[f"{label}_costs"] = round(period_costs, 3)
            total_costs += period_costs
            total_consumption += period_consumption

        if self._daily:
            await calculate_for_period("today", "today")
        if self._previous_day:
            await calculate_for_period("previous_day", "previous_day")
        if self._current_week:
            await calculate_for_period("current_week", "current_week")
        if self._previous_week:
            await calculate_for_period("previous_week", "previous_week")
        if self._current_month:
            await calculate_for_period("current_month", "current_month")
        if self._last_month:
            await calculate_for_period("last_month", "last_month")
        if self._current_year:
            await calculate_for_period("current_year", "current_year")
        if self._last_year:
            await calculate_for_period("last_year", "last_year")

        if self._periods_calculation and self._periods:
            for period in self._periods:
                begin = dt_util.parse_date(period["start_date"])
                if begin is None:
                    continue
                start = datetime.combine(begin, time.min)
                next_period = None
                candidates = [p for p in self._periods if _parse_date(p["start_date"]) > begin]
                if candidates:
                    next_begin = min(_parse_date(p["start_date"]) for p in candidates)
                    next_period = datetime.combine(next_begin, time.min)
                end = (next_period - timedelta(seconds=1)) if next_period else dt_util.now()

                consumption_block = await self._async_get_consumption_split(start, end)
                day_price = float(period["day_price"])
                night_price = float(period.get("night_price") or day_price)

                period_costs = (consumption_block["day"] * day_price) + (consumption_block["night"] * night_price)
                if self._add_base_price:
                    daycount = (end.date() - start.date()).days + 1
                    period_costs += float(period.get("base_price", 0.0)) / 365 * daycount

                key = f"period_{begin.isoformat()}"
                attributes[f"{key}_consumption"] = round(consumption_block["consumption"], 3)
                attributes[f"{key}_costs"] = round(period_costs, 3)
                total_costs += period_costs
                total_consumption += consumption_block["consumption"]

                if self._balance:
                    balance = float(period.get("advance_payment", 0.0)) * float(period.get("deductions_per_year", 0.0)) - period_costs
                    attributes[f"{key}_balance"] = round(balance, 2)

        self._state = round(total_costs, 2)
        attributes["total_consumption"] = round(total_consumption, 3)
        attributes["total_costs"] = round(total_costs, 2)
        self._data = attributes
        self.async_write_ha_state()
