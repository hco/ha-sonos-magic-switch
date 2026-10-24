# CLAUDE.md

## Offene Punkte

- **Validate-Workflow ist pausiert** (seit 2026-10-24, `gh workflow disable validate.yml`).
  hassfest scheiterte nur an `categories` im Manifest, weil
  `ghcr.io/home-assistant/hassfest:latest` noch auf HA 2026.10 stand; die
  Unterstützung kommt mit HA 2026.11.0b0 (geplant 2026-10-28). Eine Cloud-Routine
  schaltet den Workflow am 2026-10-29 wieder ein und meldet das Ergebnis per Mail
  (https://claude.ai/code/routines/trig_01Bn5oNAfFB56ePerLiLcZJZ). Sonst von Hand:
  `gh workflow enable validate.yml && gh workflow run validate.yml`. Ist hassfest
  dann grün, diesen Punkt entfernen.
- **Auf HA 2026.11 anheben:** `homeassistant` und
  `pytest-homeassistant-custom-component` in `requirements.txt` gemeinsam von Hand
  anheben (Dependabot ignoriert beide). Dann einen Test ergänzen, dass der Switch
  beim Ändern seiner entity_id erhalten bleibt; `async_entity_id_changed` ruft HA
  erst ab 2026.11 auf.

## Ideen

Mögliche Erweiterungen, die meisten davon pro Switch konfigurierbar über einen
Options-Flow:

- **Keiner Gruppe mit TV-Ton beitreten:** Spielt die größte Gruppe den Fernsehton
  einer Soundbar (`source` ist `TV` oder `Line-in`), statt ihr beizutreten lieber
  allein starten.
- **Ersatz-Favorit:** Bei leerer Queue tut `media_play` nichts. Dann stattdessen
  einen eingestellten Sonos-Favoriten oder eine Playlist starten.
- **Lautstärke beim Beitreten:** Pro Raum eine Lautstärke, die beim Einschalten
  gesetzt wird.
- **Regel für die Gruppenwahl:** Neben der größten Gruppe auch die zuletzt
  gestartete oder eine bevorzugte Gruppe.
- **Diagnose-Download** (`diagnostics.py`): Gruppen- und Wiedergabezustände der
  Sonos-Player und die Zuordnung der Switches herunterladbar machen, damit
  Bugreports nachvollziehbar sind.
