"""DataUpdateCoordinator für Energierechner – zentrale Datenbeschaffung."""
from __future__ import annotations

import logging
from datetime import datetime, date, time, timedelta
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.history import state_changes_during_period
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ADD_BASE_PRICE,
    CONF_BALANCE,
    CONF_CURRENT_MONTH,
    CONF_CURRENT_WEEK,
    CONF_CURRENT_YEAR,
    CONF_DAILY,
    CONF_DAILY_CONSUMPTION,
    CONF_LAST_MONTH,
    CONF_LAST_YEAR,
    CONF_NIGHTLY_CONSUMPTION,
    CONF_NIGHT_RATE,
    CONF_PERIODS,
    CONF_PERIODS_CALCULATION,
    CONF_PREVIOUS_DAY,
    CONF_PREVIOUS_WEEK,
    CONF_SOURCE_ENTITY,
    CONF_SOURCE_UNIT,
    SOURCE_UNIT_WH,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Datum / Zeit Helpers
# ---------------------------------------------------------------------------

def _parse_date(iso_date: str) -> date:
    return dt_util.parse_date(iso_date)


def _time_from_str(val) -> time:
    if isinstance(val, time):
        return val
    if isinstance(val, str):
        parts = val.split(":")
        return time(int(parts[0]), int(parts[1]))
    return time(22, 0)


def _is_night(ts: datetime, night_start: time, night_end: time) -> bool:
    t = ts.time().replace(second=0, microsecond=0)
    if night_start < night_end:
        return night_start <= t < night_end
    return t >= night_start or t < night_end


def _get_period_bounds(keyword: str) -> tuple[datetime, datetime]:
    now = dt_util.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if keyword == "today":
        return today, today + timedelta(days=1) - timedelta(seconds=1)
    if keyword == "previous_day":
        s = today - timedelta(days=1)
        return s, today - timedelta(seconds=1)
    if keyword == "current_week":
        s = today - timedelta(days=today.weekday())
        return s, s + timedelta(days=7) - timedelta(seconds=1)
    if keyword == "previous_week":
        s = today - timedelta(days=today.weekday() + 7)
        return s, s + timedelta(days=7) - timedelta(seconds=1)
    if keyword == "current_month":
        s = today.replace(day=1)
        nm = (s.replace(day=28) + timedelta(days=4)).replace(day=1)
        return s, nm - timedelta(seconds=1)
    if keyword == "last_month":
        s = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        return s, today.replace(day=1) - timedelta(seconds=1)
    if keyword == "current_year":
        s = today.replace(month=1, day=1)
        return s, today.replace(month=12, day=31, hour=23, minute=59, second=59)
    if keyword == "last_year":
        s = today.replace(year=today.year - 1, month=1, day=1)
        e = today.replace(year=today.year - 1, month=12, day=31, hour=23, minute=59, second=59)
        return s, e
    raise ValueError(f"Unbekanntes Zeitraum-Schlüsselwort: {keyword}")


# ---------------------------------------------------------------------------
# Coordinator
# ---------------------------------------------------------------------------

class EnergierechnerCoordinator(DataUpdateCoordinator):
    """Holt alle Energiedaten aus dem HA Recorder und berechnet Kosten."""

    def __init__(self, hass: HomeAssistant, config: dict, entry_id: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry_id}",
            update_interval=timedelta(seconds=int(config.get("scan_interval", DEFAULT_SCAN_INTERVAL))),
        )
        self._config = config
        self._entry_id = entry_id
        self._source = config[CONF_SOURCE_ENTITY]
        self._night_rate: bool = config.get(CONF_NIGHT_RATE, False)
        self._add_base_price: bool = config.get(CONF_ADD_BASE_PRICE, False)
        self._balance: bool = config.get(CONF_BALANCE, False)
        self._daily_consumption: bool = config.get(CONF_DAILY_CONSUMPTION, False)
        self._nightly_consumption: bool = config.get(CONF_NIGHTLY_CONSUMPTION, False)
        # Einheiten-Konvertierung: Wh-Sensor → Faktor 0.001 (÷ 1000)
        self._unit_factor: float = 0.001 if config.get(CONF_SOURCE_UNIT) == SOURCE_UNIT_WH else 1.0
        self._periods: list[dict] = sorted(
            config.get(CONF_PERIODS, []),
            key=lambda p: _parse_date(p["start_date"])
        )

    # ------------------------------------------------------------------ Recorder
    async def _get_states(self, start: datetime, end: datetime) -> list:
        try:
            result: dict = await get_instance(self.hass).async_add_executor_job(
                state_changes_during_period,
                self.hass,
                start,
                end,
                self._source,
                False,   # no_attributes
                None,    # limit
                True,    # include_start_time_state
            )
            return result.get(self._source, [])
        except Exception as err:
            _LOGGER.warning("Recorder-Fehler: %s", err)
            return []

    async def _consumption_split(self, start: datetime, end: datetime, label: str = "") -> dict[str, float]:
        from homeassistant.components.recorder.statistics import statistics_during_period
        
        # 1. Zuerst Langzeit-Archiv (Long-Term Statistics) probieren (mit 1h Puffer davor)
        try:
            stat_res = await get_instance(self.hass).async_add_executor_job(
                statistics_during_period,
                self.hass,
                start - timedelta(hours=1),
                end,
                {self._source},
                "hour",
                None,
                {"sum", "state"}
            )
            raw_stats = stat_res.get(self._source, [])
        except Exception as err:
            _LOGGER.warning("[%s] Fehler beim LTS-Abruf: %s", label, err)
            raw_stats = []

        valid_points = []
        for s in raw_stats:
            try:
                # "sum" bevorzugen, da es bei Resets automatisch korrigiert wird
                raw_val = s.get("sum") if s.get("sum") is not None else s.get("state")
                if raw_val is None:
                    continue
                val = float(raw_val)
                
                ts_raw = s.get("start")
                if isinstance(ts_raw, (int, float)):
                    if ts_raw > 1e11:  # Millisekunden
                        ts = dt_util.utc_from_timestamp(ts_raw / 1000)
                    else:
                        ts = dt_util.utc_from_timestamp(ts_raw)
                else:
                    ts = ts_raw
                if not getattr(ts, "tzinfo", None):
                    ts = ts.replace(tzinfo=dt_util.UTC)
                
                valid_points.append({"ts": dt_util.as_local(ts), "val": val})
            except (TypeError, ValueError):
                pass
        
        _LOGGER.debug("[%s] LTS lieferte %d gültige Punkte", label, len(valid_points))

        # 2. Fallback auf reguläre History (states), falls LTS nicht verfügbar oder leer
        if len(valid_points) < 2:
            _LOGGER.debug("[%s] Zu wenige LTS-Punkte. Fallback auf Kurzzeit-History...", label)
            states = await self._get_states(start, end)
            valid_points = []
            for s in states:
                try:
                    ts = s.last_updated or s.last_changed
                    valid_points.append({"ts": dt_util.as_local(ts), "val": float(s.state)})
                except (TypeError, ValueError):
                    pass
            _LOGGER.debug("[%s] History lieferte %d gültige Punkte", label, len(valid_points))

        if len(valid_points) < 2:
            _LOGGER.debug("[%s] Abbruch - Zeitraum liefert insg. nur %d Punkte", label, len(valid_points))
            return {
                "total": 0.0, 
                "day": 0.0, 
                "night": 0.0, 
                "first_ts": start, 
                "last_ts": end
            }

        first_val = valid_points[0]["val"]
        last_val = valid_points[-1]["val"]
        total = max(0.0, (last_val - first_val) * self._unit_factor)
        
        _LOGGER.debug("[%s] Erster Wert: %f (%s), Letzter Wert: %f (%s) -> Diff: %f", 
                      label, first_val, valid_points[0]["ts"], last_val, valid_points[-1]["ts"], total)

        if not self._night_rate or not self._periods:
            return {
                "total": total, 
                "day": total, 
                "night": 0.0, 
                "first_ts": valid_points[0]["ts"], 
                "last_ts": valid_points[-1]["ts"]
            }

        day_kwh = 0.0
        night_kwh = 0.0
        prev_val = valid_points[0]["val"]
        prev_ts = valid_points[0]["ts"]

        for pt in valid_points[1:]:
            cur_val = pt["val"]
            cur_ts = pt["ts"]
            delta = (cur_val - prev_val) * self._unit_factor
            if delta > 0:
                mid = prev_ts + (cur_ts - prev_ts) / 2
                tariff = self._tariff_at(mid)
                ns = _time_from_str(tariff.get("night_start", "22:00")) if tariff else time(22, 0)
                ne = _time_from_str(tariff.get("night_end", "06:00")) if tariff else time(6, 0)
                
                if _is_night(mid, ns, ne):
                    night_kwh += delta
                else:
                    day_kwh += delta
            prev_val = cur_val
            prev_ts = cur_ts

        _LOGGER.debug("[%s] Tag kWh: %f, Nacht kWh: %f, Total(Berechnet): %f", 
                      label, day_kwh, night_kwh, total)
        return {
            "total": round(total, 3), 
            "day": round(day_kwh, 3), 
            "night": round(night_kwh, 3),
            "first_ts": valid_points[0]["ts"],
            "last_ts": valid_points[-1]["ts"]
        }

    def _tariff_at(self, ts: datetime) -> dict | None:
        if not self._periods:
            return None
        current = self._periods[0]
        for p in self._periods:
            if _parse_date(p["start_date"]) <= ts.date():
                current = p
        if not current.get("night_price"):
            current = {**current, "night_price": current["day_price"]}
        return current

    def _costs(self, split: dict[str, float], tariff: dict | None, days: int) -> float:
        day_p = float(tariff["day_price"]) if tariff else 0.0
        night_p = float(tariff.get("night_price") or day_p) if tariff else 0.0
        if self._night_rate:
            cost = split["day"] * day_p + split["night"] * night_p
        else:
            cost = split["total"] * day_p
        if self._add_base_price and tariff:
            base = float(tariff.get("base_price", 0.0))
            if base > 0:
                cost += base / 365 * days
        return round(cost, 3)

    # ------------------------------------------------------------------ Main update
    async def _async_update_data(self) -> dict[str, Any]:
        cfg = self._config
        data: dict[str, Any] = {}
        total_costs = 0.0
        total_kwh = 0.0

        # ---- Standard-Zeiträume ----------------------------------------
        period_flags = [
            (CONF_DAILY,         "today",         "today"),
            (CONF_PREVIOUS_DAY,  "previous_day",  "previous_day"),
            (CONF_CURRENT_WEEK,  "current_week",  "current_week"),
            (CONF_PREVIOUS_WEEK, "previous_week", "previous_week"),
            (CONF_CURRENT_MONTH, "current_month", "current_month"),
            (CONF_LAST_MONTH,    "last_month",    "last_month"),
            (CONF_CURRENT_YEAR,  "current_year",  "current_year"),
            (CONF_LAST_YEAR,     "last_year",     "last_year"),
        ]

        for flag, keyword, label in period_flags:
            if not cfg.get(flag):
                continue
            start, end = _get_period_bounds(keyword)
            _LOGGER.debug("=== Starte Berechnung für %s (%s bis %s) ===", label, start, end)
            
            split = await self._consumption_split(start, end, label=label)
            tariff = self._tariff_at(start)
            _LOGGER.debug("[%s] Tarif genutzt: %s", label, tariff)
            
            days = (end.date() - start.date()).days + 1
            cost = self._costs(split, tariff, days)
            _LOGGER.debug("[%s] Kosten kalkuliert: %f (Tage berechnet: %d)", label, cost, days)

            data[f"{label}_consumption"] = split["total"]
            data[f"{label}_costs"] = cost
            if self._daily_consumption:
                data[f"{label}_day_consumption"] = split["day"]
            if self._nightly_consumption:
                data[f"{label}_night_consumption"] = split["night"]

        # ---- Periodenberechnung & Globales Total ------------------------
        # Globales Total basiert auf der kompletten Langzeithistorie, um nichts
        # zu verlieren, falls der erste Tarif erst spät startet.
        if cfg.get(CONF_PERIODS_CALCULATION) and self._periods:
            lifetime_start = dt_util.utc_from_timestamp(0).replace(tzinfo=dt_util.UTC)
            
            # 1. Daten VOR der allerersten Periode (falls der Zähler schon länger existiert)
            first_begin = _parse_date(self._periods[0]["start_date"])
            tz = dt_util.now().tzinfo
            first_p_start = datetime.combine(first_begin, time.min).replace(tzinfo=tz)
            
            if first_p_start > lifetime_start:
                _LOGGER.debug(
                    "=== Starte Berechnung für Vor-Perioden (EPOCH bis %s) ===", 
                    first_p_start
                )
                pre_split = await self._consumption_split(
                    lifetime_start, 
                    first_p_start - timedelta(seconds=1), 
                    label="pre_lifetime"
                )
                
                if pre_split["total"] > 0:
                    pre_tariff = {**self._periods[0]}
                    if not pre_tariff.get("night_price"):
                        pre_tariff["night_price"] = pre_tariff["day_price"]
                    
                    real_start = pre_split.get("first_ts", lifetime_start).date()
                    real_end = pre_split.get("last_ts", first_p_start).date()
                    days = max(1, (real_end - real_start).days + 1)
                    
                    pre_cost = self._costs(pre_split, pre_tariff, days)
                    total_costs += pre_cost
                    total_kwh += pre_split["total"]
                    _LOGGER.debug(
                        "[pre_lifetime] Verbrauch: %f kWh, Kosten: %f € (Tage berechnet: %d)", 
                        pre_split["total"], pre_cost, days
                    )

            # 2. Reguläre Perioden-Schleife
            for i, period in enumerate(self._periods):
                begin = _parse_date(period["start_date"])
                if not begin:
                    continue
                p_start = datetime.combine(begin, time.min).replace(tzinfo=tz)
                if i + 1 < len(self._periods):
                    next_begin = _parse_date(self._periods[i + 1]["start_date"])
                    p_end = datetime.combine(next_begin, time.min).replace(tzinfo=tz) - timedelta(seconds=1)
                else:
                    p_end = dt_util.now()

                _LOGGER.debug("=== Starte Berechnung für Tarifperiode ab %s (%s bis %s) ===", begin.isoformat(), p_start, p_end)
                split = await self._consumption_split(p_start, p_end, label=f"period_{begin.isoformat()}")
                
                tariff = {**period}
                if not tariff.get("night_price"):
                    tariff["night_price"] = tariff["day_price"]
                
                # Exakte Tage aus dem tatsächlich ermittelten Datensatz oder Zeitraum
                real_start = split.get("first_ts", p_start).date()
                real_end = split.get("last_ts", p_end).date()
                days = max(1, (real_end - real_start).days + 1)
                
                _LOGGER.debug("[period_%s] Tarif genutzt: %s", begin.isoformat(), tariff)
                cost = self._costs(split, tariff, days)
                _LOGGER.debug(
                    "[period_%s] Kosten kalkuliert: %f (Tage berechnet: %d)", 
                    begin.isoformat(), cost, days
                )

                key = f"period_{begin.isoformat()}"
                data[f"{key}_consumption"] = split["total"]
                data[f"{key}_costs"] = cost
                if self._daily_consumption:
                    data[f"{key}_day_consumption"] = split["day"]
                if self._nightly_consumption:
                    data[f"{key}_night_consumption"] = split["night"]
                if self._balance:
                    months = (p_end.date() - p_start.date()).days / 30.44
                    advance = float(period.get("advance_payment", 0.0)) * months
                    data[f"{key}_balance"] = round(advance - cost, 2)
                    
                total_costs += cost
                total_kwh += split["total"]
                
        else:
            # Gar keine Perioden konfiguriert -> Wir holen 
            # die absolute Lifetime als Total.
            _LOGGER.debug("Keine Perioden -> hole gesamte Langzeithistorie")
            lifetime_start = dt_util.utc_from_timestamp(0).replace(
                tzinfo=dt_util.now().tzinfo
            )
            lifetime_end = dt_util.now()
            split = await self._consumption_split(
                lifetime_start, 
                lifetime_end, 
                label="lifetime_fallback"
            )
            total_kwh += split["total"]
            # Kosten lassen sich ohne Tarif nicht ermitteln, bleiben folglich 0.

        data["total_costs"] = round(total_costs, 2)
        data["total_consumption"] = round(total_kwh, 3)
        
        _LOGGER.debug(
            "Energierechner Update abgeschlossen: %.2f €, %.3f kWh", 
            total_costs, 
            total_kwh
        )
        _LOGGER.debug("Gesammelte Daten für Sensoren: %s", data)
        return data
