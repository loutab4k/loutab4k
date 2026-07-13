# Agent instructions

- Keep the profile truthful: public stats must come from the GitHub API.
- Edit personal fields in `profile.json`; generated SVG files are build artifacts.
- Never add secrets or private repository names to the public profile.
- Before handoff, run `python scripts/generate_profile.py`, `git diff --check`, and the repository secret scan.
