"""
Axon Data Models

Schema design rationale:
- LearnerProfile: static identity + preferences
- ConceptMastery: per-concept probabilistic state (the core learner model)
- LearningSession: timestamped interaction container
- SessionEvent: granular interaction record
- ReviewSchedule: spaced repetition state per concept per learner
- KnowledgeConcept: node in the knowledge graph
- ConceptRelation: edge in the knowledge graph (type-tagged)
"""

from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, 
    ForeignKey, JSON, Enum as SAEnum, Text
)
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from datetime import datetime


class Base(DeclarativeBase):
    pass


def new_uuid():
    return str(uuid.uuid4())


# ─────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=new_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    learner_profile = relationship("LearnerProfile", back_populates="user", uselist=False)


# ─────────────────────────────────────────────
# Learner Model
# ─────────────────────────────────────────────

class LearnerProfile(Base):
    """
    Static + preference data about a learner.
    Separate from ConceptMastery which is dynamic.
    """
    __tablename__ = "learner_profiles"

    id = Column(String, primary_key=True, default=new_uuid)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    display_name = Column(String)
    
    # Onboarding-derived initial state
    self_reported_level = Column(String)  # beginner | intermediate | advanced
    goal_concept_id = Column(String, ForeignKey("knowledge_concepts.id"), nullable=True)
    active_domain = Column(String, default="mathematics")
    
    # Learned preferences (updated by adaptation engine)
    preferred_explanation_depth = Column(String, default="medium")  # brief | medium | deep
    preferred_example_style = Column(String, default="concrete")  # abstract | concrete | mixed
    
    session_count = Column(Integer, default=0)
    total_study_minutes = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="learner_profile")
    concept_masteries = relationship("ConceptMastery", back_populates="learner")
    review_schedules = relationship("ReviewSchedule", back_populates="learner")


class ConceptMastery(Base):
    """
    Core learner state: probabilistic mastery estimate per concept.
    
    mastery_score: [0.0, 1.0] — probability that learner has durable understanding
    confidence: [0.0, 1.0] — system confidence in the mastery estimate (based on evidence count)
    
    Updated after every assessment event via Bayesian update rule.
    """
    __tablename__ = "concept_masteries"

    id = Column(String, primary_key=True, default=new_uuid)
    learner_id = Column(String, ForeignKey("learner_profiles.id"), nullable=False)
    concept_id = Column(String, ForeignKey("knowledge_concepts.id"), nullable=False)
    
    mastery_score = Column(Float, default=0.0)   # P(mastered)
    confidence = Column(Float, default=0.1)       # system confidence in estimate
    attempt_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    
    # For forgetting curve: last time this was correctly demonstrated
    last_demonstrated_at = Column(DateTime, nullable=True)
    
    # Diagnostics: what kinds of errors appear
    error_patterns = Column(JSON, default=list)
    
    first_encountered_at = Column(DateTime, default=datetime.utcnow)
    last_updated_at = Column(DateTime, default=datetime.utcnow)

    learner = relationship("LearnerProfile", back_populates="concept_masteries")
    concept = relationship("KnowledgeConcept")


# ─────────────────────────────────────────────
# Sessions and Events
# ─────────────────────────────────────────────

class SessionStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    abandoned = "abandoned"


class LearningSession(Base):
    """
    Container for a learning session. One session = one sitting.
    """
    __tablename__ = "learning_sessions"

    id = Column(String, primary_key=True, default=new_uuid)
    learner_id = Column(String, ForeignKey("learner_profiles.id"), nullable=False)
    
    status = Column(SAEnum(SessionStatus), default=SessionStatus.active)
    focus_concept_id = Column(String, ForeignKey("knowledge_concepts.id"), nullable=True)
    
    # AI context: compressed learner state passed to AI at session start
    initial_context_snapshot = Column(JSON, nullable=True)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    
    events = relationship("SessionEvent", back_populates="session")


class EventType(str, enum.Enum):
    tutor_message = "tutor_message"
    learner_response = "learner_response"
    assessment = "assessment"
    concept_introduced = "concept_introduced"
    hint_requested = "hint_requested"
    explanation_requested = "explanation_requested"


class SessionEvent(Base):
    """
    Granular record of every interaction within a session.
    This is the raw evidence used to update learner state.
    """
    __tablename__ = "session_events"

    id = Column(String, primary_key=True, default=new_uuid)
    session_id = Column(String, ForeignKey("learning_sessions.id"), nullable=False)
    
    event_type = Column(SAEnum(EventType), nullable=False)
    concept_id = Column(String, ForeignKey("knowledge_concepts.id"), nullable=True)
    
    content = Column(Text)                    # message text
    metadata = Column(JSON, default=dict)     # evaluation scores, rubric outputs, etc.
    
    # Assessment-specific fields
    is_assessment = Column(Boolean, default=False)
    assessment_correct = Column(Boolean, nullable=True)
    assessment_score = Column(Float, nullable=True)  # [0, 1]
    
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("LearningSession", back_populates="events")


# ─────────────────────────────────────────────
# Knowledge Graph
# ─────────────────────────────────────────────

class KnowledgeConcept(Base):
    """
    Node in the knowledge graph.
    
    difficulty: [0.0, 1.0] — estimated cognitive load to acquire this concept
    estimated_minutes: typical time to reach threshold mastery from prerequisites
    """
    __tablename__ = "knowledge_concepts"

    id = Column(String, primary_key=True)  # human-readable slug: "quadratic_formula"
    domain = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    difficulty = Column(Float, default=0.5)
    estimated_minutes = Column(Integer, default=20)
    
    # Canonical explanation seeded into AI context
    core_explanation = Column(Text, nullable=True)
    
    # Common misconceptions — used to seed AI evaluator
    common_misconceptions = Column(JSON, default=list)
    
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    prerequisites = relationship(
        "ConceptRelation",
        foreign_keys="ConceptRelation.target_concept_id",
        back_populates="target",
    )
    dependents = relationship(
        "ConceptRelation",
        foreign_keys="ConceptRelation.source_concept_id",
        back_populates="source",
    )


class RelationType(str, enum.Enum):
    prerequisite = "prerequisite"       # must know source before target
    related = "related"                 # reinforces/contextualizes
    application_of = "application_of"  # target applies source concept


class ConceptRelation(Base):
    """
    Edge in the knowledge graph.
    source -> target means: knowing source helps with target
    """
    __tablename__ = "concept_relations"

    id = Column(String, primary_key=True, default=new_uuid)
    source_concept_id = Column(String, ForeignKey("knowledge_concepts.id"), nullable=False)
    target_concept_id = Column(String, ForeignKey("knowledge_concepts.id"), nullable=False)
    relation_type = Column(SAEnum(RelationType), default=RelationType.prerequisite)
    strength = Column(Float, default=1.0)  # how strong the dependency is

    source = relationship("KnowledgeConcept", foreign_keys=[source_concept_id], back_populates="dependents")
    target = relationship("KnowledgeConcept", foreign_keys=[target_concept_id], back_populates="prerequisites")


# ─────────────────────────────────────────────
# Memory System
# ─────────────────────────────────────────────

class ReviewSchedule(Base):
    """
    SM-2 spaced repetition state per concept per learner.
    Updated after every review event.
    """
    __tablename__ = "review_schedules"

    id = Column(String, primary_key=True, default=new_uuid)
    learner_id = Column(String, ForeignKey("learner_profiles.id"), nullable=False)
    concept_id = Column(String, ForeignKey("knowledge_concepts.id"), nullable=False)
    
    # SM-2 state
    interval_days = Column(Float, default=1.0)     # current review interval
    easiness_factor = Column(Float, default=2.5)   # SM-2 EF
    repetitions = Column(Integer, default=0)
    
    next_review_at = Column(DateTime, nullable=True)
    last_reviewed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    learner = relationship("LearnerProfile", back_populates="review_schedules")
    concept = relationship("KnowledgeConcept")
