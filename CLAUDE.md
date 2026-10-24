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
