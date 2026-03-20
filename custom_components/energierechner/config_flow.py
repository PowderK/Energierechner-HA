"""Config Flow für die Energierechner Integration."""
from __future__ import annotations

import yaml
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN


class EnergierechnerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Mehrstufiger Config Flow für Energierechner."""

    VERSION = 1

    def __init__(self):
        self._data: dict = {}

    # ------------------------------------------------------------------ Step 1
    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            self._data.update(user_input)
            self._data["scan_interval"] = int(user_input.get("scan_interval", 600))
            return await self.async_step_features()

        schema = vol.Schema({
            vol.Required("name", default="Energierechner"): selector.TextSelector(),
            vol.Required("source_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional("scan_interval", default=600): selector.NumberSelector(
                selector.NumberSelectorConfig(min=60, max=86400, step=60, mode="box")
            ),
        })
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    # ------------------------------------------------------------------ Step 2
    async def async_step_features(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_periods()

        schema = _features_schema({})
        return self.async_show_form(step_id="features", data_schema=schema)

    # ------------------------------------------------------------------ Step 3
    async def async_step_periods(self, user_input=None):
        errors = {}
        if user_input is not None:
            periods, err = _parse_periods_yaml(user_input.get("periods_yaml", ""))
            if err:
                errors["periods_yaml"] = "invalid_yaml"
            else:
                self._data["periods"] = periods
                return self.async_create_entry(
                    title=self._data["name"],
                    data=self._data,
                )

        schema = vol.Schema({
            vol.Optional("periods_yaml", default=_default_periods_yaml()): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True)
            ),
        })
        return self.async_show_form(
            step_id="periods",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EnergierechnerOptionsFlow(config_entry)


# ---------------------------------------------------------------------------
class EnergierechnerOptionsFlow(config_entries.OptionsFlow):
    """Options Flow zum nachträglichen Bearbeiten der Konfiguration."""

    def __init__(self, config_entry):
        self._entry = config_entry
        self._data: dict = dict(config_entry.data)

    async def async_step_init(self, user_input=None):
        return await self.async_step_features()

    async def async_step_features(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_periods()

        schema = _features_schema(self._entry.data)
        return self.async_show_form(step_id="features", data_schema=schema)

    async def async_step_periods(self, user_input=None):
        errors = {}
        if user_input is not None:
            periods, err = _parse_periods_yaml(user_input.get("periods_yaml", ""))
            if err:
                errors["periods_yaml"] = "invalid_yaml"
            else:
                self._data["periods"] = periods
                return self.async_create_entry(title="", data=self._data)

        existing = self._entry.data.get("periods", [])
        default_yaml = yaml.dump(existing, allow_unicode=True, default_flow_style=False) if existing else _default_periods_yaml()
        schema = vol.Schema({
            vol.Optional("periods_yaml", default=default_yaml): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True)
            ),
        })
        return self.async_show_form(
            step_id="periods",
            data_schema=schema,
            errors=errors,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _features_schema(defaults: dict) -> vol.Schema:
    def d(key, fallback=False):
        return defaults.get(key, fallback)

    return vol.Schema({
        vol.Optional("night_rate",           default=d("night_rate")):           bool,
        vol.Optional("add_base_price",       default=d("add_base_price")):       bool,
        vol.Optional("daily_consumption",    default=d("daily_consumption")):    bool,
        vol.Optional("nightly_consumption",  default=d("nightly_consumption")):  bool,
        vol.Optional("periods_calculation",  default=d("periods_calculation", True)): bool,
        vol.Optional("balance",              default=d("balance")):              bool,
        vol.Optional("daily",               default=d("daily",        True)):  bool,
        vol.Optional("previous_day",         default=d("previous_day", True)):  bool,
        vol.Optional("current_week",         default=d("current_week", True)):  bool,
        vol.Optional("previous_week",        default=d("previous_week")):       bool,
        vol.Optional("current_month",        default=d("current_month", True)): bool,
        vol.Optional("last_month",           default=d("last_month")):          bool,
        vol.Optional("current_year",         default=d("current_year", True)):  bool,
        vol.Optional("last_year",            default=d("last_year")):           bool,
    })


def _parse_periods_yaml(raw: str):
    """Parst YAML-Text zu einer Perioden-Liste. Gibt (list, error_or_None) zurück."""
    if not raw.strip():
        return [], None
    try:
        result = yaml.safe_load(raw)
        if not isinstance(result, list):
            return [], "not_a_list"
        return result, None
    except yaml.YAMLError:
        return [], "invalid_yaml"


def _default_periods_yaml() -> str:
    return (
        "- start_date: \"2024-01-01\"\n"
        "  day_price: 0.35\n"
        "  night_price: 0.22\n"
        "  base_price: 140.0\n"
        "  advance_payment: 65.0\n"
        "  night_start: \"22:00\"\n"
        "  night_end: \"06:00\"\n"
    )
