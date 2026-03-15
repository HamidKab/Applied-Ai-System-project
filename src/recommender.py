from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import csv


def _normalize_label(s: str) -> str:
    """Normalize genre/mood labels: lowercase, strip hyphens and spaces."""
    return s.lower().replace("-", "").replace(" ", "").strip()

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    @staticmethod
    def _closeness_score(value: float, target: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
        """
        Distance-to-preference score in [0, 1].
        1.0 means exact match, lower scores mean farther from target.
        """
        feature_range = max_value - min_value
        if feature_range <= 0:
            return 0.0
        normalized_distance = abs(value - target) / feature_range
        return max(0.0, 1.0 - normalized_distance)

    def _score_song(self, user: UserProfile, song: Song) -> float:
        # Basic weighted scoring based on user preferences and song attributes.
        score = 0.0

        if _normalize_label(song.genre) == _normalize_label(user.favorite_genre):
            score += 0.50

        if _normalize_label(song.mood) == _normalize_label(user.favorite_mood):
            score += 0.25

        energy_match = self._closeness_score(song.energy, user.target_energy, 0.0, 1.0)
        score += 0.20 * energy_match

        preferred_acoustic = 1.0 if user.likes_acoustic else 0.0
        acoustic_match = self._closeness_score(song.acousticness, preferred_acoustic, 0.0, 1.0)
        score += 0.10 * acoustic_match

        return score

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        # Score all songs and return the top k.
        ranked = sorted(self.songs, key=lambda song: self._score_song(user, song), reverse=True)
        return ranked[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        reasons = []
        if _normalize_label(song.genre) == _normalize_label(user.favorite_genre):
            reasons.append(f"matches your favorite genre ({user.favorite_genre})")
        if _normalize_label(song.mood) == _normalize_label(user.favorite_mood):
            reasons.append(f"matches your preferred mood ({user.favorite_mood})")

        energy_match = self._closeness_score(song.energy, user.target_energy, 0.0, 1.0)
        reasons.append(f"energy similarity is {energy_match:.2f}")

        acoustic_pref_text = "acoustic" if user.likes_acoustic else "less acoustic"
        reasons.append(f"it is {acoustic_pref_text} to match your listening style")

        return "; ".join(reasons)

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py
    """
    songs: List[Dict] = []
    with open(csv_path, "r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            songs.append(
                {
                    "id": int(row["id"]),
                    "title": row["title"],
                    "artist": row["artist"],
                    "genre": row["genre"],
                    "mood": row["mood"],
                    "energy": float(row["energy"]),
                    "tempo_bpm": float(row["tempo_bpm"]),
                    "valence": float(row["valence"]),
                    "danceability": float(row["danceability"]),
                    "acousticness": float(row["acousticness"]),
                }
            )
    return songs


def _numeric_feature_score(value: float, preference: float, min_value: float, max_value: float) -> float:
    feature_range = max_value - min_value
    if feature_range <= 0:
        return 0.0
    normalized_distance = abs(value - preference) / feature_range
    return max(0.0, 1.0 - normalized_distance)


def _score_song_dict(user_prefs: Dict, song: Dict) -> Tuple[float, str]:
    score = 0.0
    reasons: List[str] = []

    preferred_genre = _normalize_label(str(user_prefs.get("genre", "")))
    preferred_mood = _normalize_label(str(user_prefs.get("mood", "")))
    preferred_energy = float(user_prefs.get("energy", 0.5))

    if preferred_genre and _normalize_label(song["genre"]) == preferred_genre:
        score += 0.50
        reasons.append("genre match")

    if preferred_mood and _normalize_label(song["mood"]) == preferred_mood:
        score += 0.25
        reasons.append("mood match")

    energy_similarity = _numeric_feature_score(song["energy"], preferred_energy, 0.0, 1.0)
    score += 0.20 * energy_similarity
    reasons.append(f"energy similarity {energy_similarity:.2f}")

    preferred_acoustic = user_prefs.get("likes_acoustic")
    if preferred_acoustic is not None:
        acoustic_target = 1.0 if bool(preferred_acoustic) else 0.0
        acoustic_similarity = _numeric_feature_score(song["acousticness"], acoustic_target, 0.0, 1.0)
        score += 0.10 * acoustic_similarity
        reasons.append(f"acoustic similarity {acoustic_similarity:.2f}")

    return score, "; ".join(reasons)

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """
    Functional implementation of the recommendation logic.
    Required by src/main.py
    """
    scored: List[Tuple[Dict, float, str]] = []
    for song in songs:
        score, explanation = _score_song_dict(user_prefs, song)
        scored.append((song, score, explanation))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:k]
