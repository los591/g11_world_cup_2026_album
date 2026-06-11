import json
import os

import streamlit as st

st.set_page_config(
    page_title="FIFA World Cup 2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="auto",
)

# ── Session state ──────────────────────────────────────────────────────────────
for key, default in [
    ("view", "home"),
    ("selected_group", None),
    ("selected_country", None),
    ("selected_player", 0),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── CSS ────────────────────────────────────────────────────────────────────────
# The sidebar is only useful on the player-profile ("country") view, where it
# acts as a quick squad jump-list. Hide it everywhere else.
_sidebar_css = (
    "" if st.session_state.view == "country" else
    'section[data-testid="stSidebar"] { display: none; }\n'
    '[data-testid="collapsedControl"] { display: none; }'
)

st.markdown("""
<style>
""" + _sidebar_css + """
  .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

  .group-card {
    background: #1E293B; border-radius: 12px;
    padding: 1rem 1rem 0.5rem 1rem; margin-bottom: 0.25rem;
    border-top: 4px solid var(--g-color);
  }
  .group-label {
    font-size: 11px; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; color: var(--g-color); margin-bottom: 4px;
  }
  .group-countries { font-size: 13px; color: #CBD5E1; line-height: 1.8; }

  .country-card {
    background: #1E293B; border-radius: 12px;
    padding: 1.5rem 1rem; text-align: center;
    border-top: 4px solid var(--g-color);
  }
  .country-name-big { font-size: 1.1rem; font-weight: 700; color: white; }
  .country-sub { font-size: 12px; color: #94A3B8; margin-top: 4px; }

  .pos-badge {
    display: inline-block; padding: 3px 10px; border-radius: 999px;
    font-size: 12px; font-weight: 600; color: white; margin-bottom: 6px;
  }
  .info-pill {
    display: inline-block; background: #0F172A; border: 1px solid #334155;
    border-radius: 8px; padding: 4px 12px; font-size: 12px; color: #94A3B8;
    margin: 3px 4px 3px 0;
  }
  .info-pill span { color: white; font-weight: 600; }

  .stat-box {
    background: #1E293B; border-radius: 10px; padding: 0.8rem;
    text-align: center; border: 1px solid #334155;
  }
  .stat-val { font-size: 1.6rem; font-weight: 800; color: white; line-height: 1; }
  .stat-lbl { font-size: 10px; color: #64748B; margin-top: 4px; text-transform: uppercase; letter-spacing: 1px; }

  .league-row {
    display: flex; align-items: center; gap: 10px;
    background: #1E293B; border-radius: 8px; padding: 8px 12px; margin-bottom: 6px;
  }
  .league-name { font-size: 13px; color: white; font-weight: 600; }
  .league-sub  { font-size: 11px; color: #64748B; }

  .injured-badge {
    display: inline-block; background: #7F1D1D; color: #FCA5A5;
    border-radius: 999px; padding: 3px 10px; font-size: 11px; font-weight: 700;
  }

  .breadcrumb { font-size: 13px; color: #64748B; margin-bottom: 0.5rem; }
  .breadcrumb span { color: #94A3B8; }

  div[data-testid="stButton"] > button { border-radius: 8px; width: 100%; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
COUNTRIES_ORDERED = [
    "México",            "Sudáfrica",          "Corea del Sur",  "República Checa",
    "Canadá",            "Bosnia y Herzegovina","Qatar",          "Suiza",
    "Brasil",            "Marruecos",           "Haití",          "Escocia",
    "Estados Unidos",    "Paraguay",            "Australia",      "Turquía",
    "Alemania",          "Curazao",             "Costa de Marfil","Ecuador",
    "Países Bajos",      "Japón",               "Suecia",         "Túnez",
    "Bélgica",           "Egipto",              "Irán",           "Nueva Zelanda",
    "España",            "Cabo Verde",          "Arabia Saudita", "Uruguay",
    "Francia",           "Senegal",             "Irak",           "Noruega",
    "Argentina",         "Argelia",             "Austria",        "Jordania",
    "Portugal",          "RD Congo",            "Uzbekistán",     "Colombia",
    "Inglaterra",        "Croacia",             "Ghana",          "Panamá",
]

GROUP_LETTERS  = list("ABCDEFGHIJKL")
COUNTRY_GROUP  = {c: GROUP_LETTERS[i // 4] for i, c in enumerate(COUNTRIES_ORDERED)}
GROUPS         = {g: [c for c in COUNTRIES_ORDERED if COUNTRY_GROUP[c] == g] for g in GROUP_LETTERS}
GROUP_COLORS   = {
    "A": "#EF4444", "B": "#F97316", "C": "#F59E0B", "D": "#EAB308",
    "E": "#84CC16", "F": "#22C55E", "G": "#14B8A6", "H": "#06B6D4",
    "I": "#3B82F6", "J": "#6366F1", "K": "#A855F7", "L": "#EC4899",
}
POSITION_ORDER = ["Goalkeeper", "Defender", "Midfielder", "Forward"]
POSITION_COLOR = {
    "Goalkeeper": "#F59E0B", "Defender": "#10B981",
    "Midfielder": "#3B82F6", "Forward":  "#EF4444",
}

# ── Data ───────────────────────────────────────────────────────────────────────
EXCLUDED_LEAGUES = {"fifa club world cup", "fifa club world cup - play-in"}

# Leagues/competitions in these countries run on a Jan–Dec calendar, so a
# season tagged "2026" means the 2026 calendar year. Everything else is
# assumed to follow the Aug–May convention, where season "2025" means the
# 2025-26 campaign.
CALENDAR_YEAR_COUNTRIES = {
    "Argentina", "Bolivia", "Brazil", "Chile", "Colombia", "Ecuador",
    "Paraguay", "Peru", "Uruguay", "Venezuela", "Mexico", "USA", "Canada",
    "World",
}

def season_label(block):
    """Human-friendly season label, e.g. '2025' or '2025-26'."""
    season = block.get("_season")
    country = (block.get("league", {}) or {}).get("country", "")
    if country in CALENDAR_YEAR_COUNTRIES:
        return str(season)
    return f"{season}-{str(season + 1)[-2:]}"

def relevant_blocks(player):
    """Combine statistics_2025 + statistics_2026, dropping FIFA Club World Cup blocks."""
    blocks = []
    for season in (2025, 2026):
        for b in (player.get(f"statistics_{season}") or []):
            league_name = (b.get("league", {}) or {}).get("name", "")
            if league_name.strip().lower() in EXCLUDED_LEAGUES:
                continue
            blocks.append({**b, "_season": season})
    return blocks

@st.cache_data
def load_data():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "qa_updated_wc_2026_players_with_stats_25_26.json")
    with open(path, encoding="utf-8") as f:
        flat = json.load(f)

    all_players: dict[str, list] = {}
    for p in flat:
        all_players.setdefault(p["country"], []).append(p)

    for squad in all_players.values():
        squad.sort(key=lambda x: (
            POSITION_ORDER.index(x["position"]) if x["position"] in POSITION_ORDER else 99,
            x["player"],
        ))
    return all_players

all_players = load_data()

# ── Stat helpers ───────────────────────────────────────────────────────────────
def _sum(blocks, *keys):
    """Sum a nested key path across all stat blocks, ignoring None."""
    total = 0
    for b in blocks:
        val = b
        for k in keys:
            val = (val or {}).get(k)
        total += val or 0
    return total

def _avg_rating(blocks):
    ratings, apps = [], []
    for b in blocks:
        try:
            r = float(b.get("games", {}).get("rating") or 0)
            a = int(b.get("games", {}).get("appearences") or 0)
            if r and a:
                ratings.append(r * a)
                apps.append(a)
        except (ValueError, TypeError):
            pass
    if not apps:
        return None
    return sum(ratings) / sum(apps)

def aggregate(blocks):
    """Return a flat dict of aggregated stats across all league blocks."""
    if not blocks:
        return {}
    return {
        "appearances":    _sum(blocks, "games", "appearences"),
        "minutes":        _sum(blocks, "games", "minutes"),
        "rating":         _avg_rating(blocks),
        "goals":          _sum(blocks, "goals", "total"),
        "assists":        _sum(blocks, "goals", "assists"),
        "saves":          _sum(blocks, "goals", "saves"),
        "conceded":       _sum(blocks, "goals", "conceded"),
        "shots":          _sum(blocks, "shots", "total"),
        "shots_on":       _sum(blocks, "shots", "on"),
        "passes":         _sum(blocks, "passes", "total"),
        "key_passes":     _sum(blocks, "passes", "key"),
        "tackles":        _sum(blocks, "tackles", "total"),
        "interceptions":  _sum(blocks, "tackles", "interceptions"),
        "blocks":         _sum(blocks, "tackles", "blocks"),
        "duels_total":    _sum(blocks, "duels", "total"),
        "duels_won":      _sum(blocks, "duels", "won"),
        "dribbles_att":   _sum(blocks, "dribbles", "attempts"),
        "dribbles_ok":    _sum(blocks, "dribbles", "success"),
        "fouls_drawn":    _sum(blocks, "fouls", "drawn"),
        "fouls_comm":     _sum(blocks, "fouls", "committed"),
        "yellow":         _sum(blocks, "cards", "yellow"),
        "red":            _sum(blocks, "cards", "red"),
        "pen_scored":     _sum(blocks, "penalty", "scored"),
        "pen_missed":     _sum(blocks, "penalty", "missed"),
        "pen_saved":      _sum(blocks, "penalty", "saved"),
    }

def fmt(val, decimals=0, suffix=""):
    if val is None:
        return "—"
    if decimals:
        return f"{val:.{decimals}f}{suffix}"
    return f"{int(val)}{suffix}"

def pct(num, den):
    if not den:
        return "—"
    return f"{num/den*100:.0f}%"

def stat_box(val, label):
    return (
        f"<div class='stat-box'>"
        f"  <div class='stat-val'>{val}</div>"
        f"  <div class='stat-lbl'>{label}</div>"
        f"</div>"
    )

# ── Navigation ─────────────────────────────────────────────────────────────────
def go_home():
    st.session_state.view = "home"
    st.session_state.selected_group = st.session_state.selected_country = None
    st.session_state.selected_player = 0

def go_group(g):
    st.session_state.view = "group"
    st.session_state.selected_group = g
    st.session_state.selected_country = None
    st.session_state.selected_player = 0

def go_country(c):
    st.session_state.view = "country"
    st.session_state.selected_country = c
    st.session_state.selected_player = 0

# ── Banner ─────────────────────────────────────────────────────────────────────
def render_banner():
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 60%,#0f3460 100%);
                padding:2rem 2.5rem; border-radius:16px; text-align:center;
                margin-bottom:1.5rem; border:1px solid #1e40af;">
      <div style="font-size:3rem; line-height:1;">⚽</div>
      <div style="font-size:1rem; font-weight:700; letter-spacing:6px;
                  color:#93C5FD; text-transform:uppercase; margin-top:0.5rem;">FIFA</div>
      <div style="font-size:2.4rem; font-weight:900; color:white;
                  letter-spacing:2px; line-height:1.1;">WORLD CUP</div>
      <div style="font-size:2.8rem; font-weight:900;
                  background:linear-gradient(90deg,#EF4444,#F97316,#F59E0B,#22C55E,#3B82F6,#A855F7);
                  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                  letter-spacing:4px;">2026</div>
      <div style="font-size:0.85rem; color:#64748B; margin-top:0.4rem;
                  letter-spacing:3px;">USA &nbsp;·&nbsp; CANADA &nbsp;·&nbsp; MÉXICO</div>
    </div>
    """, unsafe_allow_html=True)

# ── VIEW: HOME ─────────────────────────────────────────────────────────────────
def render_home():
    render_banner()
    st.markdown("#### Select a Group")
    for row_start in range(0, 12, 4):
        cols = st.columns(4, gap="small")
        for ci, group in enumerate(GROUP_LETTERS[row_start:row_start + 4]):
            color = GROUP_COLORS[group]
            with cols[ci]:
                st.markdown(
                    f"<div class='group-card' style='--g-color:{color}'>"
                    f"<div class='group-label'>Group {group}</div>"
                    f"<div class='group-countries'>"
                    + "".join(f"<div>{c}</div>" for c in GROUPS[group])
                    + "</div></div>",
                    unsafe_allow_html=True,
                )
                if st.button(f"Group {group}", key=f"grp_{group}"):
                    go_group(group); st.rerun()

# ── VIEW: GROUP ────────────────────────────────────────────────────────────────
def render_group():
    group = st.session_state.selected_group
    color = GROUP_COLORS[group]
    render_banner()

    back, title = st.columns([1, 8])
    with back:
        if st.button("← Groups"): go_home(); st.rerun()
    with title:
        st.markdown(
            f"<div class='breadcrumb'>Groups › "
            f"<span style='color:{color};font-weight:700'>Group {group}</span></div>",
            unsafe_allow_html=True,
        )
    st.markdown(f"<h2 style='color:{color};margin:0 0 1.2rem 0'>Group {group}</h2>",
                unsafe_allow_html=True)

    cols = st.columns(4, gap="medium")
    for i, country in enumerate(GROUPS[group]):
        squad     = all_players.get(country, [])
        n_photos  = sum(1 for p in squad if p.get("player_photo"))
        with cols[i]:
            st.markdown(
                f"<div class='country-card' style='--g-color:{color}'>"
                f"<div class='country-name-big'>{country}</div>"
                f"<div class='country-sub'>{len(squad)} players</div>"
                f"<div class='country-sub'>{n_photos} with photo</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if st.button("View Squad", key=f"cty_{country}"):
                go_country(country); st.rerun()

# ── Sidebar squad navigator ───────────────────────────────────────────────────
def render_squad_sidebar(squad, sel_idx, country, group, color):
    with st.sidebar:
        st.markdown(
            f"<div style='font-weight:800;font-size:1.05rem;margin-bottom:0.25rem'>"
            f"{country} <span style='color:{color}'>· Group {group}</span></div>"
            f"<div style='font-size:12px;color:#64748B;margin-bottom:0.75rem'>"
            f"Tap a player to jump to their profile</div>",
            unsafe_allow_html=True,
        )
        for pos_group in POSITION_ORDER:
            group_players = [(i, p) for i, p in enumerate(squad) if p["position"] == pos_group]
            if not group_players:
                continue
            bg = POSITION_COLOR[pos_group]
            st.markdown(
                f"<span style='background:{bg};color:white;padding:2px 10px;"
                f"border-radius:999px;font-size:11px;font-weight:600'>{pos_group}s</span>",
                unsafe_allow_html=True,
            )
            for idx, p in group_players:
                is_sel = idx == sel_idx
                label = ("⭐ " if is_sel else "") + p["player"]
                if st.button(label, key=f"sb_{idx}", use_container_width=True,
                              type="primary" if is_sel else "secondary"):
                    st.session_state.selected_player = idx
                    st.rerun()
        st.markdown("")

# ── VIEW: COUNTRY / SQUAD ──────────────────────────────────────────────────────
def render_country():
    country  = st.session_state.selected_country
    squad    = all_players.get(country, [])
    group    = COUNTRY_GROUP.get(country, "?")
    color    = GROUP_COLORS.get(group, "#3B82F6")
    sel_idx  = min(st.session_state.selected_player, len(squad) - 1)
    player   = squad[sel_idx]

    render_squad_sidebar(squad, sel_idx, country, group, color)

    # ── Header / breadcrumb ───────────────────────────────────────────────────
    back, title = st.columns([1, 8])
    with back:
        if st.button(f"← Group {group}"):
            st.session_state.view = "group"
            st.session_state.selected_country = None; st.rerun()
    with title:
        st.markdown(
            f"<div class='breadcrumb'>Groups › "
            f"<span style='color:{color}'>Group {group}</span> › "
            f"<span style='color:white'>{country}</span></div>",
            unsafe_allow_html=True,
        )
    st.markdown(
        f"<h2 style='margin:0 0 1rem 0'>{country} "
        f"<span style='font-size:1rem;background:{color};color:white;"
        f"padding:3px 12px;border-radius:999px;font-weight:600;vertical-align:middle'>"
        f"Group {group}</span></h2>",
        unsafe_allow_html=True,
    )

    # ── Player card ───────────────────────────────────────────────────────────
    info   = player.get("player_info") or {}
    blocks = relevant_blocks(player)
    stats  = aggregate(blocks)
    pos    = player["position"]
    pos_color = POSITION_COLOR.get(pos, "#6B7280")

    photo_url = info.get("photo") or player.get("player_photo") or ""
    birth     = info.get("birth", {}) or {}
    injured   = info.get("injured", False)

    photo_col, bio_col = st.columns([1, 3], gap="large")

    with photo_col:
        if photo_url:
            st.image(photo_url, width=190)
        else:
            st.markdown(
                "<div style='width:190px;height:190px;background:#0F172A;"
                "border-radius:12px;display:flex;align-items:center;"
                "justify-content:center;font-size:64px;border:1px solid #1E293B'>👤</div>",
                unsafe_allow_html=True,
            )

    with bio_col:
        injured_badge = " <span class='injured-badge'>⚠ INJURED</span>" if injured else ""
        st.markdown(
            f"<div style='margin-bottom:0.3rem'>"
            f"  <span class='pos-badge' style='background:{pos_color}'>{pos}</span>"
            f"  {injured_badge}"
            f"</div>"
            f"<h2 style='margin:0 0 0.6rem 0'>{player['player']}</h2>",
            unsafe_allow_html=True,
        )

        pills = []
        if info.get("age"):
            pills.append(f"🎂 Age <span>{info['age']}</span>")
        if birth.get("date"):
            pills.append(f"📅 Born <span>{birth['date']}</span>")
        if birth.get("place"):
            pills.append(f"📍 {birth['place']}, {birth.get('country','')}")
        if info.get("nationality"):
            pills.append(f"🌍 <span>{info['nationality']}</span>")
        if info.get("height"):
            pills.append(f"📏 <span>{info['height']} cm</span>")
        if info.get("weight"):
            pills.append(f"⚖️ <span>{info['weight']} kg</span>")
        pills.append(f"🏟️ <span>{player['club']}</span>")

        st.markdown(
            "".join(f"<span class='info-pill'>{p}</span>" for p in pills),
            unsafe_allow_html=True,
        )

    st.markdown("")

    # ── Stats tabs ────────────────────────────────────────────────────────────
    STATS_NOTE = (
        "ℹ️ Totals combine the 2025-26 season (Aug 2025–May 2026, e.g. European "
        "leagues) and the 2026 season (Jan–Dec, e.g. South American leagues, "
        "MLS, national teams) to date — see the **Leagues** tab for the "
        "breakdown. FIFA Club World Cup appearances are excluded."
    )

    if stats:
        tab_overview, tab_attack, tab_defense, tab_leagues = st.tabs(
            ["📊 Season Overview", "⚡ Attacking", "🛡️ Defensive", "🏆 Leagues"]
        )

        with tab_overview:
            st.caption(STATS_NOTE)
            c = st.columns(5)
            c[0].markdown(stat_box(fmt(stats["appearances"]), "Appearances"), unsafe_allow_html=True)
            c[1].markdown(stat_box(fmt(stats["minutes"]), "Minutes"), unsafe_allow_html=True)
            c[2].markdown(stat_box(fmt(stats["rating"], 2) if stats["rating"] else "—", "Avg Rating"), unsafe_allow_html=True)
            c[3].markdown(stat_box(fmt(stats["goals"]), "Goals"), unsafe_allow_html=True)
            c[4].markdown(stat_box(fmt(stats["assists"]), "Assists"), unsafe_allow_html=True)

            st.markdown("")
            c2 = st.columns(5)
            c2[0].markdown(stat_box(fmt(stats["yellow"]), "Yellow Cards"), unsafe_allow_html=True)
            c2[1].markdown(stat_box(fmt(stats["red"]), "Red Cards"), unsafe_allow_html=True)
            c2[2].markdown(stat_box(fmt(stats["fouls_comm"]), "Fouls Committed"), unsafe_allow_html=True)
            c2[3].markdown(stat_box(fmt(stats["fouls_drawn"]), "Fouls Drawn"), unsafe_allow_html=True)
            if pos == "Goalkeeper":
                c2[4].markdown(stat_box(fmt(stats["saves"]), "Saves"), unsafe_allow_html=True)
            else:
                c2[4].markdown(stat_box(pct(stats["duels_won"], stats["duels_total"]), "Duels Won"), unsafe_allow_html=True)

        with tab_attack:
            st.caption(STATS_NOTE)
            if pos == "Goalkeeper":
                c = st.columns(4)
                c[0].markdown(stat_box(fmt(stats["saves"]), "Saves"), unsafe_allow_html=True)
                c[1].markdown(stat_box(fmt(stats["conceded"]), "Goals Conceded"), unsafe_allow_html=True)
                c[2].markdown(stat_box(fmt(stats["pen_saved"]), "Penalties Saved"), unsafe_allow_html=True)
                c[3].markdown(stat_box(fmt(stats["passes"]), "Total Passes"), unsafe_allow_html=True)
            else:
                c = st.columns(5)
                c[0].markdown(stat_box(fmt(stats["goals"]), "Goals"), unsafe_allow_html=True)
                c[1].markdown(stat_box(fmt(stats["assists"]), "Assists"), unsafe_allow_html=True)
                c[2].markdown(stat_box(fmt(stats["shots"]), "Shots"), unsafe_allow_html=True)
                c[3].markdown(stat_box(fmt(stats["shots_on"]), "On Target"), unsafe_allow_html=True)
                c[4].markdown(stat_box(pct(stats["shots_on"], stats["shots"]), "Shot Accuracy"), unsafe_allow_html=True)

                st.markdown("")
                c2 = st.columns(5)
                c2[0].markdown(stat_box(fmt(stats["key_passes"]), "Key Passes"), unsafe_allow_html=True)
                c2[1].markdown(stat_box(fmt(stats["passes"]), "Total Passes"), unsafe_allow_html=True)
                c2[2].markdown(stat_box(fmt(stats["dribbles_att"]), "Dribbles Att."), unsafe_allow_html=True)
                c2[3].markdown(stat_box(fmt(stats["dribbles_ok"]), "Dribbles Won"), unsafe_allow_html=True)
                c2[4].markdown(stat_box(pct(stats["dribbles_ok"], stats["dribbles_att"]), "Dribble Success"), unsafe_allow_html=True)

                if stats["pen_scored"] or stats["pen_missed"]:
                    st.markdown("")
                    c3 = st.columns(3)
                    c3[0].markdown(stat_box(fmt(stats["pen_scored"]), "Penalties Scored"), unsafe_allow_html=True)
                    c3[1].markdown(stat_box(fmt(stats["pen_missed"]), "Penalties Missed"), unsafe_allow_html=True)
                    c3[2].markdown(stat_box(pct(stats["pen_scored"], stats["pen_scored"] + stats["pen_missed"]), "Penalty Conv."), unsafe_allow_html=True)

        with tab_defense:
            st.caption(STATS_NOTE)
            c = st.columns(5)
            c[0].markdown(stat_box(fmt(stats["tackles"]), "Tackles"), unsafe_allow_html=True)
            c[1].markdown(stat_box(fmt(stats["interceptions"]), "Interceptions"), unsafe_allow_html=True)
            c[2].markdown(stat_box(fmt(stats["blocks"]), "Blocks"), unsafe_allow_html=True)
            c[3].markdown(stat_box(fmt(stats["duels_total"]), "Duels"), unsafe_allow_html=True)
            c[4].markdown(stat_box(pct(stats["duels_won"], stats["duels_total"]), "Duels Won %"), unsafe_allow_html=True)

        with tab_leagues:
            st.markdown("**Season appearances by league (2025 & 2026)**")
            st.caption(
                "ℹ️ Seasons are labeled **2025-26** for leagues that run "
                "Aug–May (e.g. most European leagues), and as a single "
                "year (e.g. **2026**) for leagues that run Jan–Dec "
                "(e.g. South American leagues, MLS, national teams)."
            )
            for b in sorted(
                blocks,
                key=lambda x: (x.get("games", {}).get("appearences") or 0, x.get("_season", 0)),
                reverse=True,
            ):
                games  = b.get("games", {}) or {}
                league = b.get("league", {}) or {}
                team   = b.get("team", {}) or {}
                apps   = games.get("appearences") or 0
                mins   = games.get("minutes") or 0
                rating = games.get("rating")
                season = b.get("_season")
                if not apps:
                    continue
                team_logo = team.get("logo", "")
                league_flag = league.get("flag", "")
                logo_html = (
                    f"<img src='{team_logo}' style='width:24px;height:24px;"
                    f"object-fit:contain;border-radius:4px'>"
                    if team_logo else "🏟️"
                )
                flag_html = (
                    f"<img src='{league_flag}' style='width:20px;height:14px;"
                    f"object-fit:cover;border-radius:2px'>"
                    if league_flag else ""
                )
                rating_str = f"  ·  ⭐ {float(rating):.2f}" if rating else ""
                season_html = (
                    f"<span class='info-pill' style='margin:0 0 0 8px'>{season_label(b)}</span>"
                    if season else ""
                )
                st.markdown(
                    f"<div class='league-row'>"
                    f"  {logo_html}"
                    f"  <div style='flex:1'>"
                    f"    <div class='league-name'>{team.get('name','—')}</div>"
                    f"    <div class='league-sub'>{flag_html} {league.get('name','—')} · "
                    f"    {apps} apps · {mins} min{rating_str}</div>"
                    f"  </div>"
                    f"  {season_html}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
    else:
        st.info("No 2025/2026 season statistics available for this player.")

    st.divider()

    # ── Full squad grid ───────────────────────────────────────────────────────
    st.markdown(f"#### Full Squad — {country}")
    for pos_group in POSITION_ORDER:
        group_players = [(i, p) for i, p in enumerate(squad) if p["position"] == pos_group]
        if not group_players:
            continue
        bg = POSITION_COLOR[pos_group]
        st.markdown(
            f"<span style='background:{bg};color:white;padding:3px 12px;"
            f"border-radius:999px;font-size:12px;font-weight:600'>{pos_group}s</span>",
            unsafe_allow_html=True,
        )
        cols = st.columns(len(group_players), gap="small")
        for col, (idx, p) in zip(cols, group_players):
            is_sel = idx == sel_idx
            photo  = (p.get("player_info") or {}).get("photo") or p.get("player_photo", "")
            with col:
                if photo:
                    st.image(photo, use_container_width=True)
                else:
                    st.markdown(
                        "<div style='aspect-ratio:1;background:#0F172A;border-radius:8px;"
                        "display:flex;align-items:center;justify-content:center;font-size:28px'>👤</div>",
                        unsafe_allow_html=True,
                    )
                name_style = "color:#F59E0B;font-weight:700" if is_sel else ""
                st.markdown(
                    f"<p style='font-size:10px;text-align:center;margin:2px 0 0 0;"
                    f"line-height:1.3;{name_style}'>{p['player']}</p>",
                    unsafe_allow_html=True,
                )
                if st.button("▸", key=f"p_{idx}", help=p["player"]):
                    st.session_state.selected_player = idx; st.rerun()
        st.markdown("")

# ── Router ─────────────────────────────────────────────────────────────────────
view = st.session_state.view
if   view == "home":    render_home()
elif view == "group":   render_group()
elif view == "country": render_country()
