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
    valid_styles = ["genre-first", "mood-first", "energy-focused"]
    print("Choose a recommendation style:")
    for i, s in enumerate(valid_styles, 1):
        print(f"  {i}. {s}")

    choice = input("Enter style name or number (default: genre-first): ").strip()

    if choice in ("1", "genre-first"):
        style = "genre-first"
    elif choice in ("2", "mood-first"):
        style = "mood-first"
    elif choice in ("3", "energy-focused"):
        style = "energy-focused"
    else:
        print(f"Unknown choice '{choice}', defaulting to genre-first.")
        style = "genre-first"

    print(f"\n=== Style: {style} ===")
    recommendations = recommend_songs(user_prefs_2, songs, k=5, style=style)
    for song, score, explanation in recommendations:
        print(f"{song['title']} - Score: {score:.2f}")
        print(f"Because: {explanation}")
        print()


if __name__ == "__main__":
    main()
