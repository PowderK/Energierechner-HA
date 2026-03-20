# Energierechner Home Assistant Integration

Ein Home Assistant Port des [Energierechner Symcon Moduls](https://github.com/Schnittcher/Energierechner) zur Berechnung von Stromkosten mit dynamischen Tarifperioden, Tag-/Nachttarifen und flexibler Aggregation.

## Funktionen

- ✅ Mehrere Tarifperioden mit konfigurierbaren Preisen
- ✅ Tag-/Nachttarif-Trennung (konfigurierbare Zeiten)
- ✅ Grundpreisberechnung
- ✅ Bilanzberechnung (Abschlag – tatsächliche Kosten)
- ✅ Zeitraum-Aggregation:
  - Täglich, Vortag
  - Wöchentlich (aktuell/vorherig)
  - Monatlich (aktuell/letzter)
  - Jährlich (aktuell/letztes)
  - Benutzerdefinierte Zeiträume
- ✅ Flexibles Verbrauchs-/Kostens-Tracking
- ✅ Recorder-basierte Verlaufsauswertung

## Installation

### Manuelle Installation

1. Dieses Repository klonen oder herunterladen
2. `custom_components/energierechner/` in das Home Assistant `config/custom_components/`-Verzeichnis kopieren
3. Home Assistant neu starten
4. Konfiguration in `configuration.yaml` hinzufügen (siehe unten)

### HACS-Installation (falls veröffentlicht)

```
HACS → Integrationen → + Benutzerdefiniertes Repository hinzufügen
URL: https://github.com/PowderK/Energierechner-HA
Kategorie: Integration
```

## Konfiguration

In `configuration.yaml` einfügen:

```yaml
sensor:
  - platform: energierechner
    name: Stromkosten
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

## Konfigurationsparameter

### Hauptparameter

| Parameter | Typ | Standard | Beschreibung |
|-----------|-----|----------|--------------|
| `source_entity` | `entity_id` | **Pflicht** | Stromverbrauchs-Sensor (kWh) |
| `name` | `string` | „Energierechner" | Anzeigename |
| `active` | `boolean` | `true` | Integration aktivieren/deaktivieren |
| `scan_interval` | `integer` | 600 | Aktualisierungsintervall in Sekunden |

### Tarifkonfiguration

| Parameter | Typ | Standard | Beschreibung |
|-----------|-----|----------|--------------|
| `night_rate` | `boolean` | `false` | Nacht-/Tagtarif-Trennung aktivieren |
| `add_base_price` | `boolean` | `false` | Grundpreis in die Kosten einrechnen |
| `periods_calculation` | `boolean` | `false` | Periodenweise Aggregation berechnen |
| `balance` | `boolean` | `false` | Bilanz pro Periode berechnen |

### Verbrauchstracking

| Parameter | Typ | Standard | Beschreibung |
|-----------|-----|----------|--------------|
| `daily_consumption` | `boolean` | `false` | Tagesverbrauch tracken |
| `nightly_consumption` | `boolean` | `false` | Nachtverbrauch tracken |

### Zeiträume (bei Bedarf aktivieren)

| Parameter | Typ | Standard | Beschreibung |
|-----------|-----|----------|--------------|
| `daily` | `boolean` | `false` | Heutigen Tag tracken |
| `previous_day` | `boolean` | `false` | Gestern tracken |
| `current_week` | `boolean` | `false` | Aktuelle Woche tracken |
| `previous_week` | `boolean` | `false` | Vorherige Woche tracken |
| `current_month` | `boolean` | `false` | Aktuellen Monat tracken |
| `last_month` | `boolean` | `false` | Letzten Monat tracken |
| `current_year` | `boolean` | `false` | Aktuelles Jahr tracken |
| `last_year` | `boolean` | `false` | Letztes Jahr tracken |

### Periodendefinition

Jede Periode in der `periods`-Liste:

```yaml
- start_date: "JJJJ-MM-TT"          # Startdatum der Periode (Pflicht)
  day_price: 0.35                    # Tagpreis in €/kWh (Pflicht)
  night_price: 0.22                  # Nachtpreis in €/kWh (optional, Standard: day_price)
  base_price: 140.0                  # Jährlicher Grundpreis in € (optional, Standard: 0)
  advance_payment: 65.0              # Monatlicher Abschlag in € (optional, Standard: 0)
  deductions_per_year: 0.2           # Abzüge pro Jahr (optional, Standard: 0)
  night_start: "22:00"               # Beginn der Nachtzeit (HH:MM, optional, Standard: 22:00)
  night_end: "06:00"                 # Ende der Nachtzeit (HH:MM, optional, Standard: 06:00)
```

## Sensor-Ausgabe

Die Integration erstellt eine Sensor-Entität mit:

- **Zustand**: Aggregierte Gesamtkosten (€)
- **Attribute**:
  - `total_consumption`: Gesamtverbrauch (kWh)
  - `total_costs`: Gesamtkosten (€)
  - `today_consumption`, `today_costs`
  - `previous_day_consumption`, `previous_day_costs`
  - `current_week_consumption`, `current_week_costs`
  - Analog für alle konfigurierten Zeiträume…
  - `period_<JJJJ-MM-TT>_consumption`
  - `period_<JJJJ-MM-TT>_costs`
  - `period_<JJJJ-MM-TT>_balance` (wenn Bilanz aktiviert)

## Blueprint

Ein Blueprint ist enthalten, um die YAML-Konfiguration über die Home Assistant UI zu generieren. Siehe `blueprints/automation/energierechner_config.yaml`.

Verwendung:
1. Einstellungen → Automatisierungen & Szenen → Blueprints
2. Blueprint-Datei importieren
3. Automatisierung mit eigenen Parametern erstellen
4. Generierten YAML-Code kopieren

## Debugging

Debug-Logging in `configuration.yaml` aktivieren:

```yaml
logger:
  logs:
    custom_components.energierechner: debug
```

Logs ansehen unter: Einstellungen → System → Protokolle

## Voraussetzungen

- Home Assistant 2023.1 oder neuer
- Recorder-Integration aktiviert (Standard)
- Stromverbrauchs-Sensor mit kWh-Werten

## Lizenz

Siehe LICENSE-Datei

## Danksagung

Originales Symcon-Modul von [Schnittcher](https://github.com/Schnittcher)

## Support

Bei Problemen oder Feature-Wünschen bitte ein Issue im GitHub-Repository eröffnen.
