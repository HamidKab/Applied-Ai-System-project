"""
Multi-source genre detection pipeline.

Detection order per source:
  1. MusicBrainz  — artist community tags, highest accuracy (weight 3)
  2. Deezer       — album genre from the track's album (weight 2)
  3. iTunes       — song search with relevance filter (weight 1)

All three sources run concurrently (logically), their votes are tallied,
and the genre with the most weighted votes wins.  Ties break on source
priority: MusicBrainz > Deezer > iTunes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from deezer_client import search_free_text, get_album_genres, DeezerTrackData
from musicbrainz_client import get_artist_genres
from itunes_client import search_and_detect, map_itunes_genre


# Source weights — higher = more trusted
_WEIGHTS = {"MusicBrainz": 3, "Deezer": 2, "iTunes": 1}


@dataclass
class GenreDetectionResult:
    mapped_genre: str
    raw_genre: str           # human-readable genre name from the winning source
    sources: list[str]       # e.g. ["MusicBrainz", "Deezer"]
    confidence: str          # "high" (≥2 sources agree) | "medium" (1 source)
    deezer_artist: Optional[str] = None  # canonical artist resolved by Deezer


def _extract_artist(query: str) -> str:
    """Best-effort artist extraction: returns text after 'by ' if present."""
    lower = query.lower()
    if " by " in lower:
        return query[lower.index(" by ") + 4:].strip()
    return query.strip()


def detect(query: str) -> Optional[GenreDetectionResult]:
    """
    Run all three sources against *query* and return the consensus genre.

    Steps:
    1. Deezer free-text search → canonical artist name + album_id
    2. MusicBrainz artist search using canonical artist name
    3. Deezer album genres using album_id from step 1
    4. iTunes Search with relevance filter
    5. Vote: weighted tally → return winner with confidence label
    """
    # ── Step 1: Deezer normalisation ────────────────────────────────────────
    deezer_hit: Optional[DeezerTrackData] = search_free_text(query)
    artist_name = deezer_hit.artist if deezer_hit else _extract_artist(query)

    # votes[mapped_genre] = [(source_name, raw_genre_label), ...]
    votes: dict[str, list[tuple[str, str]]] = {}

    def _cast(genre_name: str, source: str) -> bool:
        """Map genre_name and record a vote. Returns True if mapped."""
        mapped = map_itunes_genre(genre_name)
        if mapped:
            votes.setdefault(mapped, []).append((source, genre_name))
            return True
        return False

    # ── Step 2: MusicBrainz ─────────────────────────────────────────────────
    for tag in get_artist_genres(artist_name):
        if _cast(tag, "MusicBrainz"):
            break  # only the top mappable MB tag votes

    # ── Step 3: Deezer album genres ─────────────────────────────────────────
    if deezer_hit and deezer_hit.album_id:
        for genre_name in get_album_genres(deezer_hit.album_id):
            if _cast(genre_name, "Deezer"):
                break  # only the first mappable Deezer genre votes

    # ── Step 4: iTunes Search ───────────────────────────────────────────────
    itunes = search_and_detect(query)
    if itunes and itunes.mapped_genre:
        votes.setdefault(itunes.mapped_genre, []).append(
            ("iTunes", itunes.primary_genre)
        )

    if not votes:
        return None

    # ── Step 5: Weighted vote tally ─────────────────────────────────────────
    def _score(entry: tuple[str, list]) -> tuple[int, int]:
        genre, source_list = entry
        total_weight = sum(_WEIGHTS.get(src, 1) for src, _ in source_list)
        priority = max(_WEIGHTS.get(src, 0) for src, _ in source_list)
        return (total_weight, priority)

    winner_genre, winner_sources = max(votes.items(), key=_score)

    # Build human-readable labels
    source_names = list(dict.fromkeys(src for src, _ in winner_sources))  # deduped
    raw_label = winner_sources[0][1]  # raw genre name from the top source

    return GenreDetectionResult(
        mapped_genre=winner_genre,
        raw_genre=raw_label,
        sources=source_names,
        confidence="high" if len(source_names) >= 2 else "medium",
        deezer_artist=deezer_hit.artist if deezer_hit else None,
    )
