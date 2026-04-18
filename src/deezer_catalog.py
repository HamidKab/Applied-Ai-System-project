"""
Live music catalog sourced from Deezer Search API.
Replaces the static songs.csv with real tracks that have cover art and preview URLs.
"""
from __future__ import annotations

try:
    import requests
except ImportError as e:
    raise ImportError("Install 'requests': pip install requests") from e

DEEZER_SEARCH_URL = "https://api.deezer.com/search"
_TIMEOUT = 6

GENRE_DEFAULTS: dict[str, dict] = {
    "hiphop":    {"mood": "confident",  "energy": 0.78, "acousticness": 0.10},
    "pop":       {"mood": "happy",      "energy": 0.72, "acousticness": 0.20},
    "rock":      {"mood": "intense",    "energy": 0.82, "acousticness": 0.12},
    "rnb":       {"mood": "romantic",   "energy": 0.60, "acousticness": 0.25},
    "edm":       {"mood": "excited",    "energy": 0.88, "acousticness": 0.05},
    "jazz":      {"mood": "relaxed",    "energy": 0.45, "acousticness": 0.55},
    "classical": {"mood": "calm",       "energy": 0.38, "acousticness": 0.80},
    "metal":     {"mood": "aggressive", "energy": 0.92, "acousticness": 0.06},
    "lofi":      {"mood": "chill",      "energy": 0.35, "acousticness": 0.70},
    "ambient":   {"mood": "calm",       "energy": 0.30, "acousticness": 0.75},
    "synthwave": {"mood": "focused",    "energy": 0.70, "acousticness": 0.08},
    "indie pop": {"mood": "hopeful",    "energy": 0.62, "acousticness": 0.35},
    "indiepop":  {"mood": "hopeful",    "energy": 0.62, "acousticness": 0.35},
    "reggae":    {"mood": "warm",       "energy": 0.55, "acousticness": 0.40},
    "country":   {"mood": "warm",       "energy": 0.58, "acousticness": 0.50},
}

GENRE_SEARCH_TERMS: dict[str, str] = {
    "hiphop":    "hip hop rap",
    "pop":       "pop hits",
    "rock":      "rock",
    "rnb":       "r&b soul",
    "edm":       "electronic dance",
    "jazz":      "jazz",
    "classical": "classical music",
    "metal":     "metal",
    "lofi":      "lofi chill",
    "ambient":   "ambient",
    "synthwave": "synthwave",
    "indie pop": "indie pop",
    "indiepop":  "indie pop",
    "reggae":    "reggae",
    "country":   "country",
}


def _track_to_dict(t: dict, genre_key: str) -> dict:
    """Convert a raw Deezer track dict to the recommender-compatible schema."""
    defaults = GENRE_DEFAULTS.get(genre_key, {"mood": "happy", "energy": 0.65, "acousticness": 0.30})
    album = t.get("album", {})
    return {
        "id":            t.get("id"),
        "title":         t.get("title", ""),
        "artist":        t.get("artist", {}).get("name", ""),
        "genre":         genre_key,
        "mood":          defaults["mood"],
        "energy":        defaults["energy"],
        "tempo_bpm":     120.0,
        "valence":       0.60,
        "danceability":  0.65,
        "acousticness":  defaults["acousticness"],
        "cover_art_url": album.get("cover_medium"),
        "preview_url":   t.get("preview") or None,
        "deezer_url":    t.get("link") or None,
    }


def fetch_tracks_for_genre(genre_key: str, k: int = 20) -> list[dict]:
    """
    Search Deezer by genre keyword and return up to *k* track dicts.
    Returns [] on any failure. Never raises.
    """
    search_term = GENRE_SEARCH_TERMS.get(genre_key, genre_key)
    try:
        resp = requests.get(
            DEEZER_SEARCH_URL,
            params={"q": search_term, "limit": k},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return [_track_to_dict(t, genre_key) for t in resp.json().get("data", [])]
    except Exception:
        return []


def fetch_similar_tracks(query: str, genre_key: str, k: int = 20) -> list[dict]:
    """
    Find tracks similar to *query* using Deezer's artist graph:
      1. Search for the artist → get artist_id
      2. Fetch the artist's own top tracks
      3. Fetch related artists' top tracks

    Falls back to fetch_tracks_for_genre() if no artist is found.
    Never raises.
    """
    tracks: list[dict] = []
    artist_id: int | None = None

    # Step 1: resolve artist_id from the query
    try:
        resp = requests.get(DEEZER_SEARCH_URL, params={"q": query, "limit": 3}, timeout=_TIMEOUT)
        for hit in resp.json().get("data", []):
            artist_id = hit.get("artist", {}).get("id")
            if artist_id:
                break
    except Exception:
        pass

    if not artist_id:
        return fetch_tracks_for_genre(genre_key, k)

    # Step 2: the artist's own top tracks
    try:
        resp = requests.get(
            f"https://api.deezer.com/artist/{artist_id}/top",
            params={"limit": k // 2},
            timeout=_TIMEOUT,
        )
        for t in resp.json().get("data", []):
            tracks.append(_track_to_dict(t, genre_key))
    except Exception:
        pass

    # Step 3: related artists' top tracks
    try:
        resp = requests.get(
            f"https://api.deezer.com/artist/{artist_id}/related",
            params={"limit": 6},
            timeout=_TIMEOUT,
        )
        for rel in resp.json().get("data", []):
            if len(tracks) >= k:
                break
            rel_id = rel.get("id")
            try:
                resp2 = requests.get(
                    f"https://api.deezer.com/artist/{rel_id}/top",
                    params={"limit": 3},
                    timeout=4,
                )
                for t in resp2.json().get("data", []):
                    tracks.append(_track_to_dict(t, genre_key))
            except Exception:
                continue
    except Exception:
        pass

    # Deduplicate by track ID (preserves order)
    seen: set = set()
    deduped = [t for t in tracks if not (t["id"] in seen or seen.add(t["id"]))]  # type: ignore[arg-type]

    # Fill with genre fallback if we got too few results
    if len(deduped) < k // 2:
        deduped += fetch_tracks_for_genre(genre_key, k - len(deduped))

    return deduped[:k]
