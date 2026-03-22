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
- ✅ **Neu:** PV-Einspeisung / Ertragstracking: Wähle im Setup zwischen Strombezug (Kosten/Verbrauch) und PV-Einspeisung (Vergütung/Ertrag).
- ✅ Jede Kennzahl (Kosten, Verbrauch, Bilanz) wird als **eigene physische Sensor-Entität** erstellt (optimal für Dashboards).
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
3. **Setup-Menü (Tarifperioden)** – Hier fügst du über den Button **"+ Neue Tarifperiode anlegen"** bequem über ein Formular (Datum, Preise, Zeiten) deine Tarife hinzu. Danach auf "Speichern & Beenden" klicken.

*(Einstellungen können nachträglich jederzeit über **Konfigurieren** im selben Menü angepasst, bearbeitet oder gelöscht werden.)*

## Sensor-Entitäten & Dashboard

Die Integration erzeugt für jeden aktivierten Zeitraum separate Sensoren für **Kosten (€)** und **Verbrauch (kWh)** unterhalb eines gemeinsamen Gerätes.

*(Beispiel: Wenn der Name in der UI "Strom" lautet, heißen die Entitäten `sensor.strom_heute_kosten` und `sensor.strom_heute_verbrauch`).*

### Beispiel-Karten fürs Dashboard (Grid / Übersicht)

Hier sind zwei vorgefertigte YAML-Codes für eine schöne, getrennte Übersicht im HA-Dashboard (ersetze ggf. `energierechner` durch deinen gewählten Sensornamen). Die aktuelle Periode und die Vorperiode stehen hierbei für den direkten Vergleich (Heute vs Gestern) sofort lesbar nebeneinander.

**Kachel 1: Übersicht Verbrauch**
```yaml
type: vertical-stack
cards:
  - type: entity
    entity: sensor.energierechner_gesamtverbrauch
    name: Gesamtverbrauch
    icon: mdi:lightning-bolt
  - type: grid
    columns: 2
    square: false
    cards:
      - type: entity
        entity: sensor.energierechner_heute_verbrauch
        name: Verbrauch Heute
      - type: entity
        entity: sensor.energierechner_gestern_verbrauch
        name: Verbrauch Gestern
      - type: entity
        entity: sensor.energierechner_aktuelle_woche_verbrauch
        name: Verbrauch Diese Woche
      - type: entity
        entity: sensor.energierechner_vorherige_woche_verbrauch
        name: Verbrauch Letzte Woche
      - type: entity
        entity: sensor.energierechner_aktueller_monat_verbrauch
        name: Verbrauch Dieser Monat
      - type: entity
        entity: sensor.energierechner_letzter_monat_verbrauch
        name: Verbrauch Letzter Monat
  # Natives Balkendiagramm (Verlauf der letzten 7 Tage)
  - type: statistics-graph
    title: Verbrauch (Letzte 7 Tage)
    chart_type: bar
    period: day
    days_to_show: 7
    stat_types:
      - change
    entities:
      - sensor.energierechner_gesamtverbrauch
```

**Kachel 2: Übersicht Kosten**
```yaml
type: vertical-stack
cards:
  - type: entity
    entity: sensor.energierechner_gesamtkosten
    name: Gesamtkosten
    icon: mdi:currency-eur
  - type: grid
    columns: 2
    square: false
    cards:
      - type: entity
        entity: sensor.energierechner_heute_kosten
        name: Kosten Heute
      - type: entity
        entity: sensor.energierechner_gestern_kosten
        name: Kosten Gestern
      - type: entity
        entity: sensor.energierechner_aktuelle_woche_kosten
        name: Kosten Diese Woche
      - type: entity
        entity: sensor.energierechner_vorherige_woche_kosten
        name: Kosten Letzte Woche
      - type: entity
        entity: sensor.energierechner_aktueller_monat_kosten
        name: Kosten Dieser Monat
      - type: entity
        entity: sensor.energierechner_letzter_monat_kosten
        name: Kosten Letzter Monat
```

### Statischer Balken-Vergleich der Vorperiode (via ApexCharts)

Da die alte `custom:bar-card` nicht mehr gepflegt wird, eignet sich auch hierfür die `custom:apexcharts-card` hervorragend. 
Wenn du keine Zeitachse mit einem Verlaufskurven-Diagramm haben möchtest, sondern stattdessen einfach **zwei simple Säulenbalken** zum sofortigen Vergleich nebeneinander stehen haben willst (z.B. ein Balken für Heute, ein Balken für Gestern), kannst du die Darstellung über einen einfachen JavaScript-Zweizeiler erzwingen, sodass die Karte exakt nur einen dicken Balken pro Entität generiert und nichts abschneidet.

Hier ist ein komplettes YAML-Setup als Dashboard-Zwei-Spalten-Grid (Links: **Verbrauch**, Rechts: **Kosten**):

```yaml
type: grid
columns: 1
cards:
  - type: custom:apexcharts-card
    header:
      show: true
      title: Tagesvergleich (Verbrauch)
      show_states: true
      colorize_states: true
    graph_span: 2h
    span:
      offset: '+1h'
    update_interval: 5m
    apex_config:
      chart: { parentHeightOffset: 0 }
      plotOptions: { bar: { columnWidth: '60%' } }
      xaxis: { labels: { show: false }, tooltip: { enabled: false }, axisTicks: { show: false }, axisBorder: { show: false } }
      tooltip: { x: { show: false } }
    series:
      - entity: sensor.energierechner_heute_verbrauch
        name: Heute
        type: column
        color: '#3498db'
        data_generator: |
          return [[new Date().getTime(), entity.state]];
      - entity: sensor.energierechner_gestern_verbrauch
        name: Gestern
        type: column
        color: '#95a5a6'
        data_generator: |
          return [[new Date().getTime(), entity.state]];

  - type: custom:apexcharts-card
    header:
      show: true
      title: Tagesvergleich (Kosten)
      show_states: true
      colorize_states: true
    graph_span: 2h
    span:
      offset: '+1h'
    update_interval: 5m
    apex_config:
      chart: { parentHeightOffset: 0 }
      plotOptions: { bar: { columnWidth: '60%' } }
      xaxis: { labels: { show: false }, tooltip: { enabled: false }, axisTicks: { show: false }, axisBorder: { show: false } }
      tooltip: { x: { show: false } }
    series:
      - entity: sensor.energierechner_heute_kosten
        name: Heute
        type: column
        color: '#f1c40f'
        data_generator: |
          return [[new Date().getTime(), entity.state]];
      - entity: sensor.energierechner_gestern_kosten
        name: Gestern
        type: column
        color: '#95a5a6'
        data_generator: |
          return [[new Date().getTime(), entity.state]];
```

### Wochenvergleich (Verbrauch & Kosten getrennt)
Für den perfekten **Wochenvergleich** (Aktuelle Woche vs. Vorherige Woche):

```yaml
type: grid
columns: 1
cards:
  - type: custom:apexcharts-card
    header:
      show: true
      title: Wochenvergleich (Verbrauch)
      show_states: true
      colorize_states: true
    graph_span: 2h
    span:
      offset: '+1h'
    update_interval: 5m
    apex_config:
      chart: { parentHeightOffset: 0 }
      plotOptions: { bar: { columnWidth: '60%' } }
      xaxis: { labels: { show: false }, tooltip: { enabled: false }, axisTicks: { show: false }, axisBorder: { show: false } }
      tooltip: { x: { show: false } }
    series:
      - entity: sensor.energierechner_aktuelle_woche_verbrauch
        name: Diese Woche
        type: column
        color: '#3498db'
        data_generator: |
          return [[new Date().getTime(), entity.state]];
      - entity: sensor.energierechner_vorherige_woche_verbrauch
        name: Letzte Woche
        type: column
        color: '#95a5a6'
        data_generator: |
          return [[new Date().getTime(), entity.state]];

  - type: custom:apexcharts-card
    header:
      show: true
      title: Wochenvergleich (Kosten)
      show_states: true
      colorize_states: true
    graph_span: 2h
    span:
      offset: '+1h'
    update_interval: 5m
    apex_config:
      chart: { parentHeightOffset: 0 }
      plotOptions: { bar: { columnWidth: '60%' } }
      xaxis: { labels: { show: false }, tooltip: { enabled: false }, axisTicks: { show: false }, axisBorder: { show: false } }
      tooltip: { x: { show: false } }
    series:
      - entity: sensor.energierechner_aktuelle_woche_kosten
        name: Diese Woche
        type: column
        color: '#f1c40f'
        data_generator: |
          return [[new Date().getTime(), entity.state]];
      - entity: sensor.energierechner_vorherige_woche_kosten
        name: Letzte Woche
        type: column
        color: '#95a5a6'
        data_generator: |
          return [[new Date().getTime(), entity.state]];
```

### Jahresvergleich (Verbrauch & Kosten getrennt)
Und hier der Code für den **Jahresvergleich** (Aktuelles Jahr vs. Letztes Jahr):

```yaml
type: grid
columns: 1
cards:
  - type: custom:apexcharts-card
    header:
      show: true
      title: Jahresvergleich (Verbrauch)
      show_states: true
      colorize_states: true
    graph_span: 2h
    span:
      offset: '+1h'
    update_interval: 5m
    apex_config:
      chart: { parentHeightOffset: 0 }
      plotOptions: { bar: { columnWidth: '60%' } }
      xaxis: { labels: { show: false }, tooltip: { enabled: false }, axisTicks: { show: false }, axisBorder: { show: false } }
      tooltip: { x: { show: false } }
    series:
      - entity: sensor.energierechner_aktuelles_jahr_verbrauch
        name: Dieses Jahr
        type: column
        color: '#e74c3c'
        data_generator: |
          return [[new Date().getTime(), entity.state]];
      - entity: sensor.energierechner_letztes_jahr_verbrauch
        name: Letztes Jahr
        type: column
        color: '#95a5a6'
        data_generator: |
          return [[new Date().getTime(), entity.state]];

  - type: custom:apexcharts-card
    header:
      show: true
      title: Jahresvergleich (Kosten)
      show_states: true
      colorize_states: true
    graph_span: 2h
    span:
      offset: '+1h'
    update_interval: 5m
    apex_config:
      chart: { parentHeightOffset: 0 }
      plotOptions: { bar: { columnWidth: '60%' } }
      xaxis: { labels: { show: false }, tooltip: { enabled: false }, axisTicks: { show: false }, axisBorder: { show: false } }
      tooltip: { x: { show: false } }
    series:
      - entity: sensor.energierechner_aktuelles_jahr_kosten
        name: Dieses Jahr
        type: column
        color: '#f1c40f'
        data_generator: |
          return [[new Date().getTime(), entity.state]];
      - entity: sensor.energierechner_letztes_jahr_kosten
        name: Letztes Jahr
        type: column
        color: '#95a5a6'
        data_generator: |
          return [[new Date().getTime(), entity.state]];
```

> **Tipp zum nativen Diagramm**: Die native `statistics-graph` Karte (ganz oben im ersten Beispiel) wertet automatisch die Langzeitstatistiken (`state_class: total`) des Gesamtverbrauchs aus. Du kannst dort `period` auch auf `month` stellen, um die fortlaufenden Monate dieses Jahres miteinander zu vergleichen!

> **Tipp für kompakte Layouts:** Wenn du die [multiple-entity-row](https://github.com/benct/lovelace-multiple-entity-row) HACS Frontend-Karte verwendest, lassen sich aktuelle Periode und Vorperiode sogar numerisch in *einer einzigen* Zeile kombinieren.

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
