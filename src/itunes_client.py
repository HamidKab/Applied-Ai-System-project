"""
iTunes Search API client for genre detection.
Used by the Preferences tab to auto-detect genre from a user-supplied song/artist query.
No authentication required — the iTunes Search API is free and public.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

try:
    import requests
except ImportError as e:
    raise ImportError("Install 'requests': pip install requests") from e

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
_TIMEOUT = 5  # seconds

# ---------------------------------------------------------------------------
# Signal-based genre scoring
# ---------------------------------------------------------------------------
# Each internal genre has a list of (keyword, weight) pairs.
# map_itunes_genre() checks how many keywords appear in the raw iTunes genre
# string, sums their weights, and returns the highest-scoring internal genre.
#
# Why this beats a flat dictionary:
#   "alternative hip-hop"  → hiphop scores 4.0 (hip-hop hit), rock scores 1.5 (alternative hit)  → hiphop ✓
#   "alternative rock"     → rock scores 2.0+1.5=3.5, hiphop scores 0                           → rock  ✓
#   "indie rock"           → indie pop scores 2.5+2.0=4.5, rock scores 2.0+2.0=4.0             → indie pop ✓
#   "lo-fi hip-hop"        → lofi scores 5.0 (exact phrase), hiphop scores 4.0 (hip-hop hit)   → lofi  ✓
#
# Weights are intentionally asymmetric:
#   - Genre-defining compound phrases (e.g. "hip-hop", "heavy metal") get high weight (4–5)
#   - Ambiguous single words (e.g. "alternative", "rock", "dance") get low weight (1.5–2.0)
#     so they don't hijack results when a stronger signal is also present.

_GENRE_SIGNALS: dict[str, list[tuple[str, float]]] = {
    "hiphop": [
        ("hip-hop/rap",         5.0),   # iTunes' canonical label
        ("hip-hop",             4.0),
        ("hip hop",             4.0),
        ("rap",                 4.0),
        ("trap",                3.5),
        ("grime",               3.5),
        ("drill",               3.5),
        ("urban contemporary",  3.0),
    ],
    "rnb": [
        ("rhythm and blues",    5.0),
        ("contemporary r&b",    5.0),
        ("neo soul",            4.5),
        ("r&b/soul",            4.5),
        ("r&b",                 4.0),
        ("soul",                3.0),
        ("funk",                2.5),
    ],
    "pop": [
        ("dance pop",           4.5),
        ("electropop",          4.5),
        ("k-pop",               4.5),
        ("teen pop",            4.5),
        ("pop/rock",            3.0),
        ("pop",                 2.0),   # generic — low so it doesn't override tighter fits
    ],
    "synthwave": [
        ("synthwave",           5.0),
        ("retrowave",           5.0),
        ("synth-pop",           4.5),
        ("chillwave",           4.0),
        ("darksynth",           4.5),
        ("vaporwave",           4.0),
    ],
    "rock": [
        ("classic rock",        4.0),
        ("garage rock",         4.0),
        ("folk rock",           3.5),
        ("punk rock",           3.5),
        ("post-rock",           4.0),
        ("grunge",              4.5),
        ("punk",                3.0),
        ("rock",                2.0),       # generic
        ("alternative",         1.5),       # intentionally low — also appears in alt hip-hop
    ],
    "metal": [
        ("heavy metal",         5.0),
        ("death metal",         5.0),
        ("black metal",         5.0),
        ("thrash metal",        5.0),
        ("nu-metal",            5.0),
        ("metalcore",           5.0),
        ("hard rock",           3.5),
        ("metal",               3.5),
    ],
    "edm": [
        ("drum and bass",       5.0),
        ("dubstep",             5.0),
        ("techno",              5.0),
        ("trance",              5.0),
        ("electronica",         4.0),
        ("house",               4.0),
        ("edm",                 5.0),
        ("electronic",          3.0),
        ("dance",               1.5),       # low — "dance pop" should go to pop
    ],
    "jazz": [
        ("jazz fusion",         5.0),
        ("smooth jazz",         5.0),
        ("contemporary jazz",   5.0),
        ("big band",            4.5),
        ("bebop",               4.5),
        ("vocal jazz",          4.5),
        ("jazz",                3.5),
        ("swing",               3.0),
        ("blues",               2.0),
    ],
    "classical": [
        ("contemporary classical", 5.0),
        ("chamber music",       5.0),
        ("orchestral",          4.5),
        ("opera",               4.5),
        ("symphony",            4.0),
        ("classical",           3.5),
    ],
    "ambient": [
        ("ambient",             5.0),
        ("new age",             4.5),
        ("drone",               4.0),
        ("soundscape",          3.5),
    ],
    "lofi": [
        ("lo-fi hip-hop",       5.0),   # most specific — takes priority over generic hip-hop
        ("chillhop",            5.0),
        ("lo-fi",               4.0),
        ("lofi",                4.0),
    ],
    "indie pop": [
        ("indie pop",           5.0),
        ("dream pop",           5.0),
        ("chamber pop",         5.0),
        ("indie folk",          4.5),
        ("folktronica",         4.0),
        ("indie rock",          2.5),   # also accrues rock signal — net winner depends on context
        ("indie",               2.0),
    ],
    "reggae": [
        ("reggaeton",           5.0),
        ("dancehall",           5.0),
        ("reggae",              5.0),
        ("ska",                 4.0),
        ("dub",                 3.5),
    ],
    "country": [
        ("country & western",   5.0),
        ("bluegrass",           5.0),
        ("americana",           4.5),
        ("singer/songwriter",   3.5),
        ("singer-songwriter",   3.5),
        ("country",             3.5),
        ("folk",                2.0),   # low — "indie folk" should go to indie pop
    ],
}

# Tie-break priority (used when two genres share the exact same top score).
# More specific / niche genres rank above catch-all ones.
_GENRE_PRIORITY: list[str] = [
    "lofi", "synthwave", "metal", "reggae", "classical", "jazz",
    "ambient", "hiphop", "rnb", "edm", "country", "indie pop", "rock", "pop",
]


@dataclass
class ItunesTrackInfo:
    track_name: str
    artist_name: str
    primary_genre: str        # raw iTunes genre string (e.g. "Hip-Hop/Rap")
    mapped_genre: Optional[str]  # resolved internal genre key (e.g. "hiphop"), or None


def map_itunes_genre(itunes_genre: str) -> Optional[str]:
    """
    Score-based genre mapping.

    Sums keyword signal weights for each internal genre, then returns the
    highest-scoring genre.  Tie-breaks via _GENRE_PRIORITY.
    Returns None if no keyword matched anything.
    """
    normalised = itunes_genre.lower().strip()
    scores: dict[str, float] = {}

    for genre, signals in _GENRE_SIGNALS.items():
        total = sum(weight for kw, weight in signals if kw in normalised)
        if total > 0:
            scores[genre] = total

    if not scores:
        return None

    top_score = max(scores.values())
    # Collect all genres tied at the top score
    tied = [g for g, s in scores.items() if s == top_score]
    if len(tied) == 1:
        return tied[0]

    # Break ties using priority order
    for g in _GENRE_PRIORITY:
        if g in tied:
            return g

    return tied[0]


def search_itunes(query: str, limit: int = 5) -> list:
    """
    Call the iTunes Search API and return the results list.
    Returns [] on any network/parse error (never raises).
    """
    try:
        resp = requests.get(
            ITUNES_SEARCH_URL,
            params={"term": query, "media": "music", "entity": "song", "limit": limit},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception:
        return []


def _relevant_words(text: str) -> set[str]:
    """Return lowercase words of 4+ chars from text — used for relevance checks."""
    return {w.lower() for w in text.split() if len(w) >= 4}


def detect_genre_from_query(query: str) -> Optional[ItunesTrackInfo]:
    """
    Search iTunes for query and return genre info from the first *relevant* result.

    A result is considered relevant if at least one meaningful word (4+ chars)
    from the query appears in the returned track name or artist name.  This
    prevents accidentally accepting a completely unrelated song that iTunes
    surfaces because of coincidental word overlap (e.g. querying an obscure
    UK artist and getting back a Zach Bryan Country track).

    Returns None when no relevant result is found — callers fall back to
    manual genre selection rather than returning a confidently wrong answer.
    """
    results = search_itunes(query, limit=5)
    if not results:
        return None

    query_words = _relevant_words(query)
    best = None
    for result in results:
        result_text = (
            f"{result.get('trackName', '')} {result.get('artistName', '')}"
        ).lower()
        if query_words and any(word in result_text for word in query_words):
            best = result
            break

    if best is None:
        return None

    raw_genre = best.get("primaryGenreName", "")
    if not raw_genre:
        return None

    return ItunesTrackInfo(
        track_name=best.get("trackName", ""),
        artist_name=best.get("artistName", ""),
        primary_genre=raw_genre,
        mapped_genre=map_itunes_genre(raw_genre),
    )


def search_and_detect(artist_or_song: str) -> Optional[ItunesTrackInfo]:
    """
    Convenience entry point used by app.py.
    Accepts free-text like "chali 2na by Earl Sweatshirt" or just an artist name.

    Search strategy (stops at first hit):
    1. Full query as-is
    2. If query contains " by ", try the part before "by" (song/artist name)
    3. Try the first token(s) of the query (artist-only fallback)
    """
    query = artist_or_song.strip()

    # 1. Try the full query
    result = detect_genre_from_query(query)
    if result:
        return result

    # 2. If "by" separator present, try artist name first (after "by"), then song title
    lower = query.lower()
    if " by " in lower:
        idx = lower.index(" by ")
        before = query[:idx].strip()   # song/artist name
        after = query[idx + 4:].strip()  # artist name (more reliable)
        for sub in (after, before):
            if sub:
                result = detect_genre_from_query(sub)
                if result:
                    return result

    # 3. Fallback: first 2–3 words (handles "chali 2na earl sweatshirt" → "chali 2na")
    words = query.split()
    if len(words) > 2:
        result = detect_genre_from_query(" ".join(words[:2]))
        if result:
            return result
    if len(words) > 1:
        result = detect_genre_from_query(words[0])
        if result:
            return result

    return None
