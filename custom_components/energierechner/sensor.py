"""Sensor-Plattform für Energierechner – individuelle Entitäten pro Zeitraum."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
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
    CONF_METER_TYPE,
    METER_TYPE_FEED_IN,
    DEFAULT_NAME,
    DOMAIN,
)
from .coordinator import EnergierechnerCoordinator

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Metadaten pro Zeitraum
# ---------------------------------------------------------------------------
PERIOD_META = [
    (CONF_DAILY,         "today",         "Heute"),
    (CONF_PREVIOUS_DAY,  "previous_day",  "Gestern"),
    (CONF_CURRENT_WEEK,  "current_week",  "Aktuelle Woche"),
    (CONF_PREVIOUS_WEEK, "previous_week", "Vorherige Woche"),
    (CONF_CURRENT_MONTH, "current_month", "Aktueller Monat"),
    (CONF_LAST_MONTH,    "last_month",    "Letzter Monat"),
    (CONF_CURRENT_YEAR,  "current_year",  "Aktuelles Jahr"),
    (CONF_LAST_YEAR,     "last_year",     "Letztes Jahr"),
]


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Individuelle Sensor-Entitäten aus Config Entry erstellen."""
    config: dict = {**entry.data}
    if entry.options:
        config.update(entry.options)

    coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_config_entry_first_refresh()

    name: str = config.get("name", DEFAULT_NAME)
    entry_id: str = entry.entry_id
    night_rate: bool = config.get(CONF_NIGHT_RATE, False)
    daily_consumption: bool = config.get(CONF_DAILY_CONSUMPTION, False)
    nightly_consumption: bool = config.get(CONF_NIGHTLY_CONSUMPTION, False)

    entities: list[SensorEntity] = []

    # ---- Metadaten basierend auf Zählertyp ermitteln ----
    is_feed_in = config.get(CONF_METER_TYPE) == METER_TYPE_FEED_IN
    
    lbl_cost = "Ertrag" if is_feed_in else "Kosten"
    lbl_cons = "Einspeisung" if is_feed_in else "Verbrauch"
    icon_cons = "mdi:solar-power" if is_feed_in else "mdi:lightning-bolt"

    # ---- Gesamt-Sensoren ------------------------------------------------
    entities.append(EnergierechnerSensor(
        coordinator, entry_id, name,
        data_key="total_costs",
        label=f"Gesamt {lbl_cost}",
        unit="€",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:currency-eur",
    ))
    entities.append(EnergierechnerSensor(
        coordinator, entry_id, name,
        data_key="total_consumption",
        label=f"Gesamt {lbl_cons}",
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon=icon_cons,
    ))

    # ---- Standard-Zeiträume --------------------------------------------
    for flag, key, human in PERIOD_META:
        if not config.get(flag):
            continue

        entities.append(EnergierechnerSensor(
            coordinator, entry_id, name,
            data_key=f"{key}_costs",
            label=f"{human} {lbl_cost}",
            unit="€",
            device_class=SensorDeviceClass.MONETARY,
            state_class=SensorStateClass.TOTAL,
            icon="mdi:currency-eur",
        ))
        entities.append(EnergierechnerSensor(
            coordinator, entry_id, name,
            data_key=f"{key}_consumption",
            label=f"{human} {lbl_cons}",
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            icon=icon_cons,
        ))
        if daily_consumption and night_rate:
            entities.append(EnergierechnerSensor(
                coordinator, entry_id, name,
                data_key=f"{key}_day_consumption",
                label=f"{human} {'Tageinspeisung' if is_feed_in else 'Tagverbrauch'}",
                unit=UnitOfEnergy.KILO_WATT_HOUR,
                device_class=SensorDeviceClass.ENERGY,
                state_class=SensorStateClass.TOTAL_INCREASING,
                icon="mdi:weather-sunny",
            ))
        if nightly_consumption and night_rate:
            entities.append(EnergierechnerSensor(
                coordinator, entry_id, name,
                data_key=f"{key}_night_consumption",
                label=f"{human} {'Nachteinspeisung' if is_feed_in else 'Nachtverbrauch'}",
                unit=UnitOfEnergy.KILO_WATT_HOUR,
                device_class=SensorDeviceClass.ENERGY,
                state_class=SensorStateClass.TOTAL_INCREASING,
                icon="mdi:weather-night",
            ))

    # ---- Tarifperioden --------------------------------------------------
    if config.get(CONF_PERIODS_CALCULATION):
        periods = sorted(
            config.get(CONF_PERIODS, []),
            key=lambda p: dt_util.parse_date(p["start_date"])
        )
        for period in periods:
            start_date = period["start_date"]
            key = f"period_{start_date}"
            human = f"Periode ab {start_date}"

            entities.append(EnergierechnerSensor(
                coordinator, entry_id, name,
                data_key=f"{key}_costs",
                label=f"{human} {lbl_cost}",
                unit="€",
                device_class=SensorDeviceClass.MONETARY,
                state_class=SensorStateClass.TOTAL,
                icon="mdi:currency-eur",
            ))
            entities.append(EnergierechnerSensor(
                coordinator, entry_id, name,
                data_key=f"{key}_consumption",
                label=f"{human} {lbl_cons}",
                unit=UnitOfEnergy.KILO_WATT_HOUR,
                device_class=SensorDeviceClass.ENERGY,
                state_class=SensorStateClass.TOTAL_INCREASING,
                icon=icon_cons,
            ))
            if daily_consumption and night_rate:
                entities.append(EnergierechnerSensor(
                    coordinator, entry_id, name,
                    data_key=f"{key}_day_consumption",
                    label=f"{human} {'Tageinspeisung' if is_feed_in else 'Tagverbrauch'}",
                    unit=UnitOfEnergy.KILO_WATT_HOUR,
                    device_class=SensorDeviceClass.ENERGY,
                    state_class=SensorStateClass.TOTAL_INCREASING,
                    icon="mdi:weather-sunny",
                ))
            if nightly_consumption and night_rate:
                entities.append(EnergierechnerSensor(
                    coordinator, entry_id, name,
                    data_key=f"{key}_night_consumption",
                    label=f"{human} {'Nachteinspeisung' if is_feed_in else 'Nachtverbrauch'}",
                    unit=UnitOfEnergy.KILO_WATT_HOUR,
                    device_class=SensorDeviceClass.ENERGY,
                    state_class=SensorStateClass.TOTAL_INCREASING,
                    icon="mdi:weather-night",
                ))
            if config.get(CONF_BALANCE):
                entities.append(EnergierechnerSensor(
                    coordinator, entry_id, name,
                    data_key=f"{key}_balance",
                    label=f"{human} Bilanz",
                    unit="€",
                    device_class=SensorDeviceClass.MONETARY,
                    state_class=SensorStateClass.MEASUREMENT,
                    icon="mdi:scale-balance",
                ))

    # ---- Alle Monate des aktuellen Jahres (Jan–Dez) ----------------------
    MONTH_META = [
        ("januar",     "Januar"),
        ("februar",    "Februar"),
        ("maerz",      "März"),
        ("april",      "April"),
        ("mai",        "Mai"),
        ("juni",       "Juni"),
        ("juli",       "Juli"),
        ("august",     "August"),
        ("september",  "September"),
        ("oktober",    "Oktober"),
        ("november",   "November"),
        ("dezember",   "Dezember"),
    ]
    for key, label in MONTH_META:
        entities.append(EnergierechnerSensor(
            coordinator, entry_id, name,
            data_key=f"month_{key}_consumption",
            label=f"{label} {lbl_cons}",
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.MEASUREMENT,
            icon=icon_cons,
        ))
        entities.append(EnergierechnerSensor(
            coordinator, entry_id, name,
            data_key=f"month_{key}_costs",
            label=f"{label} {lbl_cost}",
            unit="€",
            device_class=SensorDeviceClass.MONETARY,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:currency-eur",
        ))

    # ---- Alle Wochentage der aktuellen Woche (Mo–So) --------------------
    WEEKDAY_META = [
        ("montag",     "Montag"),
        ("dienstag",   "Dienstag"),
        ("mittwoch",   "Mittwoch"),
        ("donnerstag", "Donnerstag"),
        ("freitag",    "Freitag"),
        ("samstag",    "Samstag"),
        ("sonntag",    "Sonntag"),
    ]
    for key, label in WEEKDAY_META:
        entities.append(EnergierechnerSensor(
            coordinator, entry_id, name,
            data_key=f"weekday_{key}_consumption",
            label=f"{label} {lbl_cons}",
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.MEASUREMENT,
            icon=icon_cons,
        ))
        entities.append(EnergierechnerSensor(
            coordinator, entry_id, name,
            data_key=f"weekday_{key}_costs",
            label=f"{label} {lbl_cost}",
            unit="€",
            device_class=SensorDeviceClass.MONETARY,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:currency-eur",
        ))

    async_add_entities(entities)


# ---------------------------------------------------------------------------
# Sensor-Entität
# ---------------------------------------------------------------------------

class EnergierechnerSensor(CoordinatorEntity, SensorEntity):
    """Eine einzelne Energierechner-Sensor-Entität."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EnergierechnerCoordinator,
        entry_id: str,
        device_name: str,
        data_key: str,
        label: str,
        unit: str,
        device_class: SensorDeviceClass,
        state_class: SensorStateClass,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._data_key = data_key
        self._label = label
        self._device_name = device_name
        self._entry_id = entry_id

        self._attr_name = label
        # unique_id stabil: entry_id + data_key (unabhängig vom Sensor-Namen)
        self._attr_unique_id = f"{entry_id}_{data_key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_icon = icon

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=self._device_name,
            manufacturer="PowderK",
            model="Energierechner",
            configuration_url="https://github.com/PowderK/Energierechner-HA",
        )

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._data_key)
