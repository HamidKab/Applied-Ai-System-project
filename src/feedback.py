import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

FEEDBACK_LOG_PATH = Path(__file__).parent.parent / "data" / "feedback_log.json"


@dataclass
class FeedbackRecord:
    session_id: str
    timestamp: str
    user_prefs: Dict
    recommendations: List[Dict]   # [{id, title, artist, composite_score}]
    song_ratings: Dict[str, int]  # str(song_id) → 1 (like) or 0 (dislike)
    explanation_helpfulness: Dict[str, int]  # str(song_id) → 1 or 0
    overall_rating: int           # 1–5
    free_text: str = ""
    diversity_applied: bool = False


def new_record(
    session_id: str,
    user_prefs: Dict,
    recommendations: List[Dict],
) -> FeedbackRecord:
    return FeedbackRecord(
        session_id=session_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        user_prefs=user_prefs,
        recommendations=recommendations,
        song_ratings={},
        explanation_helpfulness={},
        overall_rating=3,
    )


def save_feedback(record: FeedbackRecord) -> None:
    """Appends record to feedback_log.json as a JSON-lines entry."""
    FEEDBACK_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FEEDBACK_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(record)) + "\n")


def load_feedback() -> List[FeedbackRecord]:
    """Reads all entries from feedback_log.json."""
    if not FEEDBACK_LOG_PATH.exists():
        return []
    records: List[FeedbackRecord] = []
    with open(FEEDBACK_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    records.append(FeedbackRecord(**data))
                except Exception:
                    pass
    return records


def compute_feedback_summary(records: List[FeedbackRecord]) -> Dict:
    """
    Returns aggregated stats for the Analysis tab:
    - total_sessions
    - mean_overall_rating
    - per_genre_like_rate  {genre: rate}
    - explanation_helpfulness_rate  (overall fraction)
    - diversity_applied_count
    """
    if not records:
        return {
            "total_sessions": 0,
            "mean_overall_rating": None,
            "per_genre_like_rate": {},
            "explanation_helpfulness_rate": None,
            "diversity_applied_count": 0,
        }

    total = len(records)
    mean_rating = sum(r.overall_rating for r in records) / total

    genre_likes: Dict[str, List[int]] = {}
    for rec in records:
        genre = rec.user_prefs.get("genre", "unknown")
        for song_id_str, liked in rec.song_ratings.items():
            genre_likes.setdefault(genre, []).append(liked)

    per_genre_like_rate = {
        g: round(sum(v) / len(v), 3)
        for g, v in genre_likes.items()
        if v
    }

    all_helpfulness: List[int] = []
    for rec in records:
        all_helpfulness.extend(rec.explanation_helpfulness.values())

    helpfulness_rate = (
        round(sum(all_helpfulness) / len(all_helpfulness), 3)
        if all_helpfulness
        else None
    )

    diversity_count = sum(1 for r in records if r.diversity_applied)

    return {
        "total_sessions": total,
        "mean_overall_rating": round(mean_rating, 2),
        "per_genre_like_rate": per_genre_like_rate,
        "explanation_helpfulness_rate": helpfulness_rate,
        "diversity_applied_count": diversity_count,
    }
