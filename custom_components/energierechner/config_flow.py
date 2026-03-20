"""Config Flow für die Energierechner Integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .const import DOMAIN


class EnergierechnerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Mehrstufiger Config Flow für Energierechner."""

    VERSION = 1

    def __init__(self):
        self._data: dict = {"periods": []}
        self._edit_index: int | None = None

    # ---- 1. SETUP: Basisdaten ----------------------------------------------------
    async def async_step_user(self, user_input=None):
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
        return self.async_show_form(step_id="user", data_schema=schema)

    # ---- 2. SETUP: Funktionen ---------------------------------------------------
    async def async_step_features(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            # Nach den Features müssen wir die erste Periode anlegen
            self._edit_index = None
            return await self.async_step_edit_period()

        schema = _features_schema({})
        return self.async_show_form(step_id="features", data_schema=schema)

    # ---- 3. HAUPTMENÜ (CRUD) ----------------------------------------------------
    async def async_step_menu(self, user_input=None):
        """Hauptmenü, in dem man Perioden hinzufügen, bearbeiten oder das Setup abschließen kann."""
        if user_input is not None:
            action = user_input["action"]
            if action == "save":
                return self.async_create_entry(title=self._data["name"], data=self._data)
            elif action == "add_period":
                self._edit_index = None
                return await self.async_step_edit_period()
            elif action.startswith("edit_period_"):
                self._edit_index = int(action.replace("edit_period_", ""))
                return await self.async_step_edit_period()

        # Optionen fürs Menü aufbauen
        options = [
            selector.SelectOptionDict(value="add_period", label="➕ Neue Tarifperiode anlegen"),
        ]
        
        periods = self._data.get("periods", [])
        periods_sorted = sorted(periods, key=lambda p: dt_util.parse_date(p["start_date"]))
        self._data["periods"] = periods_sorted

        for idx, p in enumerate(periods_sorted):
            label = f"✏️ Ab {p['start_date']} ({p['day_price']} €)"
            options.append(selector.SelectOptionDict(value=f"edit_period_{idx}", label=label))
            
        options.append(selector.SelectOptionDict(value="save", label="💾 Speichern & Beenden"))

        schema = vol.Schema({
            vol.Required("action", default="add_period" if not periods else "save"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options, mode="dropdown")
            )
        })
        return self.async_show_form(step_id="menu", data_schema=schema)

    # ---- 4. PERIODE BEARBEITEN / ANLEGEN -----------------------------------------
    async def async_step_edit_period(self, user_input=None):
        """Erstellen oder Bearbeiten einer spezifischen Tarifperiode."""
        errors = {}
        if user_input is not None:
            # Löschen gewünscht?
            if user_input.get("delete_period"):
                if self._edit_index is not None:
                    self._data["periods"].pop(self._edit_index)
                return await self.async_step_menu()

            # Datumsprüfung
            start_date = user_input["start_date"]
            if not dt_util.parse_date(start_date):
                errors["start_date"] = "invalid_date"
            else:
                period_data = {
                    "start_date": start_date,
                    "day_price": user_input["day_price"],
                    "night_price": user_input.get("night_price", user_input["day_price"]),
                    "base_price": user_input.get("base_price", 0.0),
                    "advance_payment": user_input.get("advance_payment", 0.0),
                    "night_start": user_input.get("night_start", "22:00:00"),
                    "night_end": user_input.get("night_end", "06:00:00"),
                }
                if self._edit_index is not None:
                    self._data["periods"][self._edit_index] = period_data
                else:
                    self._data["periods"].append(period_data)

                return await self.async_step_menu()

        # Defaults laden, falls wir bearbeiten
        p_def = {}
        if self._edit_index is not None and self._edit_index < len(self._data["periods"]):
            p_def = self._data["periods"][self._edit_index]

        schema_dict = {
            vol.Required("start_date", default=p_def.get("start_date", dt_util.now().strftime("%Y-%m-%d"))): selector.DateSelector(),
            vol.Required("day_price", default=p_def.get("day_price", 0.30)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0.0, max=10.0, step=0.001, mode="box")
            ),
            vol.Optional("night_price", default=p_def.get("night_price", p_def.get("day_price", 0.30))): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0.0, max=10.0, step=0.001, mode="box")
            ),
            vol.Optional("base_price", default=p_def.get("base_price", 0.0)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0.0, max=5000.0, step=0.01, mode="box")
            ),
            vol.Optional("advance_payment", default=p_def.get("advance_payment", 0.0)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0.0, max=5000.0, step=0.01, mode="box")
            ),
            vol.Optional("night_start", default=p_def.get("night_start", "22:00:00")): selector.TimeSelector(),
            vol.Optional("night_end", default=p_def.get("night_end", "06:00:00")): selector.TimeSelector(),
        }
        
        # Löschen-Checkbox nur beim Bearbeiten anzeigen
        if self._edit_index is not None:
            schema_dict[vol.Optional("delete_period", default=False)] = selector.BooleanSelector()

        return self.async_show_form(
            step_id="edit_period", 
            data_schema=vol.Schema(schema_dict), 
            errors=errors
        )


    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EnergierechnerOptionsFlow(config_entry)


# ---------------------------------------------------------------------------
# Options Flow
# ---------------------------------------------------------------------------
class EnergierechnerOptionsFlow(config_entries.OptionsFlow):
    """Options Flow zum nachträglichen Bearbeiten der Konfiguration (UI Menü)."""

    def __init__(self, config_entry):
        self._entry = config_entry
        self._data: dict = dict(config_entry.data)
        if "periods" not in self._data:
            self._data["periods"] = []
        self._edit_index: int | None = None

    async def async_step_init(self, user_input=None):
        """Einstieg in die Optionen -> Hauptmenü."""
        return await self.async_step_menu()

    async def async_step_menu(self, user_input=None):
        if user_input is not None:
            action = user_input["action"]
            if action == "save":
                return self.async_create_entry(title="", data=self._data)
            elif action == "edit_features":
                return await self.async_step_features()
            elif action == "add_period":
                self._edit_index = None
                return await self.async_step_edit_period()
            elif action.startswith("edit_period_"):
                self._edit_index = int(action.replace("edit_period_", ""))
                return await self.async_step_edit_period()

        options = [
            selector.SelectOptionDict(value="edit_features", label="🛠️ Funktionen & Zeiträume anpassen"),
            selector.SelectOptionDict(value="add_period", label="➕ Neue Tarifperiode anlegen"),
        ]
        
        periods = self._data.get("periods", [])
        periods_sorted = sorted(periods, key=lambda p: dt_util.parse_date(p["start_date"]))
        self._data["periods"] = periods_sorted

        for idx, p in enumerate(periods_sorted):
            label = f"✏️ Ab {p['start_date']} ({p['day_price']} €)"
            options.append(selector.SelectOptionDict(value=f"edit_period_{idx}", label=label))
            
        options.append(selector.SelectOptionDict(value="save", label="💾 Speichern & Schließen"))

        schema = vol.Schema({
            vol.Required("action", default="edit_features"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options, mode="dropdown")
            )
        })
        return self.async_show_form(step_id="menu", data_schema=schema)

    async def async_step_features(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_menu()

        schema = _features_schema(self._data)
        return self.async_show_form(step_id="features", data_schema=schema)

    async def async_step_edit_period(self, user_input=None):
        errors = {}
        if user_input is not None:
            if user_input.get("delete_period"):
                if self._edit_index is not None:
                    self._data["periods"].pop(self._edit_index)
                return await self.async_step_menu()

            start_date = user_input["start_date"]
            if not dt_util.parse_date(start_date):
                errors["start_date"] = "invalid_date"
            else:
                period_data = {
                    "start_date": start_date,
                    "day_price": user_input["day_price"],
                    "night_price": user_input.get("night_price", user_input["day_price"]),
                    "base_price": user_input.get("base_price", 0.0),
                    "advance_payment": user_input.get("advance_payment", 0.0),
                    "night_start": user_input.get("night_start", "22:00:00"),
                    "night_end": user_input.get("night_end", "06:00:00"),
                }
                if self._edit_index is not None:
                    self._data["periods"][self._edit_index] = period_data
                else:
                    self._data["periods"].append(period_data)

                return await self.async_step_menu()

        p_def = {}
        if self._edit_index is not None and self._edit_index < len(self._data["periods"]):
            p_def = self._data["periods"][self._edit_index]

        schema_dict = {
            vol.Required("start_date", default=p_def.get("start_date", dt_util.now().strftime("%Y-%m-%d"))): selector.DateSelector(),
            vol.Required("day_price", default=p_def.get("day_price", 0.30)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0.0, max=10.0, step=0.001, mode="box")
            ),
            vol.Optional("night_price", default=p_def.get("night_price", p_def.get("day_price", 0.30))): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0.0, max=10.0, step=0.001, mode="box")
            ),
            vol.Optional("base_price", default=p_def.get("base_price", 0.0)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0.0, max=5000.0, step=0.01, mode="box")
            ),
            vol.Optional("advance_payment", default=p_def.get("advance_payment", 0.0)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0.0, max=5000.0, step=0.01, mode="box")
            ),
            vol.Optional("night_start", default=p_def.get("night_start", "22:00:00")): selector.TimeSelector(),
            vol.Optional("night_end", default=p_def.get("night_end", "06:00:00")): selector.TimeSelector(),
        }
        
        if self._edit_index is not None:
            schema_dict[vol.Optional("delete_period", default=False)] = selector.BooleanSelector()

        return self.async_show_form(
            step_id="edit_period", 
            data_schema=vol.Schema(schema_dict), 
            errors=errors
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
