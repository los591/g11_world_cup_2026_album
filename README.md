# g11_world_cup_2026_album
I was not able to complete my Panini album, so I made this one instead

# FIFA World Cup 2026 — Squad Explorer

A Streamlit app for browsing the FIFA World Cup 2026 group stage: drill down
from **Groups (A–L)** → **Countries** → **Players**, with bios and combined
2025/2026 season statistics pulled from API-Football.

## Files

- `app.py` — the Streamlit app.
- `qa_updated_wc_2026_players_with_stats_25_26.json` — player roster, group
  assignments, bios, and season statistics (QA-reviewed).
- `requirements.txt` — Python dependencies.
- `.devcontainer/` — config for running in GitHub Codespaces / VS Code Dev
  Containers.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app will be available at http://localhost:8501.

## Deploy on Streamlit Community Cloud

1. Push this folder to a GitHub repo (or push the repo containing this
   folder).
2. Go to [share.streamlit.io](https://share.streamlit.io) and create a new
   app.
3. Point it at this repo, set the branch, and set the main file path to
   `streamlit_deployment/app.py` (or `app.py` if this folder is the repo
   root).
4. Deploy — Streamlit Cloud will install `requirements.txt` automatically.

## Data notes

- Stats combine the 2025-26 season (Aug 2025–May 2026, e.g. European
  leagues) and the 2026 season (Jan–Dec, e.g. South American leagues, MLS,
  national teams).
- FIFA Club World Cup appearances are excluded from aggregated stats.
- To refresh the data, regenerate
  `qa_updated_wc_2026_players_with_stats_25_26.json` and replace the copy in
  this folder.
