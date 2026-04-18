from dataclasses import dataclass, field
from typing import Dict, List

_BIO_TEMPLATES = [
    "{artist} is a {genre} artist known for crafting {mood} soundscapes that connect with listeners on an emotional level.",
    "{artist} blends {genre} influences with a signature {mood} aesthetic, earning a dedicated fanbase worldwide.",
    "{artist} emerged from the underground {genre} scene, celebrated for their distinctly {mood} sonic palette.",
    "{artist} has spent years refining a {genre}-rooted sound that consistently evokes a {mood} atmosphere.",
    "{artist} is a celebrated {genre} act whose catalog is defined by its compelling {mood} character.",
]

_REVIEW_TEMPLATES_BY_MOOD = {
    "happy":      ["Pure joy in audio form.", "Impossible not to smile.", "Lifts your mood instantly."],
    "chill":      ["Perfect background music.", "Deeply relaxing.", "Flows effortlessly."],
    "intense":    ["Absolutely electrifying.", "Raw energy throughout.", "Leaves you breathless."],
    "relaxed":    ["Wonderfully soothing.", "Like a warm bath for the ears.", "Effortlessly calming."],
    "focused":    ["Great for deep work sessions.", "Keeps you in the zone.", "Subtle and effective."],
    "excited":    ["Gets the adrenaline going.", "High-octane from start to finish.", "Pure excitement."],
    "romantic":   ["Sets the perfect mood.", "Beautifully tender.", "Timeless and warm."],
    "calm":       ["Serenely beautiful.", "Quiet and profound.", "A moment of stillness."],
    "confident":  ["Struts with attitude.", "Makes you feel unstoppable.", "Pure self-assurance."],
    "moody":      ["Atmospheric and layered.", "Stirs something deep.", "Hauntingly good."],
    "hopeful":    ["Genuinely uplifting.", "Leaves you optimistic.", "Quietly inspiring."],
    "melancholic":["Beautiful sadness.", "Emotionally resonant.", "Lingers long after it ends."],
    "warm":       ["Like a hug in song form.", "Cozy and inviting.", "Instantly comforting."],
    "aggressive": ["Ferocious and unrelenting.", "Not for the faint-hearted.", "Maximum intensity."],
}

_SIMILAR_ARTISTS_BY_GENRE = {
    "pop":       ["Dua Lipa", "The Weeknd"],
    "lofi":      ["Joji", "Idealism"],
    "rock":      ["Arctic Monkeys", "Foo Fighters"],
    "ambient":   ["Brian Eno", "Moby"],
    "jazz":      ["Norah Jones", "Miles Davis"],
    "synthwave": ["Kavinsky", "Gunship"],
    "indiepop":  ["Vampire Weekend", "Tame Impala"],
    "hiphop":    ["Kendrick Lamar", "J. Cole"],
    "edm":       ["Martin Garrix", "Illenium"],
    "rnb":       ["H.E.R.", "SZA"],
    "metal":     ["Metallica", "Rammstein"],
    "classical": ["Ludovico Einaudi", "Yiruma"],
    "reggae":    ["Bob Marley", "Damian Marley"],
    "country":   ["Morgan Wallen", "Kacey Musgraves"],
}


@dataclass
class ExternalSongData:
    artist_bio: str
    trending_score: float
    review_sentiment: float
    review_snippets: List[str]
    similar_artists: List[str]
    data_quality_flags: List[str] = field(default_factory=list)


def fetch_external_data(song: Dict) -> ExternalSongData:
    """
    Deterministic mock: returns plausible external data for a song.
    trending_score is derived from energy + valence (normalized).
    review_sentiment mirrors song valence.
    """
    from recommender import _normalize_label

    artist = song.get("artist", "Unknown")
    genre_raw = song.get("genre", "pop")
    mood = song.get("mood", "happy")
    energy = float(song.get("energy", 0.5))
    valence = float(song.get("valence", 0.5))

    genre_key = _normalize_label(genre_raw)

    # Deterministic bio selection via artist name hash
    template_index = hash(artist) % len(_BIO_TEMPLATES)
    bio = _BIO_TEMPLATES[template_index].format(
        artist=artist, genre=genre_raw, mood=mood
    )

    trending_score = round((energy * 0.6 + valence * 0.4), 3)
    review_sentiment = round(valence, 3)

    mood_key = _normalize_label(mood)
    snippets = _REVIEW_TEMPLATES_BY_MOOD.get(mood_key, ["A solid track worth hearing."])

    similar = _SIMILAR_ARTISTS_BY_GENRE.get(genre_key, ["Various Artists", "Indie Collective"])

    quality_flags: List[str] = []
    if trending_score < 0.2:
        quality_flags.append(f"Low trending score ({trending_score:.2f}) — confidence limited.")
    if trending_score > 0.95:
        quality_flags.append(f"Trending score outlier ({trending_score:.2f}) — may be inflated.")
    if review_sentiment < 0.3:
        quality_flags.append("Low review sentiment — limited positive signal.")

    return ExternalSongData(
        artist_bio=bio,
        trending_score=trending_score,
        review_sentiment=review_sentiment,
        review_snippets=snippets,
        similar_artists=similar,
        data_quality_flags=quality_flags,
    )


def fetch_batch(songs: List[Dict]) -> Dict[int, ExternalSongData]:
    """Returns a map of song id → ExternalSongData for all songs."""
    return {song["id"]: fetch_external_data(song) for song in songs}


def assess_data_quality(external_map: Dict[int, ExternalSongData]) -> List[str]:
    """
    Aggregates quality flags across all retrieved records.
    Returns a list of warnings for the human review checkpoint.
    """
    all_flags: List[str] = []
    for song_id, data in external_map.items():
        for flag in data.data_quality_flags:
            all_flags.append(f"Song {song_id}: {flag}")
    return all_flags
