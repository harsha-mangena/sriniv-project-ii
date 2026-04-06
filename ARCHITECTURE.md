# InterviewPilot — System Architecture & Design Document

## Project Codename: InterviewPilot
### A Free, Open-Source AI Interview Coach for Mac Silicon
### Powered by Atom of Thoughts + Tree of Thoughts Hybrid Reasoning

---

## 1. Vision & Philosophy

InterviewPilot is a **100% free, locally-running** AI interview preparation and real-time meeting assistant for macOS (Apple Silicon). It uses a novel hybrid reasoning engine combining **Atom of Thoughts (AoT)** for atomic skill decomposition and evaluation, with **Tree of Thoughts (ToT)** for strategic question planning and adaptive learning paths.

**Core Principles:**
- **Zero cloud cost** — All AI runs locally via Ollama + open-source models
- **Privacy-first** — No data leaves the machine
- **Research-grounded** — AoT (NeurIPS 2025) + ToT (NeurIPS 2023) reasoning
- **Mac-native** — Built for Apple Silicon with Tauri 2 (Rust + Web UI)

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        InterviewPilot App                          │
│                     (Tauri 2 — Rust + React)                       │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    React Frontend (UI)                       │   │
│  │                                                              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────┐  │   │
│  │  │ Dashboard │ │ Mock     │ │ Real-Time │ │  Analytics   │  │   │
│  │  │ (Upload  │ │ Interview│ │ Meeting   │ │  (Progress   │  │   │
│  │  │  Resume/ │ │ (Chat +  │ │ Assistant │ │   Charts,    │  │   │
│  │  │  JD)     │ │  Voice)  │ │ (Overlay) │ │   Heatmap)   │  │   │
│  │  └──────────┘ └──────────┘ └───────────┘ └──────────────┘  │   │
│  └───────────────────────┬──────────────────────────────────────┘   │
│                          │ Tauri IPC (invoke commands)              │
│  ┌───────────────────────▼──────────────────────────────────────┐   │
│  │                   Rust Backend (Tauri)                       │   │
│  │                                                              │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐  │   │
│  │  │ Document     │ │ Audio        │ │ Window Manager     │  │   │
│  │  │ Parser       │ │ Capture      │ │ (Overlay Control)  │  │   │
│  │  │ (PDF/Text)   │ │ (SCKit)      │ │                    │  │   │
│  │  └──────┬───────┘ └──────┬───────┘ └────────────────────┘  │   │
│  └─────────┼────────────────┼──────────────────────────────────┘   │
│            │                │                                       │
│  ┌─────────▼────────────────▼──────────────────────────────────┐   │
│  │              Python AI Engine (FastAPI)                      │   │
│  │              localhost:8000                                  │   │
│  │                                                              │   │
│  │  ┌─────────────────────────────────────────────────────┐    │   │
│  │  │            Hybrid Reasoning Engine                   │    │   │
│  │  │                                                     │    │   │
│  │  │  ┌─────────────────┐  ┌──────────────────────┐     │    │   │
│  │  │  │  ToT Strategic  │  │  AoT Tactical Layer  │     │    │   │
│  │  │  │  Layer          │  │                      │     │    │   │
│  │  │  │  • Question     │  │  • Atomic Decompose  │     │    │   │
│  │  │  │    Tree Planner │  │  • Per-Atom Evaluate │     │    │   │
│  │  │  │  • Branch/      │  │  • Markov Contract   │     │    │   │
│  │  │  │    Backtrack    │  │  • Skill Atom Track  │     │    │   │
│  │  │  └─────────────────┘  └──────────────────────┘     │    │   │
│  │  └─────────────────────────────────────────────────────┘    │   │
│  │                                                              │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐  │   │
│  │  │ RAG Pipeline │ │ Resume/JD    │ │ Session Manager    │  │   │
│  │  │ (LlamaIndex) │ │ Analyzer     │ │ (SQLite + Vector)  │  │   │
│  │  └──────────────┘ └──────────────┘ └────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Ollama (Local LLM)                        │   │
│  │                    localhost:11434                            │   │
│  │                                                              │   │
│  │  • qwen3:8b (main reasoning)                                │   │
│  │  • nomic-embed-text (embeddings)                            │   │
│  │  • whisper via whisper.cpp (STT)                            │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Data Layer                                │   │
│  │                                                              │   │
│  │  • SQLite (sessions, profiles, metrics, history)            │   │
│  │  • ChromaDB (vector embeddings for RAG)                     │   │
│  │  • File System (uploaded PDFs, audio recordings)            │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Tech Stack Justification

| Layer | Choice | Why | License |
|-------|--------|-----|---------|
| **Desktop Shell** | Tauri 2 (Rust) | 10x smaller than Electron, 50% less RAM, native macOS API access via Rust FFI | MIT |
| **Frontend** | React + TypeScript + Tailwind | Fast iteration, rich ecosystem, easy to find contributors | MIT |
| **AI Backend** | Python FastAPI | Best ML/AI ecosystem, async, easy Ollama integration | MIT |
| **LLM Runtime** | Ollama | One-command setup, OpenAI-compatible API, auto Metal GPU | MIT |
| **LLM Model** | qwen3:8b | Best reasoning per parameter, Apache-2.0, 16GB RAM | Apache-2.0 |
| **Embeddings** | nomic-embed-text | 768-dim, 8192 context, most popular on Ollama | Apache-2.0 |
| **Vector DB** | ChromaDB | Zero-config, Python-native, perfect for local RAG | Apache-2.0 |
| **RAG Framework** | LlamaIndex | 40% faster retrieval than LangChain for doc Q&A | MIT |
| **STT** | faster-whisper | Python-native, CTranslate2 backend, good Mac perf | MIT |
| **TTS** | Kokoro / macOS `say` | Free, offline, fast | Apache-2.0 |
| **Database** | SQLite | Zero-config, file-based, perfect for desktop app | Public Domain |
| **PDF Parsing** | PyMuPDF (fitz) | Fast, accurate PDF text extraction | AGPL/Commercial |

---

## 4. Hybrid AoT+ToT Reasoning Engine Design

### 4.1 The Two-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SESSION CONTROLLER                        │
│         Orchestrates the interview flow                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────▼───────────────┐
        │     ToT STRATEGIC LAYER       │
        │                               │
        │  Question Tree:               │
        │   Root: "SDE Interview"       │
        │   ├── Behavioral              │
        │   │   ├── Leadership          │
        │   │   ├── Conflict            │
        │   │   └── Teamwork            │
        │   ├── Technical               │
        │   │   ├── DSA                 │
        │   │   ├── System Design       │
        │   │   └── Coding             │
        │   └── Role-Specific           │
        │       ├── SQL                 │
        │       └── Domain Knowledge    │
        │                               │
        │  Search: BFS across topics    │
        │  Evaluate: LLM scores each    │
        │  Backtrack: if too easy/hard  │
        └───────────────┬───────────────┘
                        │ selected question
        ┌───────────────▼───────────────┐
        │     AoT TACTICAL LAYER        │
        │                               │
        │  For selected question:       │
        │  1. DECOMPOSE into DAG of     │
        │     atomic evaluation units   │
        │  2. Present question to user  │
        │  3. EVALUATE answer per atom  │
        │  4. CONTRACT: generate        │
        │     follow-up targeting       │
        │     failed atoms only         │
        │  5. Update skill profile      │
        └───────────────┬───────────────┘
                        │ atom scores
        ┌───────────────▼───────────────┐
        │     SKILL PROFILE TRACKER     │
        │                               │
        │  Atom Heatmap:                │
        │  ┌─────────┬──────┬────────┐  │
        │  │ Skill   │Score │Attempts│  │
        │  ├─────────┼──────┼────────┤  │
        │  │ DFS     │ 0.9  │   3    │  │
        │  │ BFS     │ 0.4  │   2    │  │
        │  │ DP      │ 0.0  │   0    │  │
        │  │ STAR    │ 0.7  │   5    │  │
        │  └─────────┴──────┴────────┘  │
        │                               │
        │  Feeds back into ToT layer    │
        │  to select next question      │
        └───────────────────────────────┘
```

### 4.2 Data Flow for One Interview Cycle

```
Step 1: ToT selects question branch
  Input:  skill_profile + question_tree + session_goals
  Output: selected_question = "Design a distributed cache"
  Method: BFS over question tree, LLM evaluates informativeness
          of each frontier node for this candidate

Step 2: AoT decomposes question into atoms
  Input:  selected_question
  Output: evaluation_dag = {
    "atom_0": {"label": "Requirements gathering", "deps": []},
    "atom_1": {"label": "Data structure choice", "deps": []},
    "atom_2": {"label": "Eviction policy", "deps": ["atom_1"]},
    "atom_3": {"label": "Consistency model", "deps": ["atom_0"]},
    "atom_4": {"label": "Distributed coordination", "deps": ["atom_2", "atom_3"]},
    "atom_5": {"label": "Failure handling", "deps": ["atom_4"]}
  }

Step 3: Present question, receive answer

Step 4: AoT evaluates answer atom-by-atom
  For each independent atom (no deps): score against answer
  For each dependent atom: score using resolved dep context
  Output: {
    "atom_0": {"score": 0.9, "feedback": "Good requirements"},
    "atom_1": {"score": 0.8, "feedback": "HashMap good, consider trie"},
    "atom_2": {"score": 0.3, "feedback": "Missed LRU/LFU tradeoff"},
    "atom_3": {"score": 0.7, "feedback": "Eventual consistency noted"},
    "atom_4": {"score": 0.2, "feedback": "No mention of consensus"},
    "atom_5": {"score": 0.0, "feedback": "Not addressed"}
  }

Step 5: AoT contracts to follow-up
  Failed atoms: [atom_2, atom_4, atom_5]
  Contract: "You mentioned using a HashMap for the cache. Can you
   explain how you would handle eviction when memory is full, and
   how multiple cache nodes would stay consistent?"
  (This targets exactly the failed atoms, ignoring passed ones)

Step 6: Update skill profile + ToT decides next move
  If atom_precision < 0.5: ToT backtracks to prerequisite topic
  If atom_precision 0.5-0.85: continue follow-ups on same topic
  If atom_precision > 0.85: ToT advances to harder branch
```

---

## 5. Directory Structure

```
sriniv-project-ii/
├── README.md
├── ARCHITECTURE.md
├── LICENSE (MIT)
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── backend/                          # Python FastAPI AI Engine
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── main.py                       # FastAPI app entry point
│   ├── config.py                     # Settings & environment
│   │
│   ├── api/                          # API Routes
│   │   ├── __init__.py
│   │   ├── router.py                 # Main API router
│   │   ├── documents.py              # Resume/JD upload & parse
│   │   ├── interview.py              # Interview session endpoints
│   │   ├── questions.py              # Question generation
│   │   ├── evaluation.py             # Answer evaluation
│   │   ├── analytics.py              # Performance analytics
│   │   └── realtime.py               # WebSocket for real-time mode
│   │
│   ├── core/                         # Core AI Engine
│   │   ├── __init__.py
│   │   ├── llm.py                    # Ollama LLM wrapper
│   │   ├── embeddings.py             # Embedding generation
│   │   ├── rag.py                    # RAG pipeline (LlamaIndex)
│   │   └── stt.py                    # Speech-to-text (faster-whisper)
│   │
│   ├── reasoning/                    # AoT + ToT Hybrid Engine
│   │   ├── __init__.py
│   │   ├── atom_of_thoughts.py       # AoT: decompose, evaluate, contract
│   │   ├── tree_of_thoughts.py       # ToT: question tree, BFS/DFS, evaluate
│   │   ├── hybrid_engine.py          # Combined AoT+ToT orchestrator
│   │   ├── skill_atoms.py            # Skill atom taxonomy & registry
│   │   └── adaptive_controller.py    # Difficulty adaptation logic
│   │
│   ├── parsers/                      # Document Parsing
│   │   ├── __init__.py
│   │   ├── resume_parser.py          # Extract skills, experience, projects
│   │   └── jd_parser.py              # Extract requirements, keywords
│   │
│   ├── analysis/                     # Analysis Engines
│   │   ├── __init__.py
│   │   ├── skill_gap.py              # Skill gap analysis
│   │   ├── match_scoring.py          # Resume-JD match scoring
│   │   └── profile_builder.py        # User learning profile
│   │
│   ├── models/                       # Data Models (Pydantic)
│   │   ├── __init__.py
│   │   ├── schemas.py                # Request/response schemas
│   │   ├── session.py                # Interview session models
│   │   └── profile.py                # User profile models
│   │
│   ├── db/                           # Database Layer
│   │   ├── __init__.py
│   │   ├── database.py               # SQLite connection & init
│   │   ├── vector_store.py           # ChromaDB operations
│   │   └── migrations.py             # Schema migrations
│   │
│   └── data/                         # Static Data
│       ├── skill_taxonomy.json       # Predefined skill atoms
│       ├── question_templates.json   # Question template library
│       └── rubrics.json              # Evaluation rubrics
│
├── frontend/                         # React + TypeScript UI
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   │
│   ├── src/
│   │   ├── main.tsx                  # React entry
│   │   ├── App.tsx                   # Root app + routing
│   │   │
│   │   ├── components/               # Reusable Components
│   │   │   ├── Layout.tsx            # Main layout wrapper
│   │   │   ├── Sidebar.tsx           # Navigation sidebar
│   │   │   ├── FileUpload.tsx        # Resume/JD upload
│   │   │   ├── ChatBubble.tsx        # Interview chat messages
│   │   │   ├── SkillHeatmap.tsx      # Skill atom heatmap
│   │   │   ├── ProgressChart.tsx     # Progress over time
│   │   │   ├── ScoreCard.tsx         # Individual score display
│   │   │   └── OverlayPanel.tsx      # Real-time overlay component
│   │   │
│   │   ├── pages/                    # Page Components
│   │   │   ├── Dashboard.tsx         # Home dashboard
│   │   │   ├── PrepMode.tsx          # Pre-meeting preparation
│   │   │   ├── MockInterview.tsx     # Interactive mock interview
│   │   │   ├── Analytics.tsx         # Performance analytics
│   │   │   ├── Settings.tsx          # App settings
│   │   │   └── RealTimeAssist.tsx    # Real-time meeting mode
│   │   │
│   │   ├── hooks/                    # Custom React Hooks
│   │   │   ├── useInterview.ts       # Interview session management
│   │   │   ├── useApi.ts            # API communication
│   │   │   └── useAudio.ts           # Audio recording
│   │   │
│   │   ├── stores/                   # State Management (Zustand)
│   │   │   ├── sessionStore.ts       # Current session state
│   │   │   ├── profileStore.ts       # User profile state
│   │   │   └── settingsStore.ts      # App settings
│   │   │
│   │   ├── services/                 # API Service Layer
│   │   │   ├── api.ts               # Base API client
│   │   │   ├── interviewService.ts   # Interview API calls
│   │   │   └── documentService.ts    # Document upload/parse
│   │   │
│   │   └── styles/                   # Styles
│   │       └── globals.css           # Tailwind + custom styles
│   │
│   └── public/
│       └── favicon.ico
│
├── src-tauri/                        # Tauri Rust Backend
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── build.rs
│   ├── src/
│   │   ├── main.rs                   # Tauri entry point
│   │   ├── commands.rs               # Tauri IPC commands
│   │   └── lib.rs
│   └── icons/
│
├── scripts/                          # Setup & utility scripts
│   ├── setup.sh                      # One-command setup
│   ├── install_ollama.sh             # Install Ollama + models
│   └── dev.sh                        # Start all services
│
└── tests/                            # Tests
    ├── test_reasoning.py             # AoT+ToT engine tests
    ├── test_parsers.py               # Parser tests
    ├── test_api.py                   # API endpoint tests
    └── test_analysis.py              # Analysis tests
```

---

## 6. Feature Specification

### 6.1 Resume + Job Description Intelligence

**Input:** PDF or text resume + job description text
**Processing Pipeline:**
1. PDF → text extraction (PyMuPDF)
2. LLM-powered structured extraction:
   - Resume: skills[], experience[], projects[], achievements[], education[]
   - JD: requirements[], responsibilities[], keywords[], nice_to_have[]
3. Embedding generation (nomic-embed-text) → stored in ChromaDB
4. Skill gap analysis: resume_skills ∩ jd_requirements → gap report
5. Match score: weighted overlap percentage

### 6.2 Question Generation Engine (ToT-Powered)

**Question Types:**
- Behavioral (STAR format)
- Technical (DSA, coding)
- System Design
- SQL / Data Engineering
- Role-specific (based on JD)

**ToT Question Tree Construction:**
1. Parse JD → extract competency categories
2. For each category, generate question tree with BFS branching
3. Each node: {question, difficulty, target_skills, evaluation_atoms}
4. Evaluate nodes using LLM scoring: "informativeness for this candidate"
5. Select top-k paths personalized to candidate's skill profile

### 6.3 Iterative Interview Training Loop (AoT-Powered)

```
User starts session → ToT selects first question
  → User answers (text or voice)
  → AoT decomposes ideal answer into atoms
  → AoT scores each atom against user's answer
  → Generates detailed feedback per atom
  → AoT contracts failed atoms into follow-up question
  → Loop continues until topic mastered or moved
  → ToT decides: go deeper, go broader, or backtrack
```

### 6.4 Pre-Meeting Preparation Mode

**Input:** Resume + JD
**Output:**
- Top 30-50 likely questions (prioritized by ToT)
- Personalized model answers (RAG-enhanced with resume context)
- Talking points per question
- Weakness analysis (skill gap heatmap)
- Quick 10-question rapid mock interview

### 6.5 Real-Time Meeting Assistant

**Architecture:**
- ScreenCaptureKit → captures system audio from Zoom/Teams
- faster-whisper → live transcription
- Question detection → RAG query → LLM generates suggestion
- Floating overlay window (always-on-top, transparent)
- Hotkey toggle (Cmd+Shift+I)

### 6.6 Analytics Dashboard

- Session history with scores over time
- Skill atom heatmap (color-coded mastery)
- Confidence score trending
- Weak area drill-down
- Time-per-answer metrics
- Progress toward interview readiness

---

## 7. API Design

### Endpoints

```
POST   /api/documents/upload          # Upload resume/JD
POST   /api/documents/parse           # Parse uploaded document
GET    /api/documents/{id}            # Get parsed document

POST   /api/interview/start           # Start interview session
POST   /api/interview/answer          # Submit answer
POST   /api/interview/next            # Get next question
GET    /api/interview/session/{id}    # Get session details
POST   /api/interview/end             # End session

POST   /api/prep/generate             # Generate prep materials
GET    /api/prep/{session_id}         # Get prep results

POST   /api/evaluate/answer           # Evaluate a single answer
GET    /api/evaluate/atoms/{qid}      # Get atom breakdown

GET    /api/analytics/profile         # Get user profile
GET    /api/analytics/heatmap         # Get skill heatmap
GET    /api/analytics/history         # Get session history
GET    /api/analytics/progress        # Get progress metrics

WS     /api/realtime/stream           # WebSocket for real-time mode

GET    /api/health                    # Health check
```

---

## 8. Database Schema

```sql
-- User profile
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Uploaded documents
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    type TEXT CHECK(type IN ('resume', 'job_description')),
    raw_text TEXT,
    parsed_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Interview sessions
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    resume_id TEXT REFERENCES documents(id),
    jd_id TEXT REFERENCES documents(id),
    mode TEXT CHECK(mode IN ('mock', 'prep', 'realtime')),
    status TEXT DEFAULT 'active',
    overall_score REAL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP
);

-- Questions asked in sessions
CREATE TABLE questions (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id),
    question_text TEXT,
    question_type TEXT,
    difficulty INTEGER,
    target_skills JSON,
    evaluation_atoms JSON,
    sequence_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User answers
CREATE TABLE answers (
    id TEXT PRIMARY KEY,
    question_id TEXT REFERENCES questions(id),
    session_id TEXT REFERENCES sessions(id),
    answer_text TEXT,
    atom_scores JSON,
    overall_score REAL,
    feedback TEXT,
    follow_up_question TEXT,
    time_taken_seconds REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Skill atom tracking
CREATE TABLE skill_atoms (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    atom_id TEXT,
    atom_label TEXT,
    category TEXT,
    cumulative_score REAL DEFAULT 0,
    attempt_count INTEGER DEFAULT 0,
    last_assessed TIMESTAMP,
    UNIQUE(user_id, atom_id)
);

-- Prep materials generated
CREATE TABLE prep_materials (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id),
    questions JSON,
    talking_points JSON,
    weakness_analysis JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 9. Setup & Run

```bash
# 1. Clone
git clone https://github.com/harsha-mangena/sriniv-project-ii.git
cd sriniv-project-ii

# 2. Run setup script (installs everything)
chmod +x scripts/setup.sh
./scripts/setup.sh

# 3. Start development
./scripts/dev.sh
```

**Prerequisites:**
- macOS 12.3+ (Apple Silicon: M1/M2/M3/M4)
- Python 3.11+
- Node.js 18+
- Rust (installed via rustup)
- Ollama (installed via setup script)

---

## 10. License

MIT License — completely free and open source.
