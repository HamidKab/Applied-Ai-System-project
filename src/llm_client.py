from typing import Dict, List

import google.generativeai as genai

from augmentation import format_for_prompt

MODEL_ID = "gemma-3-1b-it"

SYSTEM_PROMPT = (
    "You are a music recommendation assistant. "
    "Your task is to explain in 2-3 sentences why a specific song is a good match "
    "for a listener's preferences. "
    "Base your explanation ONLY on the song metadata and user preferences provided. "
    "Do not invent facts about the artist or song that are not in the provided context."
)


class LLMError(Exception):
    """Raised when the Gemini API call fails."""


def build_explanation_prompt(
    augmented_song: Dict,
    user_prefs: Dict,
    prompt_context: str = "",
) -> str:
    context_block = format_for_prompt(augmented_song, user_prefs)
    extra = f"\n\nAdditional guidance: {prompt_context}" if prompt_context else ""
    return (
        f"{context_block}{extra}\n\n"
        "Please explain in 2-3 sentences why this song is a good match for the user."
    )


def generate_explanation(
    augmented_song: Dict,
    user_prefs: Dict,
    model: genai.GenerativeModel,
    prompt_context: str = "",
) -> str:
    """
    Calls Gemini and returns the explanation text.
    Raises LLMError on API failure.
    """
    prompt = build_explanation_prompt(augmented_song, user_prefs, prompt_context)
    full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
    try:
        response = model.generate_content(full_prompt)
        return response.text.strip()
    except Exception as exc:
        raise LLMError(f"Gemini API call failed: {exc}") from exc


def generate_batch_explanations(
    augmented_songs: List[Dict],
    user_prefs: Dict,
    model: genai.GenerativeModel,
    prompt_context: str = "",
) -> List[str]:
    """
    Generates explanations for all songs sequentially.
    Returns a list of explanation strings in the same order as augmented_songs.
    On LLMError for a single song, stores the error message as a placeholder.
    """
    explanations: List[str] = []
    for song in augmented_songs:
        try:
            text = generate_explanation(song, user_prefs, model, prompt_context)
        except LLMError as exc:
            text = f"[Explanation unavailable: {exc}]"
        explanations.append(text)
    return explanations


# ---------------------------------------------------------------------------
# Boilerplate fallback (AI generation disabled)
# ---------------------------------------------------------------------------

def generate_boilerplate_explanation(augmented_song: Dict, user_prefs: Dict) -> str:
    """
    Returns a template explanation without any API call.
    Used when AI generation is toggled off.
    """
    title = augmented_song.get("title", "This song")
    artist = augmented_song.get("artist", "the artist")
    genre = augmented_song.get("genre", "this genre")
    mood = augmented_song.get("mood", "this mood")
    energy = float(augmented_song.get("energy", 0.5))
    acousticness = float(augmented_song.get("acousticness", 0.5))

    pref_genre = user_prefs.get("genre", genre)
    pref_mood = user_prefs.get("mood", mood)
    pref_energy = float(user_prefs.get("energy", 0.5))
    likes_acoustic = user_prefs.get("likes_acoustic", False)

    genre_line = (
        f"It matches your preferred genre ({pref_genre})."
        if genre.lower() == pref_genre.lower()
        else f"Although it is a {genre} track, it shares qualities with your preferred genre ({pref_genre})."
    )
    mood_line = (
        f"The {mood} mood aligns with what you are looking for."
        if mood.lower() == pref_mood.lower()
        else f"Its {mood} feel may complement your preferred {pref_mood} mood."
    )
    energy_diff = abs(energy - pref_energy)
    energy_line = (
        "The energy level closely matches your target."
        if energy_diff < 0.15
        else f"The energy level ({energy:.2f}) is {'higher' if energy > pref_energy else 'lower'} than your target ({pref_energy:.2f})."
    )
    acoustic_line = (
        "Its acoustic character suits your listening style."
        if (likes_acoustic and acousticness > 0.5) or (not likes_acoustic and acousticness <= 0.5)
        else "Its acoustic profile differs slightly from your usual preference."
    )

    return (
        f"**{title}** by {artist} was selected based on your preferences. "
        f"{genre_line} {mood_line} {energy_line} {acoustic_line}"
    )


def generate_boilerplate_batch(
    augmented_songs: List[Dict],
    user_prefs: Dict,
) -> List[str]:
    """Generates boilerplate explanations for all songs without any API calls."""
    return [generate_boilerplate_explanation(song, user_prefs) for song in augmented_songs]
