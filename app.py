"""
RAG Music Recommender — Streamlit Application
Run with: streamlit run app.py
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()

import requests
import google.generativeai as genai
import streamlit as st

from validation import GENRE_OPTIONS, MOOD_OPTIONS
from deezer_client import DeezerTrackData
import streamlit.components.v1 as components
from deezer_catalog import fetch_tracks_for_genre, fetch_similar_tracks
from genre_detector import detect as detect_genre_multi
from llm_client import generate_explanation, generate_boilerplate_explanation  # type: ignore[import]
from feedback import (
    FeedbackRecord,
    compute_feedback_summary,
    load_feedback,
    save_feedback,
)
from pipeline import (
    PipelineState,
    run_stage_1_validate,
    run_stage_2_retrieve,
    run_stage_3_external,
    run_stage_4_augment,
    run_stage_5_explain,
    run_stage_6_validate_explanations,
    run_stage_7_rank,
    run_stage_8_finalize,
)

_THEME_CSS = """
<style>
/* ── Hide white Streamlit chrome ───────────────────────────── */
header[data-testid="stHeader"] { background-color: #0d0d1a !important; border-bottom: 1px solid #2d1b69; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }

/* ── Base — white text on black ────────────────────────────── */
html, body, .stApp { background-color: #0d0d1a !important; color: #ffffff; }
.main .block-container { padding-top: 1.5rem; background-color: #0d0d1a; }
p, span, li, div { color: #ffffff; }
label { color: #ffffff !important; }
h1, h2, h3, h4, h5, h6 { color: #ffffff !important; }

/* ── Sidebar ───────────────────────────────────────────────── */
.stSidebar, section[data-testid="stSidebar"] > div { background-color: #130a2a !important; }
section[data-testid="stSidebar"] { border-right: 1px solid #4c1d95; }
.stSidebar p, .stSidebar span, .stSidebar label,
.stSidebar div, .stSidebar h2, .stSidebar h3 { color: #ffffff !important; }

/* ── Buttons ───────────────────────────────────────────────── */
.stButton > button[kind="primary"],
.stFormSubmitButton > button {
    background: linear-gradient(135deg, #6d28d9, #7c3aed) !important;
    border: none !important; color: #ffffff !important; font-weight: 600;
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button:hover { background: #5b21b6 !important; }
.stButton > button[kind="secondary"] {
    border: 1px solid #6d28d9 !important; color: #ffffff !important; background: transparent !important;
}

/* ── Text inputs ───────────────────────────────────────────── */
.stTextInput input, .stTextArea textarea {
    background-color: #1a0a2e !important;
    color: #ffffff !important;
    border: 1px solid #4c1d95 !important;
    border-radius: 6px !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color: #9f7aea !important; }
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #7c3aed !important; box-shadow: 0 0 0 1px #7c3aed !important;
}

/* ── Selectbox ─────────────────────────────────────────────── */
.stSelectbox [data-baseweb="select"] > div:first-child {
    background-color: #1a0a2e !important; border-color: #4c1d95 !important;
}
.stSelectbox [data-baseweb="select"] span,
.stSelectbox [data-baseweb="select"] div { color: #ffffff !important; }
[data-baseweb="popover"] ul { background-color: #1a0a2e !important; }
[role="option"] { background-color: #1a0a2e !important; color: #ffffff !important; }
[role="option"]:hover, [aria-selected="true"] { background-color: #2d1b69 !important; }

/* ── Form container ────────────────────────────────────────── */
[data-testid="stForm"] {
    background-color: #120824 !important;
    border: 1px solid #2d1b69 !important;
    border-radius: 10px !important;
    padding: 1rem !important;
}

/* ── Tabs ──────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] { background-color: #0d0d1a !important; border-bottom: 1px solid #4c1d95; }
.stTabs [data-baseweb="tab"] { color: #a78bfa !important; background-color: transparent !important; }
.stTabs [aria-selected="true"] { color: #ffffff !important; border-bottom: 2px solid #7c3aed !important; }

/* ── Expanders ─────────────────────────────────────────────── */
.stExpander { border: 1px solid #4c1d95 !important; border-radius: 8px !important; }
.stExpander > details > summary {
    background-color: #1e0a3c !important; border-radius: 8px 8px 0 0 !important; color: #ffffff !important;
}
.stExpander > details > summary:hover { background-color: #2d1060 !important; }
.stExpander > details > div { background-color: #120824 !important; }

/* ── Cards ─────────────────────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #2d1b69 !important; border-radius: 10px !important; background-color: #120824 !important;
}

/* ── Progress bar ──────────────────────────────────────────── */
.stProgress > div > div > div { background: linear-gradient(90deg, #6d28d9, #a855f7) !important; }
[data-testid="stProgressBarTrack"] { background-color: #2d1b69 !important; }

/* ── Radio ─────────────────────────────────────────────────── */
.stRadio label, .stRadio p { color: #ffffff !important; }

/* ── Captions — subtle purple, not white ──────────────────── */
.stCaption, [data-testid="stCaptionContainer"] p { color: #a78bfa !important; }

/* ── Metrics ───────────────────────────────────────────────── */
[data-testid="stMetricLabel"] p { color: #a78bfa !important; }
[data-testid="stMetricValue"] { color: #ffffff !important; }

/* ── Alerts ────────────────────────────────────────────────── */
.stAlert { border-radius: 8px !important; }
.stAlert p { color: #ffffff !important; }

/* ── Dividers ──────────────────────────────────────────────── */
hr { border-color: #2d1b69 !important; }

/* ── Spotify-style search input ──────────────────────────────── */
input[placeholder="What do you want to play?"] {
    border-radius: 500px !important;
    background-color: #ffffff !important;
    color: #121212 !important;
    border: none !important;
    height: 48px !important;
    font-size: 15px !important;
    padding: 0 1.5rem !important;
    box-shadow: none !important;
}
input[placeholder="What do you want to play?"]:focus {
    box-shadow: 0 0 0 3px rgba(255,255,255,0.25) !important;
    border: none !important;
}
input[placeholder="What do you want to play?"]::placeholder { color: #737373 !important; }

/* ── Transparent columns (prevents white bleed inside containers) ─ */
[data-testid="stHorizontalBlock"], [data-testid="stColumn"] {
    background: transparent !important;
}
</style>
"""


# ---------------------------------------------------------------------------
# Session initialisation
# ---------------------------------------------------------------------------

def init_session() -> None:
    if "pipeline" not in st.session_state:
        st.session_state["pipeline"] = PipelineState()
    if "anthropic_client" not in st.session_state:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        genai.configure(api_key=api_key)
        st.session_state["anthropic_client"] = genai.GenerativeModel("gemma-3-1b-it")
    if "k" not in st.session_state:
        st.session_state["k"] = 5
    if "style" not in st.session_state:
        st.session_state["style"] = "genre-first"
    if "threshold" not in st.session_state:
        st.session_state["threshold"] = 0.0
    if "ai_enabled" not in st.session_state:
        st.session_state["ai_enabled"] = True
    if "deezer_cache" not in st.session_state:
        st.session_state["deezer_cache"] = {}
    if "autocomplete_results" not in st.session_state:
        st.session_state["autocomplete_results"] = []
    if "autocomplete_last_q" not in st.session_state:
        st.session_state["autocomplete_last_q"] = ""
    if "recent_searches" not in st.session_state:
        st.session_state["recent_searches"] = []


def reset_pipeline() -> None:
    st.session_state["pipeline"] = PipelineState()
    st.session_state["deezer_cache"] = {}
    st.session_state["autocomplete_results"] = []
    st.session_state["autocomplete_last_q"] = ""


# ---------------------------------------------------------------------------
# Helper UI components
# ---------------------------------------------------------------------------

def _flags_box(flags: list[str], level: str = "warning") -> None:
    if not flags:
        return
    fn = st.warning if level == "warning" else st.error
    for flag in flags:
        fn(flag)


def _on_autocomplete_change() -> None:
    """Fetch Deezer suggestions on each text_input change; debounced by last query."""
    q = st.session_state.get("similar_input", "").strip()
    if len(q) >= 3 and q != st.session_state.get("autocomplete_last_q", ""):
        try:
            resp = requests.get(
                "https://api.deezer.com/search",
                params={"q": q, "limit": 5},
                timeout=4,
            )
            resp.raise_for_status()
            results = [
                {
                    "title": t.get("title", ""),
                    "artist": t.get("artist", {}).get("name", ""),
                    "cover_art": t.get("album", {}).get("cover_small", ""),
                    "type": "Song",
                    "query_str": (
                        f"{t.get('title', '')} by {t.get('artist', {}).get('name', '')}"
                    ),
                }
                for t in resp.json().get("data", [])
            ]
        except Exception:
            results = []
        st.session_state["autocomplete_results"] = results
        st.session_state["autocomplete_last_q"] = q
    elif len(q) < 3:
        st.session_state["autocomplete_results"] = []
        st.session_state["autocomplete_last_q"] = ""


def _add_to_recent_searches(entry: dict) -> None:
    recent: list = st.session_state.get("recent_searches", [])
    recent = [r for r in recent if r.get("query_str") != entry.get("query_str")]
    recent.insert(0, entry)
    st.session_state["recent_searches"] = recent[:6]


def _render_spotify_search() -> str:
    """Renders Spotify-style search bar with live suggestions and recent searches.
    Returns the currently active query string."""

    if "search_pending" in st.session_state:
        st.session_state["similar_input"] = st.session_state.pop("search_pending")

    st.text_input(
        "Search",
        key="similar_input",
        placeholder="What do you want to play?",
        on_change=_on_autocomplete_change,
        label_visibility="collapsed",
    )

    autocomplete_results: list = st.session_state.get("autocomplete_results", [])
    recent_searches: list = st.session_state.get("recent_searches", [])
    items = autocomplete_results if autocomplete_results else recent_searches
    is_recent = not bool(autocomplete_results) and bool(recent_searches)

    if not items:
        return st.session_state.get("similar_input", "")

    with st.container(border=True):
        if is_recent:
            st.markdown(
                "<p style='color:#fff;font-size:13px;font-weight:700;margin:0 0 6px'>Recent searches</p>",
                unsafe_allow_html=True,
            )

        for i, item in enumerate(items):
            col_thumb, col_info, col_btn = st.columns([1, 8, 2])

            with col_thumb:
                cover = item.get("cover_art", "")
                if cover:
                    st.markdown(
                        f'<img src="{cover}" style="width:44px;height:44px;'
                        f'border-radius:4px;object-fit:cover;margin-top:2px">',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div style="width:44px;height:44px;background:#3d1b69;'
                        'border-radius:4px;display:flex;align-items:center;'
                        'justify-content:center;font-size:20px;margin-top:2px">🎵</div>',
                        unsafe_allow_html=True,
                    )

            with col_info:
                st.markdown(
                    f'<div style="padding-top:4px">'
                    f'<span style="color:#fff;font-size:14px;font-weight:500">{item["title"]}</span><br>'
                    f'<span style="color:#a7a7a7;font-size:12px">'
                    f'{item.get("type","Song")} &bull; {item["artist"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            with col_btn:
                if st.button("Select ↗", key=f"srch_sel_{i}", type="secondary"):
                    st.session_state["search_pending"] = item["query_str"]
                    _add_to_recent_searches(item)
                    st.session_state["autocomplete_results"] = []
                    st.rerun()

    return st.session_state.get("similar_input", "")


def _cover_play_component(
    cover_url: str | None,
    preview_url: str | None,
    song_id: int,
    width: int = 90,
) -> None:
    """Clickable album cover that plays/pauses the 30-sec preview. No st.audio bar shown."""
    cover_src = cover_url or ""
    fallback_display = "none" if cover_src else "flex"
    img_display = "block" if cover_src else "none"

    if not preview_url:
        if cover_src:
            components.html(
                f'<img src="{cover_src}" style="width:{width}px;height:{width}px;'
                f'border-radius:8px;object-fit:cover;display:block">',
                height=width + 10,
            )
        else:
            st.markdown(
                "<div style='font-size:36px;text-align:center;padding:8px'>🎵</div>",
                unsafe_allow_html=True,
            )
        return

    html = f"""
    <style>
      .cw{{position:relative;width:{width}px;height:{width}px;cursor:pointer;
           border-radius:8px;overflow:hidden;}}
      .cw img{{width:100%;height:100%;object-fit:cover;display:{img_display};}}
      .cf{{width:100%;height:100%;background:#1e0a3c;
           display:{fallback_display};align-items:center;justify-content:center;font-size:32px;}}
      .pi{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
           background:rgba(0,0,0,0.65);border-radius:50%;width:32px;height:32px;
           display:flex;align-items:center;justify-content:center;
           font-size:15px;color:#fff;pointer-events:none;user-select:none;}}
    </style>
    <div class="cw" onclick="tp()">
      <img src="{cover_src}"
           onerror="this.style.display='none';document.getElementById('fb{song_id}').style.display='flex'"/>
      <div class="cf" id="fb{song_id}">🎵</div>
      <div class="pi" id="ic{song_id}">▶</div>
    </div>
    <audio id="au{song_id}" src="{preview_url}" preload="none"></audio>
    <script>
      var a=document.getElementById('au{song_id}');
      var ic=document.getElementById('ic{song_id}');
      function tp(){{if(a.paused){{a.play();ic.textContent='⏸';}}else{{a.pause();ic.textContent='▶';}}}}
      a.onended=function(){{ic.textContent='▶';}};
    </script>
    """
    components.html(html, height=width + 10)


def _song_card(song: dict, score: float, explanation: str, index: int) -> None:
    """3-column card used in the Results tab."""
    sid = song.get("id")
    deezer_data = st.session_state["deezer_cache"].get(sid)

    with st.container(border=True):
        col_art, col_info, col_score = st.columns([1, 3, 1])

        with col_art:
            _cover_play_component(
                deezer_data.cover_art_url if deezer_data else None,
                deezer_data.preview_url if deezer_data else None,
                sid,
                width=100,
            )

        with col_info:
            st.markdown(f"**{index}. {song.get('title')}** — *{song.get('artist')}*")
            st.caption(
                f"Genre: {song.get('genre')} | Mood: {song.get('mood')} | "
                f"Energy: {song.get('energy')} | Acousticness: {song.get('acousticness')}"
            )
            st.markdown(explanation)
            if deezer_data and not deezer_data.preview_url and deezer_data.track_id is not None:
                st.caption("_No preview available_")

        with col_score:
            st.metric("Score", f"{score:.2f}")
            st.progress(min(score, 1.0))


def _populate_deezer_cache_from_catalog(songs: list[dict]) -> None:
    """
    Store DeezerTrackData entries in the cache directly from catalog dicts.
    Deezer catalog tracks already carry cover_art_url / preview_url — no
    second API lookup needed.
    """
    cache: dict = st.session_state["deezer_cache"]
    for song in songs:
        sid = song.get("id")
        if sid is not None and sid not in cache:
            cache[sid] = DeezerTrackData(
                track_id=sid,
                title=song.get("title", ""),
                artist=song.get("artist", ""),
                cover_art_url=song.get("cover_art_url"),
                preview_url=song.get("preview_url"),
                deezer_url=song.get("deezer_url"),
            )
    st.session_state["deezer_cache"] = cache


# ---------------------------------------------------------------------------
# Tab 1 — Preferences & Input
# ---------------------------------------------------------------------------

def render_preferences_tab() -> None:
    st.header("Your Music Preferences")
    state: PipelineState = st.session_state["pipeline"]

    # ── Spotify-style search (outside form so on_change fires per keystroke) ──
    st.markdown("**Find similar songs** *(optional — type 3+ characters for suggestions)*")
    selected_similar = _render_spotify_search()

    st.divider()

    # ── Preferences form ──────────────────────────────────────────────────────
    with st.form("prefs_form"):
        genre = st.selectbox("Favorite Genre", GENRE_OPTIONS, index=0)
        mood = st.selectbox("Favorite Mood", MOOD_OPTIONS, index=0)
        energy = st.slider("Target Energy Level", 0.0, 1.0, 0.6, 0.05)
        likes_acoustic = st.toggle("I like acoustic music", value=False)

        col1, col2 = st.columns(2)
        submitted = col1.form_submit_button("Get Recommendations", type="primary")
        col2.form_submit_button("Reset", on_click=reset_pipeline)

    if not submitted:
        return

    # ── Genre detection ───────────────────────────────────────────────────────
    query_for_detection = selected_similar or st.session_state.get("similar_input", "").strip()
    effective_genre = genre
    if query_for_detection:
        with st.spinner("Detecting genre (MusicBrainz · Deezer · iTunes)…"):
            result = detect_genre_multi(query_for_detection)
        if result and result.mapped_genre:
            effective_genre = result.mapped_genre
            source_str = " + ".join(result.sources)
            artist_note = f" · artist: *{result.deezer_artist}*" if result.deezer_artist else ""
            conf_icon = "✅" if result.confidence == "high" else "ℹ️"
            st.info(
                f"{conf_icon} **{source_str}**: {result.raw_genre}"
                f" → genre: **{effective_genre}**{artist_note}"
            )
        else:
            st.caption(f"Genre detection found no match — using manual selection: {genre}")

    user_prefs = {
        "genre": effective_genre,
        "mood": mood,
        "energy": energy,
        "likes_acoustic": likes_acoustic,
    }
    state.user_prefs = user_prefs
    state = run_stage_1_validate(state)

    val = state.input_validation
    if val.flags:
        _flags_box(val.flags)
    if not val.is_valid:
        st.error("Please correct the input errors above before continuing.")
        st.session_state["pipeline"] = state
        return
    if val.requires_human_review:
        st.warning("Some values were auto-corrected. Please review:")
        st.json(val.corrected_input)
        if not st.button("Approve corrections and continue"):
            st.session_state["pipeline"] = state
            return

    # ── Fetch real tracks from Deezer ─────────────────────────────────────────
    resolved_genre = val.corrected_input.get("genre", effective_genre)
    with st.spinner("Fetching tracks from Deezer…"):
        if query_for_detection:
            deezer_tracks = fetch_similar_tracks(query_for_detection, resolved_genre, k=20)
        else:
            deezer_tracks = fetch_tracks_for_genre(resolved_genre, k=20)

    if not deezer_tracks:
        st.warning("Deezer returned no tracks — check your internet connection.")
        st.session_state["pipeline"] = state
        return

    # Store cover art / previews in cache immediately from catalog data
    _populate_deezer_cache_from_catalog(deezer_tracks)

    # ── Run pipeline stages 2–6 automatically ────────────────────────────────
    with st.spinner("Building recommendations and generating explanations…"):
        state = run_stage_2_retrieve(
            state,
            deezer_tracks,
            k_candidates=15,
            threshold=0.0,
            style=st.session_state["style"],
        )
        state = run_stage_3_external(state)
        state = run_stage_4_augment(state)
        state = run_stage_5_explain(
            state,
            st.session_state["anthropic_client"],
            ai_enabled=st.session_state["ai_enabled"],
        )
        state = run_stage_6_validate_explanations(state)

    st.session_state["pipeline"] = state
    n = len(state.candidates or [])
    st.success(f"Found {n} tracks. Move to the **Review** tab.")


# ---------------------------------------------------------------------------
# Tab 2 — Review (merged retrieval + explanation)
# ---------------------------------------------------------------------------

def render_review_tab() -> None:
    st.header("Review Recommendations")
    state: PipelineState = st.session_state["pipeline"]

    if state.explanation_validations is None:
        st.info("Submit your preferences first.")
        return

    augmented = state.augmented_songs or []
    validations = list(state.explanation_validations)
    updated_explanations = list(state.explanations or [])
    cache: dict = st.session_state["deezer_cache"]

    for i, (song, val) in enumerate(zip(augmented, validations)):
        sid = song.get("id")
        dz: DeezerTrackData | None = cache.get(sid)
        cover_url = dz.cover_art_url if dz else None
        preview_url = dz.preview_url if dz else None

        with st.container(border=True):
            col_img, col_title = st.columns([1, 6])

            with col_img:
                _cover_play_component(cover_url, preview_url, sid, width=80)

            with col_title:
                icon = "❌" if val.rejected else ("✅" if val.approved else "⚠️")
                st.markdown(f"#### {icon} {song.get('title')} — *{song.get('artist')}*")
                st.caption(
                    f"Genre: {song.get('genre')} · Mood: {song.get('mood')} · "
                    f"Energy: {song.get('energy')} · Confidence: {val.confidence_score:.0%}"
                )

            exp_label = "▶ Play & Explanation"
            with st.expander(exp_label, expanded=val.rejected):
                if not preview_url:
                    st.caption("_No preview available_")

                if val.flags:
                    _flags_box(val.flags)
                if val.rejected:
                    st.warning("This song has been rejected and will be excluded from results.")

                new_text = st.text_area(
                    "Explanation (editable)",
                    value=val.explanation,
                    key=f"exp_{sid}_{i}",
                    height=90,
                    disabled=val.rejected,
                )
                if not val.rejected:
                    updated_explanations[i] = new_text

                c1, c2, c3 = st.columns(3)

                if c1.button("Approve", key=f"approve_exp_{i}"):
                    validations[i].approved = True
                    validations[i].rejected = False
                    validations[i].explanation = new_text
                    st.rerun()

                if c2.button("Regenerate", key=f"regen_exp_{i}", disabled=val.rejected):
                    with st.spinner("Regenerating…"):
                        if st.session_state["ai_enabled"]:
                            new_exp = generate_explanation(
                                song,
                                state.input_validation.corrected_input,
                                st.session_state["anthropic_client"],
                            )
                        else:
                            new_exp = generate_boilerplate_explanation(
                                song,
                                state.input_validation.corrected_input,
                            )
                    updated_explanations[i] = new_exp
                    validations[i].explanation = new_exp
                    validations[i].approved = True
                    validations[i].rejected = False
                    st.rerun()

                if c3.button(
                    "Un-reject" if val.rejected else "Reject",
                    key=f"reject_exp_{i}",
                    type="secondary",
                ):
                    if val.rejected:
                        validations[i].rejected = False
                        validations[i].approved = False
                    else:
                        validations[i].rejected = True
                        validations[i].approved = False
                    st.rerun()

    # Persist edits
    for i, val in enumerate(validations):
        val.explanation = updated_explanations[i]
    state.explanation_validations = validations
    state.explanations = updated_explanations
    st.session_state["pipeline"] = state

    n_approved = sum(1 for v in validations if v.approved and not v.rejected)
    n_rejected = sum(1 for v in validations if v.rejected)
    n_pending = sum(1 for v in validations if not v.approved and not v.rejected)
    st.caption(f"✅ {n_approved} approved · ❌ {n_rejected} rejected · ⚠️ {n_pending} pending")

    if st.button("Approve All & Rank", type="primary"):
        for val in validations:
            if not val.rejected:
                val.approved = True
        state.explanation_validations = validations
        with st.spinner("Ranking…"):
            state = run_stage_7_rank(state, k=st.session_state["k"])
        st.session_state["pipeline"] = state
        st.success("Ranking complete. Move to the **Results** tab.")


# ---------------------------------------------------------------------------
# Tab 3 — Results & Bias Checkpoint
# ---------------------------------------------------------------------------

def render_results_tab() -> None:
    st.header("Recommendations & Bias Check")
    state: PipelineState = st.session_state["pipeline"]

    if state.ranked is None:
        st.info("Complete the **Review** tab first.")
        return

    bias = state.bias_report
    if bias and not bias.passed:
        st.subheader("Bias / Fairness Report")
        _flags_box(bias.flags)

        col_g, col_a, col_m = st.columns(3)
        with col_g:
            st.caption("Genre distribution")
            st.bar_chart(bias.genre_counts)
        with col_a:
            st.caption("Artist distribution")
            st.bar_chart(bias.artist_counts)
        with col_m:
            st.caption("Mood distribution")
            st.bar_chart(bias.mood_counts)

        apply_diversity = st.checkbox("Apply diversity reranking", value=True)
        if st.button("Finalise Results", type="primary"):
            state = run_stage_8_finalize(
                state, k=st.session_state["k"], apply_diversity=apply_diversity
            )
            st.session_state["pipeline"] = state
    else:
        if bias:
            st.success("No bias issues detected.")
        if state.final_recommendations is None:
            if st.button("Accept & Finalise", type="primary"):
                state = run_stage_8_finalize(state, k=st.session_state["k"], apply_diversity=False)
                st.session_state["pipeline"] = state

    if state.final_recommendations is None:
        return

    st.subheader(f"Top-{st.session_state['k']} Recommendations")
    for i, (song, score, explanation) in enumerate(state.final_recommendations, 1):
        _song_card(song, score, explanation, i)

    st.info("Rate your recommendations in the **Feedback** tab.")


# ---------------------------------------------------------------------------
# Tab 4 — Feedback
# ---------------------------------------------------------------------------

def render_feedback_tab() -> None:
    st.header("Your Feedback")
    state: PipelineState = st.session_state["pipeline"]

    if state.final_recommendations is None:
        st.info("Complete the **Results** tab first.")
        return

    st.markdown("Help us improve by rating each recommendation.")

    song_ratings: dict[str, int] = {}
    exp_helpfulness: dict[str, int] = {}

    for song, score, explanation in state.final_recommendations:
        sid = str(song.get("id"))
        with st.container(border=True):
            st.markdown(f"**{song.get('title')}** — *{song.get('artist')}*")
            st.caption(explanation)
            c1, c2 = st.columns(2)
            liked = c1.radio(
                "Did you like this?", ["👍 Yes", "👎 No"],
                key=f"like_{sid}", horizontal=True
            )
            helpful = c2.radio(
                "Was the explanation helpful?", ["👍 Yes", "👎 No"],
                key=f"help_{sid}", horizontal=True
            )
            song_ratings[sid] = 1 if "Yes" in liked else 0
            exp_helpfulness[sid] = 1 if "Yes" in helpful else 0

    overall = st.select_slider(
        "Overall rating", options=[1, 2, 3, 4, 5], value=3
    )
    free_text = st.text_area("Any comments?", height=80)

    if st.button("Submit Feedback", type="primary"):
        recs_meta = [
            {
                "id": s.get("id"),
                "title": s.get("title"),
                "artist": s.get("artist"),
                "composite_score": sc,
            }
            for s, sc, _ in state.final_recommendations
        ]
        diversity_applied = (
            state.bias_report is not None and not state.bias_report.passed
        )
        record = FeedbackRecord(
            session_id=state.session_id,
            timestamp=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            user_prefs=state.input_validation.corrected_input if state.input_validation else {},
            recommendations=recs_meta,
            song_ratings=song_ratings,
            explanation_helpfulness=exp_helpfulness,
            overall_rating=overall,
            free_text=free_text,
            diversity_applied=diversity_applied,
        )
        save_feedback(record)
        st.success("Thank you! Feedback saved.")


# ---------------------------------------------------------------------------
# Tab 5 — Analysis
# ---------------------------------------------------------------------------

def render_analysis_tab() -> None:
    st.header("Performance Analysis")
    records = load_feedback()

    if not records:
        st.info("No feedback collected yet. Complete a recommendation session first.")
        return

    summary = compute_feedback_summary(records)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sessions", summary["total_sessions"])
    col2.metric(
        "Mean Overall Rating",
        f"{summary['mean_overall_rating']}/5" if summary["mean_overall_rating"] else "—",
    )
    col3.metric(
        "Explanation Helpfulness",
        f"{summary['explanation_helpfulness_rate']:.0%}"
        if summary["explanation_helpfulness_rate"] is not None
        else "—",
    )

    if summary["per_genre_like_rate"]:
        st.subheader("Like Rate by Genre")
        st.bar_chart(summary["per_genre_like_rate"])

    st.subheader("All Feedback Records")
    rows = [
        {
            "Session": r.session_id[:8],
            "Genre": r.user_prefs.get("genre"),
            "Mood": r.user_prefs.get("mood"),
            "Rating": r.overall_rating,
            "Diversity Applied": r.diversity_applied,
            "Timestamp": r.timestamp[:19],
        }
        for r in records
    ]
    st.dataframe(rows, use_container_width=True)

    import json
    raw_json = json.dumps(
        [__import__("dataclasses").asdict(r) for r in records], indent=2
    )
    st.download_button(
        "Export for Regression Testing",
        data=raw_json,
        file_name="feedback_regression_dataset.json",
        mime="application/json",
    )


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar() -> None:
    with st.sidebar:
        st.title("🎵 Settings")
        st.session_state["k"] = st.slider("Top-k results", 3, 10, st.session_state["k"])
        st.session_state["style"] = st.selectbox(
            "Recommendation style",
            ["genre-first", "mood-first", "energy-focused"],
            index=["genre-first", "mood-first", "energy-focused"].index(
                st.session_state["style"]
            ),
        )
        st.divider()
        st.subheader("AI Generation")
        ai_enabled = st.toggle(
            "Enable AI explanations",
            value=st.session_state["ai_enabled"],
            help="When off, template-based explanations are used — no API calls made.",
        )
        st.session_state["ai_enabled"] = ai_enabled
        if not ai_enabled:
            st.caption("AI off — boilerplate explanations will be used.")

        st.divider()

        # ── Pipeline progress bar ────────────────────────────────────────────
        state = st.session_state["pipeline"]
        stages = [
            ("Input validated",        state.input_validation is not None),
            ("Tracks fetched",         state.candidates is not None),
            ("External data fetched",  state.external_data is not None),
            ("Metadata augmented",     state.augmented_songs is not None),
            ("Explanations generated", state.explanations is not None),
            ("Explanations validated", state.explanation_validations is not None),
            ("Ranked",                 state.ranked is not None),
            ("Finalised",              state.final_recommendations is not None),
        ]
        st.subheader("Pipeline Progress")
        stages_done = sum(1 for _, done in stages if done)
        st.progress(stages_done / len(stages))
        for label, done in stages:
            color = "#a855f7" if done else "#4b5563"
            st.markdown(
                f"<span style='color:{color}'>{'●' if done else '○'} {label}</span>",
                unsafe_allow_html=True,
            )

        st.divider()
        if st.button("Start Over", type="secondary"):
            reset_pipeline()
            st.rerun()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="Music Matcher+",
        page_icon="🎵",
        layout="wide",
    )
    st.markdown(_THEME_CSS, unsafe_allow_html=True)

    init_session()
    render_sidebar()

    st.title("🎵 Music Matcher+")
    st.caption("Human-in-the-loop recommendation pipeline · powered by Google Gemini & Deezer")

    tabs = st.tabs(["Preferences", "Review", "Results", "Feedback", "Analysis"])

    with tabs[0]:
        render_preferences_tab()
    with tabs[1]:
        render_review_tab()
    with tabs[2]:
        render_results_tab()
    with tabs[3]:
        render_feedback_tab()
    with tabs[4]:
        render_analysis_tab()


if __name__ == "__main__":
    main()
