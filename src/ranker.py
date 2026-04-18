from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from external_data import ExternalSongData
from explanation_validator import ExplanationValidationResult


@dataclass
class BiasReport:
    genre_counts: Dict[str, int] = field(default_factory=dict)
    artist_counts: Dict[str, int] = field(default_factory=dict)
    mood_counts: Dict[str, int] = field(default_factory=dict)
    flags: List[str] = field(default_factory=list)
    passed: bool = True


def composite_score(
    base_score: float,
    confidence_score: float,
    trending_score: float,
    base_weight: float = 0.60,
    confidence_weight: float = 0.25,
    trending_weight: float = 0.15,
) -> float:
    return (
        base_score * base_weight
        + confidence_score * confidence_weight
        + trending_score * trending_weight
    )


def rank_candidates(
    candidates: List[Tuple[Dict, float, str]],
    external_map: Dict[int, ExternalSongData],
    validations: List[ExplanationValidationResult],
) -> List[Tuple[Dict, float, str]]:
    """
    Applies composite_score to each candidate and returns a sorted list.
    Output tuple: (augmented_song, composite_score, validated_explanation).
    """
    val_map: Dict[int, ExplanationValidationResult] = {
        v.song_id: v for v in validations
    }

    scored: List[Tuple[Dict, float, str]] = []
    for song, base, _ in candidates:
        song_id = song.get("id", -1)
        ext = external_map.get(song_id)
        trending = ext.trending_score if ext else 0.5

        val = val_map.get(song_id)
        confidence = val.confidence_score if val else 1.0
        explanation = val.explanation if val else ""

        final = composite_score(base, confidence, trending)
        scored.append((song, round(final, 4), explanation))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def check_bias(ranked: List[Tuple[Dict, float, str]], k: int) -> BiasReport:
    """
    Inspects the top-k songs for genre concentration, artist repetition,
    and mood homogeneity. Returns a BiasReport with flags.
    """
    top = ranked[:k]
    genre_counts: Dict[str, int] = {}
    artist_counts: Dict[str, int] = {}
    mood_counts: Dict[str, int] = {}

    for song, _, _ in top:
        g = song.get("genre", "unknown")
        a = song.get("artist", "unknown")
        m = song.get("mood", "unknown")
        genre_counts[g] = genre_counts.get(g, 0) + 1
        artist_counts[a] = artist_counts.get(a, 0) + 1
        mood_counts[m] = mood_counts.get(m, 0) + 1

    flags: List[str] = []
    threshold = 0.60

    for genre, count in genre_counts.items():
        if k > 0 and count / k > threshold:
            flags.append(
                f"Genre '{genre}' appears in {count}/{k} recommendations ({count/k:.0%})."
            )

    for artist, count in artist_counts.items():
        if count > 2:
            flags.append(
                f"Artist '{artist}' appears {count} times in top-{k}."
            )

    for mood, count in mood_counts.items():
        if k > 0 and count / k > threshold:
            flags.append(
                f"Mood '{mood}' appears in {count}/{k} recommendations ({count/k:.0%})."
            )

    return BiasReport(
        genre_counts=genre_counts,
        artist_counts=artist_counts,
        mood_counts=mood_counts,
        flags=flags,
        passed=len(flags) == 0,
    )


def apply_diversity_reranking(
    ranked: List[Tuple[Dict, float, str]],
    k: int,
    max_same_genre: int = 2,
    max_same_artist: int = 1,
) -> List[Tuple[Dict, float, str]]:
    """
    Greedy selection that enforces diversity constraints.
    Iterates the score-sorted list and picks songs that don't exceed
    max_same_genre or max_same_artist limits until k songs are selected.
    Falls back to score-order if not enough diverse songs exist.
    """
    selected: List[Tuple[Dict, float, str]] = []
    genre_seen: Dict[str, int] = {}
    artist_seen: Dict[str, int] = {}
    remainder: List[Tuple[Dict, float, str]] = []

    for item in ranked:
        song = item[0]
        g = song.get("genre", "unknown")
        a = song.get("artist", "unknown")

        if (
            genre_seen.get(g, 0) < max_same_genre
            and artist_seen.get(a, 0) < max_same_artist
        ):
            selected.append(item)
            genre_seen[g] = genre_seen.get(g, 0) + 1
            artist_seen[a] = artist_seen.get(a, 0) + 1
        else:
            remainder.append(item)

        if len(selected) == k:
            break

    # Fill remaining slots with best-scoring leftovers if needed
    if len(selected) < k:
        for item in remainder:
            if len(selected) >= k:
                break
            selected.append(item)

    return selected[:k]
