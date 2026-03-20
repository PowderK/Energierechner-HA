# Energierechner Home Assistant Integration

Ein Home Assistant Port des [Energierechner Symcon Moduls](https://github.com/Schnittcher/Energierechner) zur Berechnung von Stromkosten mit dynamischen Tarifperioden, Tag-/Nachttarifen und flexibler Aggregation.

## Funktionen

- ✅ Mehrere Tarifperioden mit konfigurierbaren Preisen
- ✅ Tag-/Nachttarif-Trennung (konfigurierbare Zeiten)
- ✅ Grundpreisberechnung
- ✅ Bilanzberechnung (monatlicher Abschlag – tatsächliche Kosten)
- ✅ Zeitraum-Aggregation:
  - Täglich, Vortag
  - Wöchentlich (aktuell/vorherig)
  - Monatlich (aktuell/letzter)
  - Jährlich (aktuell/letztes)
  - Periodenweise (je Tarif)
- ✅ Flexibles Verbrauchs-/Kosten-Tracking (Tag/Nacht getrennt)
- ✅ Recorder-basierte Verlaufsauswertung
- ✅ Einrichtung über die **Home Assistant UI** (kein YAML nötig)

## Installation

### HACS (empfohlen)

1. HACS → Integrationen → ⋮ → **Benutzerdefinierte Repositories**
2. URL: `https://github.com/PowderK/Energierechner-HA` · Kategorie: **Integration**
3. „Energierechner" suchen und installieren
4. Home Assistant neu starten

### Manuelle Installation

1. Dieses Repository klonen
2. `custom_components/energierechner/` in das HA-Verzeichnis `config/custom_components/` kopieren
3. Home Assistant neu starten

## Einrichtung

Nach dem Neustart:

**Einstellungen → Integrationen → + Hinzufügen → „Energierechner"**

Der dreistufige Assistent führt durch:
1. **Grundkonfiguration** – Sensorname, kWh-Quelle, Aktualisierungsintervall
2. **Funktionen** – Aktivierung von Tag-/Nachttarif, Zeiträumen (heute, Woche, Monat…), Bilanz
3. **Tarifperioden** – YAML-Liste der Tarifabschnitte (Preis, Grundgebühr, Abschlag)

Einstellungen können nachträglich über **Konfigurieren** geändert werden.

## Tarifperioden (YAML-Format)

```yaml
- start_date: "2024-01-01"
  day_price: 0.35           # Tagpreis €/kWh
  night_price: 0.22         # Nachtpreis €/kWh (optional, Standard = day_price)
  base_price: 140.0         # Jährliche Grundgebühr in € (optional)
  advance_payment: 65.0     # Monatlicher Abschlag in € (für Bilanz)
  night_start: "22:00"      # Beginn der Nachtzeit (optional, Standard: 22:00)
  night_end: "06:00"        # Ende der Nachtzeit (optional, Standard: 06:00)
- start_date: "2025-01-01"
  day_price: 0.38
  night_price: 0.23
  base_price: 155.0
  advance_payment: 70.0
```

## Sensor-Attribute

Der Sensor liefert im Zustand die **aggregierten Gesamtkosten (€)** sowie folgende Attribute:

| Attribut | Beschreibung |
|----------|-------------|
| `total_consumption` | Gesamtverbrauch (kWh) |
| `total_costs` | Gesamtkosten (€) |
| `today_consumption` / `today_costs` | Heute |
| `previous_day_consumption` / `_costs` | Gestern |
| `current_week_*` / `current_month_*` / `current_year_*` | Zeiträume |
| `period_JJJJ-MM-TT_consumption` / `_costs` | Pro Tarifperiode |
| `period_JJJJ-MM-TT_balance` | Bilanz (nur wenn aktiviert) |

## Debugging

Debug-Logging in `configuration.yaml` aktivieren:

```yaml
logger:
  logs:
    custom_components.energierechner: debug
```

Logs ansehen: **Einstellungen → System → Protokolle**

## Voraussetzungen

- Home Assistant 2023.1 oder neuer
- Recorder-Integration aktiviert (Standard)
- Stromverbrauchs-Sensor mit kWh-Werten (z. B. von einem Energiezähler)

## Lizenz

Siehe [LICENSE](LICENSE)

## Danksagung

Originales Symcon-Modul von [Schnittcher](https://github.com/Schnittcher)

## Support

Bei Problemen oder Feature-Wünschen bitte ein [Issue](https://github.com/PowderK/Energierechner-HA/issues) erstellen.
