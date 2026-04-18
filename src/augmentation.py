from typing import Dict, List

from external_data import ExternalSongData


def augment_song(song: Dict, external: ExternalSongData) -> Dict:
    """
    Merges a song dict with ExternalSongData fields.
    Returns a new dict — does not mutate the input.
    """
    return {
        **song,
        "artist_bio": external.artist_bio,
        "trending_score": external.trending_score,
        "review_sentiment": external.review_sentiment,
        "review_snippets": external.review_snippets,
        "similar_artists": external.similar_artists,
    }


def augment_batch(
    songs: List[Dict],
    external_map: Dict[int, ExternalSongData],
) -> List[Dict]:
    """Applies augment_song to each song using its id as the lookup key."""
    result = []
    for song in songs:
        ext = external_map.get(song["id"])
        if ext is not None:
            result.append(augment_song(song, ext))
        else:
            result.append(dict(song))
    return result


def format_for_prompt(augmented_song: Dict, user_prefs: Dict) -> str:
    """
    Renders the augmented song and user preferences as a plain-text
    block for injection into the LLM prompt.
    """
    snippets = "\n  - ".join(augmented_song.get("review_snippets", []))
    similar = ", ".join(augmented_song.get("similar_artists", []))

    return f"""SONG INFORMATION:
  Title: {augmented_song.get('title')}
  Artist: {augmented_song.get('artist')}
  Genre: {augmented_song.get('genre')}
  Mood: {augmented_song.get('mood')}
  Energy: {augmented_song.get('energy')}
  Acousticness: {augmented_song.get('acousticness')}
  Valence (positiveness): {augmented_song.get('valence')}
  Tempo (BPM): {augmented_song.get('tempo_bpm')}
  Artist bio: {augmented_song.get('artist_bio')}
  Trending score: {augmented_song.get('trending_score')}
  Review sentiment: {augmented_song.get('review_sentiment')}
  Listener reviews:
  - {snippets}
  Similar artists: {similar}

USER PREFERENCES:
  Favorite genre: {user_prefs.get('genre')}
  Favorite mood: {user_prefs.get('mood')}
  Target energy level: {user_prefs.get('energy')}
  Likes acoustic music: {user_prefs.get('likes_acoustic')}"""
