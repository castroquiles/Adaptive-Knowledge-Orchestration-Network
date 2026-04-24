"""
Learner Model

Maintains and updates the probabilistic model of a learner's knowledge state.

Design:
- Mastery is estimated per concept, not per session
- Updates use a simple Bayesian update: evidence from correct/incorrect responses
  shifts the mastery estimate, weighted by system confidence in the assessment
- Confidence in the estimate grows with evidence count (reduces on long inactivity)
- The model is the single source of truth that drives all adaptation decisions
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timedelta
import math
import logging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────
# Types
# ─────────────────────────────────────────────────────

@dataclass
class ConceptState:
    concept_id: str
    mastery_score: float = 0.0       # P(mastered), [0, 1]
    confidence: float = 0.1          # system confidence in estimate
    attempt_count: int = 0
    correct_count: int = 0
    last_demonstrated_at: Optional[datetime] = None
    error_patterns: list = field(default_factory=list)


@dataclass
class LearnerState:
    learner_id: str
    concept_states: dict[str, ConceptState] = field(default_factory=dict)
    active_domain: str = "mathematics"
    goal_concept_id: Optional[str] = None
    preferred_depth: str = "medium"   # brief | medium | deep


# ─────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────

# Mastery threshold: above this, concept is considered "known"
# Set conservatively — it is better to over-review than under-review
MASTERY_THRESHOLD = 0.80

# Forgetting decay rate: how quickly mastery degrades without review
# Based on Ebbinghaus; domain-specific tuning is an open research question
DECAY_RATE = 0.05   # per day

# Learning rate: how much a single correct response shifts mastery
# Higher for early attempts (high-signal); lower when already confident
BASE_LEARNING_RATE = 0.15

# Minimum evidence count before system is confident in mastery estimate
MIN_CONFIDENCE_EVIDENCE = 5


# ─────────────────────────────────────────────────────
# Mastery Update Logic
# ─────────────────────────────────────────────────────

def update_mastery(
    state: ConceptState,
    assessment_score: float,   # [0, 1] — quality of response
    assessment_weight: float = 1.0,  # how reliable was this assessment
    timestamp: Optional[datetime] = None,
) -> ConceptState:
    """
    Bayesian-style mastery update.
    
    Correct response: shifts mastery up, magnitude decreases as mastery increases
    Incorrect response: shifts mastery down, magnitude proportional to error severity
    
    The update rate scales with assessment_weight (a low-quality question
    should carry less evidential weight than a deep open-ended question).
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    prev_mastery = state.mastery_score
    lr = BASE_LEARNING_RATE * assessment_weight

    if assessment_score >= 0.7:
        # Correct response
        # Diminishing returns as mastery approaches 1.0
        delta = lr * (1.0 - prev_mastery) * assessment_score
        new_mastery = min(1.0, prev_mastery + delta)
        state.correct_count += 1
        state.last_demonstrated_at = timestamp
    else:
        # Incorrect or partial response
        # Decay proportional to error severity and current mastery
        error_severity = 1.0 - assessment_score
        delta = lr * prev_mastery * error_severity
        new_mastery = max(0.0, prev_mastery - delta)

    state.mastery_score = new_mastery
    state.attempt_count += 1

    # Update confidence: grows with evidence, capped at 1.0
    state.confidence = min(1.0, 0.1 + (state.attempt_count / MIN_CONFIDENCE_EVIDENCE) * 0.9)

    logger.debug(
        f"Mastery update for {state.concept_id}: "
        f"{prev_mastery:.3f} -> {new_mastery:.3f} "
        f"(score={assessment_score:.2f}, confidence={state.confidence:.2f})"
    )

    return state


def apply_forgetting(state: ConceptState, as_of: Optional[datetime] = None) -> ConceptState:
    """
    Applies time-based decay to mastery score.
    Called when retrieving learner state to get current estimate.
    
    Uses exponential decay: M(t) = M0 * e^(-decay_rate * days_since_last_review)
    Only applied if mastery is above threshold (no point decaying below floor).
    """
    if state.last_demonstrated_at is None:
        return state
    
    if as_of is None:
        as_of = datetime.utcnow()

    days_elapsed = (as_of - state.last_demonstrated_at).total_seconds() / 86400
    
    if days_elapsed <= 0:
        return state

    decay_factor = math.exp(-DECAY_RATE * days_elapsed)
    state.mastery_score = state.mastery_score * decay_factor
    
    return state


def is_mastered(state: ConceptState, as_of: Optional[datetime] = None) -> bool:
    """
    Returns True if concept is considered mastered with sufficient confidence.
    Both the mastery score AND the confidence must meet threshold.
    """
    current = apply_forgetting(state, as_of)
    return (
        current.mastery_score >= MASTERY_THRESHOLD
        and current.confidence >= 0.5
    )


def needs_review(state: ConceptState, as_of: Optional[datetime] = None) -> bool:
    """
    Returns True if this concept was once known but has decayed below threshold.
    Signals that spaced repetition review is needed.
    """
    if as_of is None:
        as_of = datetime.utcnow()
    
    was_mastered = state.correct_count >= 3 and max(
        0, state.mastery_score  # before decay
    ) >= MASTERY_THRESHOLD
    
    current = apply_forgetting(state, as_of)
    currently_mastered = current.mastery_score >= MASTERY_THRESHOLD
    
    return was_mastered and not currently_mastered


# ─────────────────────────────────────────────────────
# Learner State Utilities
# ─────────────────────────────────────────────────────

def get_mastered_concepts(state: LearnerState) -> list[str]:
    return [
        cid for cid, cs in state.concept_states.items()
        if is_mastered(cs)
    ]


def get_weak_concepts(state: LearnerState, top_n: int = 5) -> list[str]:
    """
    Returns concepts where mastery is low but some attempts have been made.
    These are gaps, not unknowns.
    """
    candidates = [
        (cid, cs) for cid, cs in state.concept_states.items()
        if cs.attempt_count > 0 and not is_mastered(cs)
    ]
    candidates.sort(key=lambda x: x[1].mastery_score)
    return [cid for cid, _ in candidates[:top_n]]


def get_concepts_due_for_review(state: LearnerState) -> list[str]:
    return [
        cid for cid, cs in state.concept_states.items()
        if needs_review(cs)
    ]


def summarize_for_ai_context(state: LearnerState, max_concepts: int = 20) -> dict:
    """
    Produces a compressed summary of learner state for injection into AI context.
    Prioritizes recent and high-signal concepts. Truncated to control token usage.
    """
    sorted_concepts = sorted(
        state.concept_states.items(),
        key=lambda x: x[1].last_demonstrated_at or datetime.min,
        reverse=True
    )[:max_concepts]

    return {
        "learner_id": state.learner_id,
        "domain": state.active_domain,
        "goal": state.goal_concept_id,
        "preferred_depth": state.preferred_depth,
        "known_concepts": [
            cid for cid, cs in sorted_concepts if is_mastered(cs)
        ],
        "weak_concepts": [
            {"concept_id": cid, "mastery": round(cs.mastery_score, 2)}
            for cid, cs in sorted_concepts
            if cs.attempt_count > 0 and not is_mastered(cs)
        ],
        "due_for_review": get_concepts_due_for_review(state),
    }
