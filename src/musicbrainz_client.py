"""
MusicBrainz API client for artist genre detection.
Free, no auth required. Rate limit: 1 request/second — acceptable for
our use case (one lookup per user query submission).
"""
from __future__ import annotations

from typing import Optional

try:
    import requests
except ImportError as e:
    raise ImportError("Install 'requests': pip install requests") from e

_ARTIST_SEARCH = "https://musicbrainz.org/ws/2/artist/"
_TIMEOUT = 5
# MusicBrainz requires a descriptive User-Agent or requests may be rejected
_HEADERS = {"User-Agent": "MusicMatcher+/1.0 (music-recommendation-app)"}


def get_artist_genres(artist_name: str) -> list[str]:
    """
    Search MusicBrainz for an artist and return their genre/tag names,
    sorted by community vote count (most agreed-upon first).

    Applies a relevance check: the returned artist's name must share at
    least one word (3+ chars) with the query so we don't accept a
    completely unrelated artist that happens to rank #1.

    Returns [] on any failure or when no genres/tags are found.
    """
    try:
        resp = requests.get(
            _ARTIST_SEARCH,
            params={"query": artist_name, "limit": 5, "fmt": "json"},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        artists = resp.json().get("artists", [])
        if not artists:
            return []

        input_words = {w.lower() for w in artist_name.split() if len(w) >= 3}
        best = None
        for artist in artists:
            mb_name = (
                artist.get("name", "") + " " + artist.get("sort-name", "")
            ).lower()
            if input_words and any(w in mb_name for w in input_words):
                best = artist
                break

        if best is None:
            best = artists[0]

        # Prefer curated genres over free tags
        genres = sorted(
            best.get("genres", []), key=lambda x: x.get("count", 0), reverse=True
        )
        if genres:
            return [g["name"] for g in genres]

        # Fall back to community tags (also useful, e.g. "hip-hop", "grime")
        tags = sorted(
            best.get("tags", []), key=lambda x: x.get("count", 0), reverse=True
        )
        return [t["name"] for t in tags[:8]]

    except Exception:
        return []


def detect_genre(artist_name: str) -> Optional[str]:
    """
    Return the internal genre key for artist_name using MusicBrainz tags.
    Tries each tag in vote-count order until one maps to an internal genre.
    Returns None if no mappable genre is found.
    """
    from itunes_client import map_itunes_genre

    for tag in get_artist_genres(artist_name):
        mapped = map_itunes_genre(tag)
        if mapped:
            return mapped
    return None
