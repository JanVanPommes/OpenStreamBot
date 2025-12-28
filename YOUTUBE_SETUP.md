# YouTube API Setup Guide

## 🎯 Warum eigenes API-Projekt?

Die **YouTube Data API v3** hat ein tägliches Quota-Limit von **10.000 Einheiten** pro Projekt. Für einen Bot, der im Chat interagiert, reicht das **nicht** aus, wenn jeder User dasselbe Projekt nutzt.

### Quota-Kosten (Beispiel):
- **Stream-Suche** (`liveBroadcasts.list`): **1 Unit**
- **Chat abrufen** (`liveChatMessages.list`): **5 Units** pro Poll
- **Chat senden** (`liveChatMessages.insert`): **50 Units**

**Problem**: Ein 8-Stunden-Stream mit 5s Polling verbraucht ~**29.000 Units** 💀

**Lösung**: Jeder Nutzer erstellt sein eigenes Google Cloud Project und hat damit sein eigenes 10k-Limit.

---

## 📋 Schritt-für-Schritt-Anleitung

### 1. Google Cloud Console öffnen
- Gehe zu: [https://console.cloud.google.com/](https://console.cloud.google.com/)
- Melde dich mit deinem Google-Account an (am besten der, mit dem du streamst)

### 2. Neues Projekt erstellen
1. Klicke oben auf **"Projekt erstellen"** (oder über das Dropdown-Menü)
2. **Projektname**: z.B. `OpenStreamBot` (frei wählbar)
3. **Organisation**: Leer lassen (oder dein Konto wählen)
4. Klicke **"Erstellen"**

### 3. YouTube Data API v3 aktivieren
1. Im linken Menü: **"APIs & Dienste" → "Bibliothek"**
2. Suche nach: **"YouTube Data API v3"**
3. Klicke auf das Ergebnis → **"Aktivieren"**

### 4. OAuth-Anmeldedaten erstellen
1. Im linken Menü: **"APIs & Dienste" → "Anmeldedaten"**
2. Klicke **"+ Anmeldedaten erstellen" → "OAuth-Client-ID"**
3. **Falls OAuth-Zustimmungsbildschirm noch nicht konfiguriert**:
   - Klicke **"Zustimmungsbildschirm konfigurieren"**
   - Wähle **"Extern"** (oder "Intern" falls du G Suite nutzt)
   - **App-Name**: `OpenStreamBot` (frei wählbar)
   - **Nutzer-Support-E-Mail**: Deine E-Mail
   - **Developer-Kontakt**: Deine E-Mail
   - **Scopes**: Nichts hinzufügen (überspringen)
   - **Testnutzer**: Deine E-Mail hinzufügen (wichtig!)
   - **Speichern**
   
4. Zurück zu **"Anmeldedaten"**:
   - **Anwendungstyp**: **"Desktop-App"**
   - **Name**: `OpenStreamBot Desktop` (frei wählbar)
   - Klicke **"Erstellen"**

5. **Download der Datei**:
   - Im Popup auf **"JSON herunterladen"** klicken
   - Datei wird als `client_secret_XXXXXX.json` heruntergeladen

### 5. Datei im Bot hinterlegen
1. **Umbenennen**: Die heruntergeladene Datei in **`client_secret.json`** umbenennen
2. **Verschieben**: In den **Hauptordner** von OpenStreamBot (dort wo `main.py` liegt)

### 6. Config anpassen (optional)
Öffne `config.yaml` und stelle sicher, dass YouTube aktiviert ist:

```yaml
youtube:
  enabled: true
  client_secret_file: client_secret.json
  token_file: token_youtube.json
```

### 7. Bot starten und einloggen
1. **Launcher starten**: `python launcher.py`
2. **Accounts-Tab** öffnen
3. **"Login with Google"** klicken
4. Browser öffnet sich → **Mit deinem Google-Account anmelden**
5. **Wichtig**: "Diese App wurde nicht von Google verifiziert" wird erscheinen:
   - Klicke auf **"Erweitert"**
   - Dann auf **"Zu [App-Name] (unsicher) wechseln"**
   - Das ist normal, weil es dein eigenes Projekt ist!
6. **Berechtigungen erteilen**
7. Fertig! Token wird als `token_youtube.json` gespeichert

---

## 🔧 Quota optimieren

### Best Practices:
1. **Manuelles Verbinden**: Nutze den **"Connect YouTube Stream"** Button im Dashboard nur wenn du streamst
2. **Nicht 24/7 laufen lassen**: YouTube-Bot pausiert automatisch nach 1h bei Quota-Fehlern
3. **Polling-Intervall**: Der Bot nutzt das von YouTube empfohlene Intervall (meist 5-10s)

### Quota-Übersicht prüfen:
1. [Google Cloud Console](https://console.cloud.google.com/) → Dein Projekt
2. **"APIs & Dienste" → "Dashboard"**
3. Klicke auf **"YouTube Data API v3"**
4. Tab **"Kontingente"** → Zeigt tägliche Nutzung

---

## ❓ Häufige Probleme

### "Quota Exceeded" Fehler
- **Ursache**: Tageslimit von 10.000 Units überschritten
- **Lösung**: 
  - Warte bis Mitternacht (Pacific Time, ca. 9:00 Uhr MEZ)
  - Oder: Aktiviere YouTube nur bei Bedarf (Button im Dashboard)
  - Langfristig: Quota-Erhöhung bei Google beantragen (selten nötig)

### "Access blocked: This app's request is invalid"
- **Ursache**: Redirect-URI falsch konfiguriert
- **Lösung**: Der Bot nutzt `localhost` automatisch, daher sollte das nicht passieren. Falls doch:
  - Cloud Console → Anmeldedaten → OAuth-Client bearbeiten
  - **Autorisierte Weiterleitungs-URIs** hinzufügen: `http://localhost:8080/`

### "The OAuth Client ID has been deleted"
- **Ursache**: Client wurde gelöscht, Token ist ungültig
- **Lösung**: 
  - Lösche `token_youtube.json`
  - Erstelle neue OAuth-Anmeldedaten (siehe Schritt 4)
  - Erneut einloggen

---

## 🚀 Quota erhöhen (Optional, für Heavy Users)

Falls du regelmäßig über 10k Units/Tag kommst:
1. [Quota-Erhöhung beantragen](https://support.google.com/youtube/contact/yt_api_form)
2. Begründung angeben (z.B. "Open Source Stream Bot für persönlichen Kanal")
3. Normalerweise wird auf **1.000.000 Units/Tag** erhöht
4. Bearbeitungszeit: 1-2 Wochen

---

## 📊 Kosten?

**Kompletter kostenlos** für normale Nutzung! 🎉

Google stellt die YouTube API kostenlos bereit. Nur wenn du **extrem hohe** Quotas brauchst (> 1 Mio./Tag), könnte Google dich bitten, auf ein kostenpflichtiges Kontingent umzusteigen (sehr selten).

---

## 🛡️ Sicherheit

- **`client_secret.json`**: Nicht öffentlich teilen! Diese Datei identifiziert deine App
- **`token_youtube.json`**: **Niemals** teilen oder committen! Enthält Zugriff auf deinen YouTube-Account
- Füge beide Dateien zu `.gitignore` hinzu (schon standardmäßig im Projekt)

---

Bei Fragen oder Problemen: [GitHub Issues](https://github.com/JanVanPommes/OpenStreamBot/issues) öffnen!
