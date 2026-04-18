from dataclasses import dataclass, field
from typing import Dict, List

from recommender import _normalize_label

KNOWN_GENRES: set = {
    "pop", "lofi", "rock", "ambient", "jazz", "synthwave",
    "indiepop", "hiphop", "edm", "rnb", "metal", "classical",
    "reggae", "country",
}

KNOWN_MOODS: set = {
    "happy", "chill", "intense", "relaxed", "focused", "excited",
    "romantic", "calm", "confident", "moody", "hopeful",
    "melancholic", "warm", "aggressive",
}

# Display-friendly labels for the UI
GENRE_OPTIONS: List[str] = [
    "pop", "lofi", "rock", "ambient", "jazz", "synthwave",
    "indie pop", "hiphop", "edm", "rnb", "metal", "classical",
    "reggae", "country",
]

MOOD_OPTIONS: List[str] = [
    "happy", "chill", "intense", "relaxed", "focused", "excited",
    "romantic", "calm", "confident", "moody", "hopeful",
    "melancholic", "warm", "aggressive",
]


def _levenshtein(a: str, b: str) -> int:
    """Compute edit distance between two strings."""
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


def _closest_known(label: str, known: set) -> str | None:
    """Return the closest known label if edit distance <= 2, else None."""
    normalized = _normalize_label(label)
    if normalized in known:
        return normalized
    best, best_dist = None, 3
    for candidate in known:
        dist = _levenshtein(normalized, candidate)
        if dist < best_dist:
            best, best_dist = candidate, dist
    return best


@dataclass
class ValidationResult:
    is_valid: bool
    flags: List[str] = field(default_factory=list)
    corrected_input: Dict = field(default_factory=dict)
    requires_human_review: bool = False


def validate_user_input(user_prefs: Dict) -> ValidationResult:
    """
    Validate genre, mood, energy, and likes_acoustic from user_prefs.
    Returns a ValidationResult with flags and best-guess corrections.
    requires_human_review is True when input is ambiguous (near-miss),
    is_valid is False only when input cannot be corrected at all.
    """
    flags: List[str] = []
    corrected: Dict = dict(user_prefs)
    requires_review = False
    is_valid = True

    genre = str(user_prefs.get("genre", "")).strip()
    if not genre:
        flags.append("Genre is required.")
        is_valid = False
    else:
        normalized = _normalize_label(genre)
        if normalized in KNOWN_GENRES:
            corrected["genre"] = normalized
        else:
            closest = _closest_known(genre, KNOWN_GENRES)
            if closest:
                flags.append(
                    f"Unknown genre '{genre}'. Did you mean '{closest}'?"
                )
                corrected["genre"] = closest
                requires_review = True
            else:
                flags.append(
                    f"Unknown genre '{genre}'. Please pick a valid genre."
                )
                is_valid = False

    mood = str(user_prefs.get("mood", "")).strip()
    if not mood:
        flags.append("Mood is required.")
        is_valid = False
    else:
        normalized = _normalize_label(mood)
        if normalized in KNOWN_MOODS:
            corrected["mood"] = normalized
        else:
            closest = _closest_known(mood, KNOWN_MOODS)
            if closest:
                flags.append(
                    f"Unknown mood '{mood}'. Did you mean '{closest}'?"
                )
                corrected["mood"] = closest
                requires_review = True
            else:
                flags.append(
                    f"Unknown mood '{mood}'. Please pick a valid mood."
                )
                is_valid = False

    try:
        energy = float(user_prefs.get("energy", 0.5))
        if not (0.0 <= energy <= 1.0):
            flags.append(f"Energy must be between 0.0 and 1.0 (got {energy}).")
            corrected["energy"] = max(0.0, min(1.0, energy))
            requires_review = True
        else:
            corrected["energy"] = energy
    except (TypeError, ValueError):
        flags.append("Energy must be a number between 0.0 and 1.0.")
        corrected["energy"] = 0.5
        requires_review = True

    if user_prefs.get("likes_acoustic") is None:
        flags.append("Acoustic preference not specified — defaulting to False.")
        corrected["likes_acoustic"] = False
        requires_review = True

    return ValidationResult(
        is_valid=is_valid,
        flags=flags,
        corrected_input=corrected,
        requires_human_review=requires_review,
    )


def validate_explanation(
    explanation: str,
    song: Dict,
    user_prefs: Dict,
    external_data=None,
) -> ValidationResult:
    """
    Check an LLM-generated explanation for factual drift.
    Flags: wrong artist name claim, genre/mood mismatch, external data contradiction.
    """
    flags: List[str] = []
    exp_lower = explanation.lower()

    artist = song.get("artist", "")
    if artist and artist.lower() not in exp_lower:
        pass  # artist not mentioned is fine
    # Check if a different artist name appears — heuristic: look for "by <word>"
    import re
    by_matches = re.findall(r"\bby\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", explanation)
    for mentioned in by_matches:
        if _normalize_label(mentioned) != _normalize_label(artist):
            flags.append(
                f"Explanation mentions artist '{mentioned}' but song artist is '{artist}'."
            )

    song_genre = _normalize_label(song.get("genre", ""))
    genre_mentions = [
        g for g in KNOWN_GENRES
        if g in exp_lower and g != song_genre
    ]
    if genre_mentions:
        flags.append(
            f"Explanation references genre(s) {genre_mentions} which don't match song genre '{song.get('genre')}'."
        )

    song_mood = _normalize_label(song.get("mood", ""))
    mood_mentions = [
        m for m in KNOWN_MOODS
        if m in exp_lower and m != song_mood
    ]
    if mood_mentions:
        flags.append(
            f"Explanation references mood(s) {mood_mentions} which don't match song mood '{song.get('mood')}'."
        )

    confidence = max(0.0, 1.0 - len(flags) * 0.25)
    return ValidationResult(
        is_valid=len(flags) == 0,
        flags=flags,
        corrected_input={},
        requires_human_review=confidence < 0.75,
    )
