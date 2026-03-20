# Energierechner Home Assistant Integration

A Home Assistant port of the [Energierechner Symcon module](https://github.com/Schnittcher/Energierechner) for electricity cost calculation with dynamic tariff periods, day/night rates, and flexible aggregation.

## Features

- ✅ Multiple tariff periods with configurable prices
- ✅ Day/night rate separation (configurable times)
- ✅ Base price calculation
- ✅ Balance calculation (advance payment - actual costs)
- ✅ Time period aggregation:
  - Daily, previous day
  - Weekly (current/previous)
  - Monthly (current/last)
  - Yearly (current/last)
  - Custom periods
- ✅ Flexible consumption/cost tracking
- ✅ Recorder-based history evaluation

## Installation

### Manual Installation

1. Clone or download this repository
2. Copy `custom_components/energierechner/` to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant
4. Add configuration to `configuration.yaml` (see below)

### HACS Installation (if published)

```
HACS → Integrations → + Create Custom Repository
URL: https://github.com/Schnittcher/Energierechner-HA
Category: Integration
```

## Configuration

Add to your `configuration.yaml`:

```yaml
sensor:
  - platform: energierechner
    name: Electricity Costs
    source_entity: sensor.energy_consumption_kwh
    active: true
    night_rate: true
    daily_consumption: true
    nightly_consumption: true
    periods_calculation: true
    balance: true
    daily: true
    previous_day: true
    current_week: true
    previous_week: true
    current_month: true
    last_month: true
    current_year: true
    last_year: true
    add_base_price: true
    scan_interval: 600
    periods:
      - start_date: "2024-01-01"
        day_price: 0.35
        night_price: 0.22
        base_price: 140.0
        advance_payment: 65.0
        deductions_per_year: 0.2
        night_start: "22:00"
        night_end: "06:00"
      - start_date: "2025-01-01"
        day_price: 0.38
        night_price: 0.23
        base_price: 155.0
        advance_payment: 70.0
        deductions_per_year: 0.2
```

## Configuration Parameters

### Main Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source_entity` | `entity_id` | **required** | Energy consumption sensor (kWh) |
| `name` | `string` | "Energierechner" | Friendly name |
| `active` | `boolean` | `true` | Enable/disable integration |
| `scan_interval` | `integer` | 600 | Update interval in seconds |

### Rate Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `night_rate` | `boolean` | `false` | Enable night/day rate splitting |
| `add_base_price` | `boolean` | `false` | Include base price in costs |
| `periods_calculation` | `boolean` | `false` | Calculate per-period aggregate |
| `balance` | `boolean` | `false` | Calculate balance per period |

### Consumption Tracking

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `daily_consumption` | `boolean` | `false` | Track daytime consumption |
| `nightly_consumption` | `boolean` | `false` | Track nighttime consumption |

### Time Periods (Enable as needed)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `daily` | `boolean` | `false` | Track today |
| `previous_day` | `boolean` | `false` | Track yesterday |
| `current_week` | `boolean` | `false` | Track current week |
| `previous_week` | `boolean` | `false` | Track previous week |
| `current_month` | `boolean` | `false` | Track current month |
| `last_month` | `boolean` | `false` | Track last month |
| `current_year` | `boolean` | `false` | Track current year |
| `last_year` | `boolean` | `false` | Track last year |

### Period Definition

Each period in the `periods` list:

```yaml
- start_date: "YYYY-MM-DD"          # Period start date (required)
  day_price: 0.35                   # Day rate in €/kWh (required)
  night_price: 0.22                 # Night rate in €/kWh (optional, defaults to day_price)
  base_price: 140.0                 # Annual base fee in € (optional, default: 0)
  advance_payment: 65.0             # Monthly advance payment in € (optional, default: 0)
  deductions_per_year: 0.2          # Deductions per year (optional, default: 0)
  night_start: "22:00"              # Night period start (HH:MM, optional, default: 22:00)
  night_end: "06:00"                # Night period end (HH:MM, optional, default: 06:00)
```

## Sensor Output

The integration creates a sensor entity with:

- **State**: Aggregated total costs (€)
- **Attributes**:
  - `total_consumption`: Total consumption (kWh)
  - `total_costs`: Total costs (€)
  - `today_consumption`, `today_costs`
  - `previous_day_consumption`, `previous_day_costs`
  - `current_week_consumption`, `current_week_costs`
  - Similar for all configured time periods...
  - `period_<YYYY-MM-DD>_consumption`
  - `period_<YYYY-MM-DD>_costs`
  - `period_<YYYY-MM-DD>_balance` (if balance enabled)

## Blueprint

A blueprint is included for generating YAML configuration via the Home Assistant UI. See `blueprints/automation/energierechner_config.yaml`.

To use:
1. Settings → Automations & Scenes → Blueprints
2. Import the blueprint file
3. Create automation with your parameters
4. Copy generated YAML configuration

## Debugging

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.energierechner: debug
```

View logs in: Settings → System → Logs

## Requirements

- Home Assistant 2023.1 or newer
- Recorder integration enabled (default)
- Energy consumption sensor providing kWh values

## License

See LICENSE file

## Credits

Original Symcon module by [Schnittcher](https://github.com/Schnittcher)

## Support

For issues or feature requests, please open an issue in the GitHub repository.
