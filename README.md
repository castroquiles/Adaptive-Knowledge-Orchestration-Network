# AXON
# Adaptive-Knowledge-Orchestration-Network
A foundational open-source system for AI-native education infrastructure.

## What This Is

Axon is a runtime for personalized learning. It maintains a dynamic model of each learner's cognitive state, maps that state against a structured knowledge graph, and orchestrates AI-driven instruction, assessment, and memory consolidation in a continuous feedback loop.

It is not a course platform. It is not an LLM wrapper. It is not a productivity tool.

It is an attempt to build education infrastructure from first principles, given that the core constraint of traditional systems — the impossibility of one-to-one instruction at scale — no longer holds.

---

## The Problem

Modern education systems were architected around a fundamental scarcity: one teacher, many students. This constraint produced:

- Fixed curricula that cannot adapt to individual knowledge state
- Cohort-based pacing that is wrong for nearly every individual student
- Summative assessment that measures recall at arbitrary timestamps
- No persistent model of what a learner actually knows versus what they can perform under exam conditions
- No mechanism to detect the specific conceptual gap causing downstream failures

These are not pedagogical failures. They are engineering failures caused by operating without sufficient feedback resolution.

The result is a system that is structurally incapable of doing what it claims to do: produce durable, transferable understanding.

## Why AI Changes the Constraint

Large language models, combined with structured knowledge representation and adaptive algorithms, make the following possible for the first time at scale:

1. **Real-time learner modeling** — continuous inference of knowledge state from responses
2. **Socratic dialogue at scale** — dynamic question generation calibrated to the zone of proximal development
3. **Causal gap detection** — identifying which upstream concept is responsible for a downstream failure
4. **Curriculum synthesis** — generating learning sequences from a knowledge graph rather than a fixed syllabus
5. **Memory-optimal scheduling** — spacing review based on measured forgetting curves per concept per learner

None of these are speculative. Each component is implementable with current technology. What has been missing is a coherent system that integrates them.

## Why Existing Solutions Are Insufficient

| System | What It Does | What It Fails At |
|--------|--------------|-----------------|
| Khan Academy | Fixed video + exercise sequences | No dynamic adaptation; same path for every learner |
| Duolingo | Gamified spaced repetition | No deep conceptual modeling; surface-level retention |
| ChatGPT in education | Ad hoc tutoring | No persistent learner model; no curriculum structure; no memory |
| MOOCs | Scaled content delivery | Same failure mode as lecture: one-to-many with no feedback |
| Intelligent Tutoring Systems (ITS) | Rule-based adaptive instruction | Brittle; domain-specific; require massive manual authoring |

The gap is a system that combines: **structured knowledge representation + dynamic learner state + LLM-driven instruction + memory-optimal scheduling** as an integrated runtime.

## Why Open Source

Education infrastructure should not be a proprietary layer between learners and knowledge. The system's adaptation logic, knowledge graph schemas, assessment rubrics, and AI prompts should be auditable, forkable, and improvable by the community of researchers and engineers who care about this problem.

Closed systems cannot be trusted to optimize for learner outcomes when they are also optimizing for engagement metrics and subscription retention.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AXON RUNTIME                            │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │ Learner Model│◄──►│Knowledge Graph│◄──►│Curriculum Engine │  │
│  │              │    │              │    │                  │  │
│  │ - concept    │    │ - concepts   │    │ - path synthesis │  │
│  │   mastery    │    │ - prereqs    │    │ - lesson gen     │  │
│  │ - confidence │    │ - difficulty │    │ - gap targeting  │  │
│  │ - forgetting │    │ - relations  │    │                  │  │
│  └──────┬───────┘    └──────────────┘    └──────────────────┘  │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  AI Tutor    │◄──►│  Assessment  │◄──►│  Memory System   │  │
│  │  Engine      │    │  Engine      │    │                  │  │
│  │              │    │              │    │ - SM-2 variant   │  │
│  │ - dialogue   │    │ - rubrics    │    │ - forgetting     │  │
│  │ - scaffolding│    │ - eval       │    │   curve model    │  │
│  │ - Socratic   │    │ - feedback   │    │ - review sched.  │  │
│  └──────────────┘    └──────────────┘    └──────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Adaptation Engine                        │  │
│  │  Reads learner state → selects next action →             │  │
│  │  updates model → schedules memory consolidation          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                                           │
         ▼                                           ▼
  ┌─────────────┐                          ┌──────────────────┐
  │  REST API   │                          │  Frontend        │
  │  (FastAPI)  │                          │  (React/Vite)    │
  └─────────────┘                          └──────────────────┘
```

### Data Flow

```
Learner Input
     │
     ▼
Assessment Engine ──► rubric evaluation ──► concept mastery delta
     │
     ▼
Learner Model Update ──► forgetting curve recalibration
     │
     ▼
Adaptation Engine ──► next action decision
     │
     ├── IF review needed ──► Memory System ──► schedule review
     ├── IF gap detected  ──► Curriculum Engine ──► prerequisite path
     └── IF ready         ──► AI Tutor Engine ──► next concept dialogue
```

---

## Tech Stack

| Layer | Technology | Reason |
|-------|-----------|--------|
| API | FastAPI (Python) | Async, typed, OpenAPI auto-docs; Python ecosystem for AI |
| AI Engine | Anthropic Claude API | Best instruction-following; structured output support |
| Knowledge Graph | NetworkX + PostgreSQL | Graph traversal in memory; persistent storage |
| Learner State | PostgreSQL + Redis | Durable state + fast session cache |
| Spaced Repetition | Custom SM-2 variant | Standard algorithm, modified for concept-level not card-level |
| Frontend | React + Vite + TypeScript | Fast iteration; component model fits lesson/quiz structure |
| Auth | JWT + bcrypt | Minimal, real, replaceable |
| Deployment | Docker + docker-compose | Reproducible; cloud-agnostic |
| Testing | pytest + vitest | Ecosystem standard |

---

## Repository Structure

```
axon/
├── README.md
├── THESIS.md                    # Extended foundational argument
├── ARCHITECTURE.md              # Full system design documentation
├── CONTRIBUTING.md
├── LICENSE                      # MIT
│
├── backend/
│   ├── main.py                  # FastAPI application entry
│   ├── requirements.txt
│   ├── src/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── learner.py   # Learner profile endpoints
│   │   │   │   ├── session.py   # Learning session endpoints
│   │   │   │   ├── curriculum.py
│   │   │   │   ├── assessment.py
│   │   │   │   └── progress.py
│   │   │   └── middleware.py
│   │   ├── auth/
│   │   │   ├── jwt.py
│   │   │   └── models.py
│   │   ├── core/
│   │   │   ├── learner_model.py    # Dynamic cognitive profile
│   │   │   ├── curriculum_engine.py
│   │   │   ├── adaptation_engine.py
│   │   │   └── progress_tracker.py
│   │   ├── db/
│   │   │   ├── connection.py
│   │   │   ├── models.py           # SQLAlchemy models
│   │   │   └── repositories.py
│   │   └── services/
│   │       ├── learner_service.py
│   │       ├── session_service.py
│   │       └── analytics_service.py
│   └── tests/
│
├── ai/
│   ├── engine/
│   │   ├── tutor.py              # AI tutor orchestration
│   │   ├── evaluator.py          # Answer evaluation
│   │   └── generator.py          # Content generation
│   ├── prompts/
│   │   ├── tutor_system.py       # Tutor behavior prompts
│   │   ├── evaluator_system.py
│   │   └── generator_system.py
│   ├── memory/
│   │   ├── context_manager.py    # Learner context compression
│   │   └── session_memory.py
│   └── evaluation/
│       ├── rubric.py
│       └── hallucination_guard.py
│
├── learning/
│   ├── spaced_repetition/
│   │   ├── sm2.py               # SM-2 algorithm implementation
│   │   ├── forgetting_curve.py
│   │   └── scheduler.py
│   ├── knowledge_graph/
│   │   ├── graph.py             # Core graph operations
│   │   ├── traversal.py         # Path-finding algorithms
│   │   └── seeds/               # Domain knowledge graphs
│   │       ├── mathematics.json
│   │       └── programming.json
│   ├── adaptation/
│   │   ├── decision_engine.py   # What to teach next
│   │   └── weakness_detector.py
│   └── assessment/
│       ├── rubric_engine.py
│       └── question_generator.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Onboarding.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Lesson.tsx
│   │   │   ├── Quiz.tsx
│   │   │   └── Progress.tsx
│   │   ├── components/
│   │   │   ├── TutorChat.tsx
│   │   │   ├── ConceptMap.tsx
│   │   │   ├── ProgressBar.tsx
│   │   │   └── MasteryGrid.tsx
│   │   ├── hooks/
│   │   │   ├── useLearnerState.ts
│   │   │   └── useSession.ts
│   │   └── store/
│   │       └── learner.ts
│
├── data/
│   ├── schemas/
│   │   ├── learner.json
│   │   ├── knowledge_graph.json
│   │   ├── lesson.json
│   │   └── assessment.json
│   └── migrations/
│
└── devops/
    ├── docker/
    │   ├── Dockerfile.backend
    │   ├── Dockerfile.frontend
    │   └── docker-compose.yml
    └── scripts/
        ├── setup.sh
        └── seed_knowledge_graph.py
```

---

## Quickstart

### Prerequisites
- Docker + docker-compose
- Anthropic API key

### Run

```bash
git clone https://github.com/your-org/axon
cd axon

cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

docker-compose up --build

# Seed initial knowledge graph
docker-compose exec backend python devops/scripts/seed_knowledge_graph.py

# Frontend: http://localhost:5173
# API:      http://localhost:8000
# Docs:     http://localhost:8000/docs
```

### Local Development (without Docker)

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

---

## Core API Endpoints

```
POST   /auth/register
POST   /auth/login

GET    /learner/{id}/profile
PUT    /learner/{id}/profile
GET    /learner/{id}/mastery
GET    /learner/{id}/schedule       # What to review today

POST   /session/start
POST   /session/{id}/respond        # Submit answer/response
GET    /session/{id}/next           # Get next action
POST   /session/{id}/end

GET    /curriculum/path/{learner_id}/{goal_concept}
POST   /curriculum/generate

POST   /assessment/evaluate
GET    /progress/{learner_id}/summary
GET    /progress/{learner_id}/concepts
```

---

## Extending Axon

### Add a Knowledge Domain

Create a JSON knowledge graph in `learning/knowledge_graph/seeds/`:

```json
{
  "domain": "linear_algebra",
  "concepts": [
    {
      "id": "vector_spaces",
      "name": "Vector Spaces",
      "difficulty": 0.6,
      "prerequisites": ["sets", "real_numbers", "functions"]
    }
  ],
  "edges": [
    { "from": "real_numbers", "to": "vector_spaces", "type": "prerequisite" }
  ]
}
```

Then run: `python devops/scripts/seed_knowledge_graph.py --domain linear_algebra`

### Modify Tutor Behavior

Edit `ai/prompts/tutor_system.py`. The tutor prompt is structured, versioned, and separated from engine logic so it can be changed, A/B tested, or domain-specialized without touching the orchestration layer.

### Replace the AI Provider

The AI engine is abstracted behind `ai/engine/tutor.py`. Replace the Anthropic client call with any provider that supports structured output and system prompts. The interface contract is defined in `ai/engine/base.py`.

### Custom Adaptation Logic

Override `learning/adaptation/decision_engine.py`. The decision engine receives the full learner state and returns an `AdaptationDecision` — what to do next and why. The default logic is documented and replaceable.

---

## Research Directions

This system is intentionally incomplete in several areas where open research questions exist:

- **Knowledge graph authoring at scale** — manual graph construction is the current bottleneck; automated extraction from curricula is unsolved
- **Mastery threshold calibration** — what confidence score constitutes "mastered" varies by domain and stakes; needs empirical grounding
- **Long-horizon learner modeling** — current model is session-scoped; persistence across months requires forgetting curve research
- **Multi-modal assessment** — current system is text-only; mathematical reasoning, code execution, and visual domains require extension
- **Hallucination in instructional context** — LLM errors in education are qualitatively different from other domains; mitigation strategies are underspecified

Contributors interested in any of these directions: see CONTRIBUTING.md.

---

## License

MIT. The knowledge graphs, schemas, and system design are explicitly in the public domain. Build on this.

---

## Contributing

See CONTRIBUTING.md. The highest-value contributions are:
1. Knowledge graph expansions (new domains)
2. Improvements to the adaptation decision engine
3. Assessment rubric quality
4. Empirical validation of learning outcomes

This work focuses on infrastructure research rather than feature development.
