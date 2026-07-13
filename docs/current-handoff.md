# Current handoff

- Profile source: `profile.json`
- Portrait source: `assets/portrait-ascii-v3.png`
- Portrait converter: `scripts/make_ascii_portrait.py` (deterministic, source photo is not stored in the repository)
- Generator: `scripts/generate_profile.py`
- Generated artifacts: `profile-dark.svg`, `profile-light.svg`
- Automation: `.github/workflows/profile.yml` runs daily and on source changes
