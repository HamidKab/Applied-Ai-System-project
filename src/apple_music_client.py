"""
Apple Music Catalog API client for genre detection.

Requires a developer token in the APPLE_MUSIC_TOKEN environment variable.
Without it every call returns None and the caller falls back to iTunes Search.

How to generate a token
-----------------------
1. Enrol in the Apple Developer Program (developer.apple.com)
2. In your portal create a MusicKit identifier and download the .p8 private key
3. Run the snippet below (needs PyJWT + cryptography: pip install PyJWT cryptography):

       import jwt, time, pathlib
       private_key = pathlib.Path("AuthKey_XXXXXXXXXX.p8").read_text()
       token = jwt.encode(
           {"iss": "<TEAM_ID>", "iat": int(time.time()), "exp": int(time.time()) + 15777000},
           private_key, algorithm="ES256",
           headers={"kid": "<KEY_ID>"},
       )
       print(token)

4. Add the output to your .env file:
       APPLE_MUSIC_TOKEN=<token>

The token is valid for up to 6 months (15,777,000 seconds).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

try:
    import requests
except ImportError as e:
    raise ImportError("Install 'requests': pip install requests") from e

from itunes_client import map_itunes_genre

_CATALOG_SEARCH = "https://api.music.apple.com/v1/catalog/{storefront}/search"
_TIMEOUT = 5  # seconds


@dataclass
class AppleMusicGenreResult:
    track_name: str
    artist_name: str
    raw_genres: list[str] = field(default_factory=list)  # all Apple Music genres for this track
    primary_genre: str = ""         # first non-"Music" entry in raw_genres
    mapped_genre: Optional[str] = None  # resolved internal genre key


def _developer_token() -> Optional[str]:
    return os.environ.get("APPLE_MUSIC_TOKEN")


def search_catalog(
    query: str,
    storefront: str = "us",
    limit: int = 5,
) -> list[dict]:
    """
    Search the Apple Music catalog.  Returns a list of song attribute dicts.
    Returns [] when:
      - APPLE_MUSIC_TOKEN is not set
      - the network request fails
      - the API returns no results
    Never raises.
    """
    token = _developer_token()
    if not token:
        return []
    try:
        url = _CATALOG_SEARCH.format(storefront=storefront)
        resp = requests.get(
            url,
            params={"term": query, "types": "songs", "limit": limit},
            headers={"Authorization": f"Bearer {token}"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        songs = resp.json().get("results", {}).get("songs", {}).get("data", [])
        return [s.get("attributes", {}) for s in songs]
    except Exception:
        return []


def detect_genre(
    query: str,
    relevant_words: Optional[set] = None,
) -> Optional[AppleMusicGenreResult]:
    """
    Search Apple Music for *query* and return genre info from the best matching result.

    relevant_words — when provided, a candidate result is only accepted if at least
    one word from this set appears in its track name or artist name.  Pass the 4+-char
    words extracted from the original user query to avoid accepting unrelated results.

    Returns None when:
      - APPLE_MUSIC_TOKEN is not configured
      - no results are returned
      - no result passes the relevance check
    """
    songs = search_catalog(query)
    if not songs:
        return None

    best: Optional[dict] = None
    for attrs in songs:
        if relevant_words:
            result_text = (
                f"{attrs.get('name', '')} {attrs.get('artistName', '')}"
            ).lower()
            if not any(w in result_text for w in relevant_words):
                continue
        best = attrs
        break

    if best is None:
        return None

    # Apple Music always appends the catch-all "Music" genre — strip it
    raw_genres = [g for g in best.get("genreNames", []) if g.lower() != "music"]
    if not raw_genres:
        return None

    primary = raw_genres[0]
    return AppleMusicGenreResult(
        track_name=best.get("name", ""),
        artist_name=best.get("artistName", ""),
        raw_genres=raw_genres,
        primary_genre=primary,
        mapped_genre=map_itunes_genre(primary),
    )
