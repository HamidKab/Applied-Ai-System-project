"""
Deezer API client for fetching song cover art and 30-second preview URLs.
Used exclusively by the UI layer — does not affect the recommendation pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

try:
    import requests
except ImportError as e:
    raise ImportError("Install 'requests': pip install requests") from e

DEEZER_SEARCH_URL = "https://api.deezer.com/search"
_TIMEOUT = 5  # seconds


@dataclass
class DeezerTrackData:
    track_id: Optional[int]
    title: str
    artist: str
    cover_art_url: Optional[str]        # album.cover_medium (~500x500)
    preview_url: Optional[str]          # 30-second MP3 URL
    deezer_url: Optional[str]           # link to full track page on Deezer
    album_id: Optional[int] = None      # used to fetch album genres via get_album_genres()


def _track_to_data(track: dict, title_fallback: str = "", artist_fallback: str = "") -> DeezerTrackData:
    """Convert a raw Deezer track dict to DeezerTrackData."""
    album = track.get("album", {})
    return DeezerTrackData(
        track_id=track.get("id"),
        title=track.get("title", title_fallback),
        artist=track.get("artist", {}).get("name", artist_fallback),
        cover_art_url=album.get("cover_medium"),
        preview_url=track.get("preview") or None,
        deezer_url=track.get("link") or None,
        album_id=album.get("id"),
    )


def search_track(title: str, artist: str) -> Optional[DeezerTrackData]:
    """
    Search Deezer for a track by title + artist.
    Returns a DeezerTrackData on success, or None on any failure.
    Never raises — all exceptions are silently swallowed.
    """
    query = f"{title} {artist}"
    try:
        resp = requests.get(
            DEEZER_SEARCH_URL,
            params={"q": query, "limit": 1},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        tracks = resp.json().get("data", [])
        if not tracks:
            return None
        return _track_to_data(tracks[0], title, artist)
    except Exception:
        return None


def get_album_genres(album_id: int) -> list:
    """
    Fetch genre names for a Deezer album.
    Returns a list of genre name strings, e.g. ["Rap/Hip Hop", "Pop"].
    Returns [] on any failure.
    """
    try:
        resp = requests.get(
            f"https://api.deezer.com/album/{album_id}",
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return [g["name"] for g in data.get("genres", {}).get("data", [])]
    except Exception:
        return []


def get_cached_or_fetch(
    song_id: int,
    title: str,
    artist: str,
    cache: dict,
) -> Optional[DeezerTrackData]:
    """
    Return cached Deezer data for song_id, or fetch and cache it on miss.
    None is stored as an explicit sentinel so a failed lookup is not
    retried on every Streamlit rerun — check with `song_id not in cache`,
    not `not cache[song_id]`.
    """
    if song_id in cache:
        return cache[song_id]
    result = search_track(title, artist)
    cache[song_id] = result  # None is a valid "miss" sentinel
    return result


def search_free_text(query: str) -> Optional[DeezerTrackData]:
    """
    Search Deezer with a free-text query (e.g. "HOW TO KILL A MAN by Sideshow").
    Returns the first result whose title or artist shares a meaningful word (4+ chars)
    with the query, so unrelated results are not used to normalise the canonical name.
    Returns None if nothing relevant is found.
    """
    query_words = {w.lower() for w in query.split() if len(w) >= 4}
    try:
        resp = requests.get(
            DEEZER_SEARCH_URL,
            params={"q": query, "limit": 5},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        tracks = resp.json().get("data", [])
        for track in tracks:
            t_text = (
                f"{track.get('title', '')} "
                f"{track.get('artist', {}).get('name', '')}"
            ).lower()
            if not query_words or any(w in t_text for w in query_words):
                return _track_to_data(track)
        return None
    except Exception:
        return None


def fetch_batch_deezer(songs: list) -> dict:
    """
    Fetch Deezer metadata for a list of song dicts.
    Returns {song_id: DeezerTrackData}.  Songs with no Deezer match are absent.
    """
    result: dict = {}
    for song in songs:
        sid = song.get("id")
        data = search_track(song.get("title", ""), song.get("artist", ""))
        if data is not None:
            result[sid] = data
    return result
