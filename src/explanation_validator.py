import re
from dataclasses import dataclass, field
from typing import Dict, List

from recommender import _normalize_label
from external_data import ExternalSongData
from validation import KNOWN_GENRES, KNOWN_MOODS


@dataclass
class ExplanationValidationResult:
    song_id: int
    explanation: str
    flags: List[str] = field(default_factory=list)
    confidence_score: float = 1.0
    approved: bool = True   # Human can override at the checkpoint
    rejected: bool = False  # Human explicitly excluded this song from results


def _check_artist_name(explanation: str, song: Dict) -> List[str]:
    """Flag if explanation's 'by <Name>' pattern names a different artist."""
    flags: List[str] = []
    correct_artist = _normalize_label(song.get("artist", ""))
    matches = re.findall(r"\bby\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)", explanation)
    for mentioned in matches:
        if _normalize_label(mentioned) != correct_artist:
            flags.append(
                f"Explanation mentions artist '{mentioned}' but song artist is '{song.get('artist')}'."
            )
    return flags


def _check_metadata_consistency(explanation: str, song: Dict) -> List[str]:
    """Flag if explanation references genre/mood labels that don't match the song."""
    flags: List[str] = []
    exp_lower = explanation.lower()
    song_genre = _normalize_label(song.get("genre", ""))
    song_mood = _normalize_label(song.get("mood", ""))

    wrong_genres = [g for g in KNOWN_GENRES if g in exp_lower and g != song_genre]
    if wrong_genres:
        flags.append(
            f"Explanation references genre(s) {wrong_genres} "
            f"but song genre is '{song.get('genre')}'."
        )

    wrong_moods = [m for m in KNOWN_MOODS if m in exp_lower and m != song_mood]
    if wrong_moods:
        flags.append(
            f"Explanation references mood(s) {wrong_moods} "
            f"but song mood is '{song.get('mood')}'."
        )
    return flags


def _check_external_data_grounding(
    explanation: str,
    external: ExternalSongData,
) -> List[str]:
    """
    Check whether the explanation contradicts the artist bio.
    Since the bio is short, we flag if any genre/mood word in the bio
    is directly contradicted in the explanation.
    """
    flags: List[str] = []
    if not external or not external.artist_bio:
        return flags

    bio_lower = external.artist_bio.lower()
    exp_lower = explanation.lower()

    bio_genres = [g for g in KNOWN_GENRES if g in bio_lower]
    for bg in bio_genres:
        if "not " + bg in exp_lower or "isn't " + bg in exp_lower:
            flags.append(
                f"Explanation contradicts the artist bio regarding genre '{bg}'."
            )
    return flags


def validate_explanation(
    explanation: str,
    song: Dict,
    external: ExternalSongData,
) -> ExplanationValidationResult:
    """
    Runs all three checks and returns an ExplanationValidationResult.
    confidence_score = 1.0 - (num_flags * 0.25), clamped to [0, 1].
    approved defaults to True; set to False by the human at the checkpoint
    when confidence_score < 0.75.
    """
    song_id = song.get("id", -1)
    flags: List[str] = []
    flags.extend(_check_artist_name(explanation, song))
    flags.extend(_check_metadata_consistency(explanation, song))
    flags.extend(_check_external_data_grounding(explanation, external))

    confidence = max(0.0, 1.0 - len(flags) * 0.25)
    needs_review = confidence < 0.75

    return ExplanationValidationResult(
        song_id=song_id,
        explanation=explanation,
        flags=flags,
        confidence_score=confidence,
        approved=not needs_review,
    )
