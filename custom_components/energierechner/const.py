"""Constants for the Energierechner integration."""

DOMAIN = "energierechner"
CONF_SOURCE_ENTITY = "source_entity"
CONF_PERIODS = "periods"
CONF_INDIVIDUAL_PERIODS = "individual_periods"
CONF_NAME = "name"
CONF_NIGHT_RATE = "night_rate"
CONF_DAILY_CONSUMPTION = "daily_consumption"
CONF_NIGHTLY_CONSUMPTION = "nightly_consumption"
CONF_ACTIVE = "active"
CONF_ADD_BASE_PRICE = "add_base_price"
CONF_PERIODS_CALCULATION = "periods_calculation"
CONF_BALANCE = "balance"
CONF_DAILY = "daily"
CONF_PREVIOUS_DAY = "previous_day"
CONF_CURRENT_WEEK = "current_week"
CONF_PREVIOUS_WEEK = "previous_week"
CONF_CURRENT_MONTH = "current_month"
CONF_LAST_MONTH = "last_month"
CONF_CURRENT_YEAR = "current_year"
CONF_LAST_YEAR = "last_year"

DEFAULT_NAME = "Energierechner"
DEFAULT_SCAN_INTERVAL = 600
ENERGY_KWH = "kWh"

CONF_METER_TYPE = "meter_type"
METER_TYPE_CONSUMPTION = "consumption"  # Kosten/Verbrauch
METER_TYPE_FEED_IN = "feed_in"          # Ertrag/Einspeisung

CONF_SOURCE_UNIT = "source_unit"
SOURCE_UNIT_KWH = "kwh"  # Sensor liefert kWh (Standard)
SOURCE_UNIT_WH  = "wh"   # Sensor liefert Wh → wird durch 1000 geteilt
