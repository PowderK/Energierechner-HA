# GitHub Push Instructions

Das lokale Repository `Energierechner-HA` ist fertig. So pushst du es zu GitHub:

## 1. Neues Repository auf GitHub erstellen

1. Gehe zu https://github.com/new
2. Name: `Energierechner-HA`
3. Description: "Home Assistant integration for electricity cost calculation with dynamic tariff support"
4. Wähle **Public**
5. **Nicht** Initialize with README/LICENSE (bereits vorhanden!)
6. Klicke **Create repository**

## 2. Push vom lokalen Repo

```bash
cd /Users/benni/Energierechner-HA
git remote add origin https://github.com/Schnittcher/Energierechner-HA.git
git branch -M main
git push -u origin main
```

## 3. Verify

- Besuche https://github.com/Schnittcher/Energierechner-HA
- Prüfe: Dateien vorhanden? `.gitignore`, `README.md`, `LICENSE`, `custom_components/`, `blueprints/` ?

## Optional: Weitere GitHub-Settings

- Settings → About → Add topic: `home-assistant`, `energy`, `integration`
- Settings → Danger Zone → Make public (falls noch privat)

---

### Fertig! 🎉

Dein HA-Integration ist jetzt auf GitHub ohne das Symcon-Modul.
