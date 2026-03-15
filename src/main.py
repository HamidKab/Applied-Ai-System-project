"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

try:
    from .recommender import load_songs, recommend_songs
except ImportError:
    from recommender import load_songs, recommend_songs


def main() -> None:
    songs = load_songs("data/songs.csv") 

    # Starter example profile
    user_prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False}

    user_prefs_2 = {
        "genre": "jazz",
        "mood": "relaxed",
        "energy": 0.3,
        "likes_acoustic": True
    }

    user_prefs_3 = {
        "genre": "hip-hop",
        "mood": "energetic",
        "energy": 0.85,
        "likes_acoustic": False
    }
    user_prefs_edge = {
    "genre": "",          # empty genre - may skip genre scoring entirely
    "mood": "HAPPY",      # uppercase - tests case sensitivity handling
    "energy": 0.5,        # exactly mid-range - ties may be unpredictable
    "likes_acoustic": None  # None - may skip acoustic scoring or cause errors
}
    recommendations = recommend_songs(user_prefs_3, songs, k=5)

    print("\nTop recommendations:\n")
    for rec in recommendations:
        # You decide the structure of each returned item.
        # A common pattern is: (song, score, explanation)
        song, score, explanation = rec
        print(f"{song['title']} - Score: {score:.2f}")
        print(f"Because: {explanation}")
        print()


if __name__ == "__main__":
    main()
