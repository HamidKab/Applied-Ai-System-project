import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import google.generativeai as genai

from recommender import recommend_songs
from validation import ValidationResult, validate_user_input
from external_data import ExternalSongData, fetch_batch, assess_data_quality
from augmentation import augment_batch
from llm_client import generate_batch_explanations, generate_boilerplate_batch
from explanation_validator import ExplanationValidationResult, validate_explanation
from ranker import BiasReport, rank_candidates, check_bias, apply_diversity_reranking


@dataclass
class PipelineState:
    # Stage 1
    user_prefs: Optional[Dict] = None
    input_validation: Optional[ValidationResult] = None
    # Stage 2
    candidates: Optional[List[Tuple[Dict, float, str]]] = None
    # Stage 3
    external_data: Optional[Dict[int, ExternalSongData]] = None
    data_quality_flags: Optional[List[str]] = None
    # Stage 4
    augmented_songs: Optional[List[Dict]] = None
    # Stage 5
    explanations: Optional[List[str]] = None
    # Stage 6
    explanation_validations: Optional[List[ExplanationValidationResult]] = None
    # Stage 7
    ranked: Optional[List[Tuple[Dict, float, str]]] = None
    bias_report: Optional[BiasReport] = None
    # Stage 8
    final_recommendations: Optional[List[Tuple[Dict, float, str]]] = None
    # Meta
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prompt_context: str = ""


def run_stage_1_validate(state: PipelineState) -> PipelineState:
    """Validate user_prefs and store the result."""
    result = validate_user_input(state.user_prefs or {})
    return PipelineState(
        **{**state.__dict__, "input_validation": result}
    )


def run_stage_2_retrieve(
    state: PipelineState,
    songs: List[Dict],
    k_candidates: int = 15,
    threshold: float = 0.3,
    style: str = "genre-first",
) -> PipelineState:
    """
    Score all songs with recommend_songs, take up to k_candidates,
    then filter by threshold. Stores raw (song, score, reason) tuples.
    """
    prefs = state.input_validation.corrected_input if state.input_validation else state.user_prefs
    all_scored = recommend_songs(prefs, songs, k=k_candidates, style=style)
    candidates = [(s, sc, r) for s, sc, r in all_scored if sc >= threshold]
    return PipelineState(**{**state.__dict__, "candidates": candidates})


def run_stage_3_external(state: PipelineState) -> PipelineState:
    """Fetch external data for all candidates and run quality assessment."""
    songs = [s for s, _, _ in (state.candidates or [])]
    ext_map = fetch_batch(songs)
    quality_flags = assess_data_quality(ext_map)
    return PipelineState(
        **{**state.__dict__, "external_data": ext_map, "data_quality_flags": quality_flags}
    )


def run_stage_4_augment(state: PipelineState) -> PipelineState:
    """Merge candidate songs with external data."""
    candidate_songs = [s for s, _, _ in (state.candidates or [])]
    augmented = augment_batch(candidate_songs, state.external_data or {})
    return PipelineState(**{**state.__dict__, "augmented_songs": augmented})


def run_stage_5_explain(
    state: PipelineState,
    client: genai.GenerativeModel,
    ai_enabled: bool = True,
) -> PipelineState:
    """
    Call LLM to generate explanations for all augmented songs.
    When ai_enabled is False, uses template boilerplate instead of the API.
    """
    prefs = state.input_validation.corrected_input if state.input_validation else state.user_prefs
    if ai_enabled:
        explanations = generate_batch_explanations(
            state.augmented_songs or [],
            prefs,
            client,
            prompt_context=state.prompt_context,
        )
    else:
        explanations = generate_boilerplate_batch(state.augmented_songs or [], prefs)
    return PipelineState(**{**state.__dict__, "explanations": explanations})


def run_stage_6_validate_explanations(state: PipelineState) -> PipelineState:
    """Run factual validation on each LLM explanation."""
    augmented = state.augmented_songs or []
    explanations = state.explanations or []
    ext_map = state.external_data or {}

    validations: List[ExplanationValidationResult] = []
    for song, explanation in zip(augmented, explanations):
        ext = ext_map.get(song.get("id", -1))
        result = validate_explanation(explanation, song, ext)
        # Carry through the (possibly human-edited) explanation text
        result.explanation = explanation
        validations.append(result)

    return PipelineState(**{**state.__dict__, "explanation_validations": validations})


def run_stage_7_rank(state: PipelineState, k: int = 5) -> PipelineState:
    """Compute composite scores, sort, and run bias check."""
    candidates = state.candidates or []
    ext_map = state.external_data or {}
    validations = state.explanation_validations or []

    rejected_ids = {v.song_id for v in validations if v.rejected}
    filtered_candidates = [(s, sc, r) for s, sc, r in candidates if s.get("id") not in rejected_ids]
    ranked = rank_candidates(filtered_candidates, ext_map, validations)
    bias = check_bias(ranked, k)

    return PipelineState(**{**state.__dict__, "ranked": ranked, "bias_report": bias})


def run_stage_8_finalize(
    state: PipelineState,
    k: int = 5,
    apply_diversity: bool = False,
) -> PipelineState:
    """Optionally apply diversity reranking and slice to final top-k."""
    ranked = state.ranked or []
    if apply_diversity:
        final = apply_diversity_reranking(ranked, k)
    else:
        final = ranked[:k]
    return PipelineState(**{**state.__dict__, "final_recommendations": final})
