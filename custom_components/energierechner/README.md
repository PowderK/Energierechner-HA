# Energierechner Home Assistant integration

Portierung des Symcon-Moduls aus dem Projekt.

## Installation

1. Kopiere den Ordner `custom_components/energierechner` in dein Home Assistant `config`-Verzeichnis.
2. Starte Home Assistant neu.

## Beispielkonfiguration (configuration.yaml)

```yaml
sensor:
  - platform: energierechner
    name: Energierechner Kosten
    source_entity: sensor.stromverbrauch_kwh
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

## Datenpunkte

Der Sensorwert (`state`) ist die aggregierte Gesamtkosten-Berechnung (in Euro).

`attributes` enthalten beispielsweise:

- `total_consumption`
- `total_costs`
- `today_consumption`, `today_costs`
- `current_month_consumption`, `current_month_costs`
- `period_<startdate>_consumption`, `period_<startdate>_costs`
- `period_<startdate>_balance` (wenn `balance` aktiviert)

## Limitierungen

- Die Berechnung basiert auf Recorder-Historie von `source_entity`.
- Für robuste High-Precision-Nacht/Tag-Trennung sollte eine geeignet dichte Messwerte-Historie vorhanden sein.
