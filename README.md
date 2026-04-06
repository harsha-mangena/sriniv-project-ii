# InterviewPilot

**A free, open-source AI interview coach for macOS, powered by Atom of Thoughts + Tree of Thoughts hybrid reasoning.**

InterviewPilot helps you prepare for technical interviews with an intelligent system that adapts to your skill level in real time. It runs 100% locally on your Mac — no cloud APIs, no data leaves your machine.

## Key Innovation: AoT + ToT Hybrid Reasoning

InterviewPilot combines two cutting-edge LLM reasoning methodologies:

- **Tree of Thoughts (ToT)** ([Yao et al., NeurIPS 2023](https://arxiv.org/abs/2305.10601)) — Strategic layer that navigates a question tree using BFS/DFS, evaluates which topic to probe next, and backtracks when difficulty is mismatched.

- **Atom of Thoughts (AoT)** ([Teng et al., NeurIPS 2025](https://arxiv.org/abs/2502.12018)) — Tactical layer that decomposes each question into atomic evaluation units (DAGs), scores your answer per-atom, and generates targeted follow-ups via Markov contraction.

The result: every question is personalized, every answer is evaluated at granular depth, and the system continuously adapts to focus on your weak areas.

## Features

### Resume + JD Intelligence
- Upload resume (PDF or text) and job description
- LLM-powered structured extraction (skills, experience, projects)
- Skill gap analysis with match scoring

### Mock Interview Mode
- Interactive chat-based interview with AI interviewer
- Atom-by-atom answer evaluation with detailed feedback
- Adaptive difficulty that increases/decreases based on performance
- Follow-up questions targeting exactly what you missed (AoT contraction)

### Pre-Meeting Preparation
- Generate 30-50 personalized questions based on your resume and JD
- Model answers tailored to your background
- Talking points and weakness analysis

### Real-Time Meeting Assistant
- WebSocket-based live transcription
- Question detection with context-aware suggestions
- Floating overlay panel for during-meeting hints

### Analytics Dashboard
- Skill atom heatmap showing mastery across categories
- Progress charts over time
- Weak areas identification with study recommendations

## Tech Stack (100% Free & Open Source)

| Layer | Technology | License |
|-------|-----------|---------|
| Desktop Shell | Tauri 2 (Rust) | MIT |
| Frontend | React + TypeScript + Tailwind | MIT |
| AI Backend | Python FastAPI | MIT |
| LLM Runtime | Ollama (Metal GPU) | MIT |
| LLM Model | Qwen3 8B | Apache-2.0 |
| Embeddings | nomic-embed-text | Apache-2.0 |
| Vector DB | ChromaDB | Apache-2.0 |
| Database | SQLite | Public Domain |
| STT | faster-whisper | MIT |

**Total recurring cost: $0**

## Prerequisites

- macOS 12.3+ (Apple Silicon: M1/M2/M3/M4)
- 16GB RAM recommended (8GB minimum with smaller model)
- Python 3.11+
- Node.js 18+
- ~10GB disk space for models

## Quick Start

```bash
# Clone the repo
git clone https://github.com/harsha-mangena/sriniv-project-ii.git
cd sriniv-project-ii

# Run one-command setup (installs Ollama, models, dependencies)
chmod +x scripts/setup.sh
./scripts/setup.sh

# Start development servers
./scripts/dev.sh
```

Then open http://localhost:5173 in your browser.

## Manual Setup

### 1. Install Ollama
```bash
brew install ollama
ollama serve &
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

### 2. Setup Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Setup Frontend
```bash
cd frontend
npm install
npm run dev
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│          React Frontend (Tauri Shell)            │
│  Dashboard │ Mock Interview │ Prep │ Analytics   │
└─────────────────────┬───────────────────────────┘
                      │ REST API / WebSocket
┌─────────────────────▼───────────────────────────┐
│             Python FastAPI Backend               │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │         Hybrid Reasoning Engine             │ │
│  │  ToT Strategic Layer ←→ AoT Tactical Layer  │ │
│  │  (Question Selection)   (Answer Evaluation) │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  RAG Pipeline │ Parsers │ Analytics │ Sessions    │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│  Ollama (localhost:11434)  │  SQLite  │  ChromaDB│
│  qwen3:8b + nomic-embed   │  Sessions│  Vectors │
└─────────────────────────────────────────────────┘
```

## API Documentation

Once running, visit http://localhost:8000/docs for the interactive Swagger API documentation.

Key endpoints:
- `POST /api/documents/upload` — Upload resume/JD
- `POST /api/interview/start` — Start mock interview
- `POST /api/interview/answer` — Submit and evaluate answer
- `POST /api/questions/generate-prep` — Generate prep questions
- `GET /api/analytics/profile` — Get learning profile
- `WS /api/realtime/stream` — Real-time meeting assistant

## Research References

1. Teng, F., et al. (2025). *Atom of Thoughts for Markov LLM Test-Time Scaling*. NeurIPS 2025. [arXiv:2502.12018](https://arxiv.org/abs/2502.12018)
2. Yao, S., et al. (2023). *Tree of Thoughts: Deliberate Problem Solving with Large Language Models*. NeurIPS 2023. [arXiv:2305.10601](https://arxiv.org/abs/2305.10601)

## Contributing

Contributions welcome. Please open an issue first to discuss what you'd like to change.

## License

[MIT](LICENSE) — completely free and open source.
