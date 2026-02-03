<p align="center">
  <h1 align="center">🔮 Prismatic Engine</h1>
  <p align="center"><strong>AI-Powered Content Generation Pipeline for Instagram</strong></p>
  <p align="center">
    <em>Transform raw content into viral-ready Reels, Carousels, and Quotes with a 7-stage LLM pipeline</em>
  </p>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"></a>
  <a href="https://www.postgresql.org/"><img src="https://img.shields.io/badge/PostgreSQL-14+-336791?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"></a>
  <a href="https://openai.com/"><img src="https://img.shields.io/badge/OpenAI-GPT--4-412991?style=for-the-badge&logo=openai&logoColor=white" alt="OpenAI GPT-4"></a>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-how-it-works">How It Works</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-api-reference">API</a> •
  <a href="docs/PRISMATIC_ENGINE_DOCUMENTATION.md">Documentation</a>
</p>

---

## ✨ What is Prismatic Engine?

Prismatic Engine is a **5-phase content automation pipeline** that harvests raw material from Reddit, books, and blogs, then transforms it into **Instagram-ready content** through sophisticated LLM analysis, strategic scheduling, and multi-stage generation.

```
📥 Ingestion → 🏷️ Classification → 📅 Strategy → ✍️ Creation → 📤 Delivery
```

> **No more content fatigue.** Prismatic extracts atomic insights, applies anti-repetition rules, and generates content that's optimized for scroll-stopping power, shareability, and retention.

---

## 🚀 Features

### 📊 **Intelligent Content Pipeline**
| Phase | What It Does |
|-------|-------------|
| **🌐 Ingestion** | Harvest from Reddit, PDFs (books), and blogs with quality filtering |
| **🧠 Classification** | LLM extracts atomic components, assigns pillars, and scores virality |
| **📅 Strategy** | Generate 21-slot weekly schedules with diversity scoring (Shannon entropy) |
| **✍️ Creation** | 7-stage pipeline produces retention-optimized content |
| **📤 Delivery** | Export to Markdown and Telegram for review |

### 🎯 **8 Content Pillars**
```
💔 RELATIONSHIPS     🧠 SELF_AWARENESS     ⚡ PRODUCTIVITY     🌑 DARK_PSYCHOLOGY
💰 MONEY_MINDSET     🔥 MOTIVATION         🎭 SOCIAL_DYNAMICS  🧘 MENTAL_HEALTH
```

### 🎭 **4 Voice Modes (Manson Protocol)**
| Mode | Purpose | Energy |
|------|---------|--------|
| 🔥 **ROAST_MASTER** | Direct call-out, behavior naming | High |
| 🪞 **MIRROR** | Recognition, "being seen" energy | Medium |
| 🔮 **ORACLE** | Mechanism reveal, truth delivery | Variable |
| 🔪 **SURGEON** | Tactical precision, no fluff | Low-Medium |

### 🛡️ **Anti-Repetition Engine**
- **6-week atom cooldown** — Same content can't repeat
- **12-week atom+angle cooldown** — Same combination blocked
- **Pillar saturation limit (40%)** — Balanced content distribution
- **Shannon entropy scoring** — Diversity optimization

### 📈 **Retention Architecture**
- Hook implementation (<3 seconds)
- Screenshot line isolation
- Open loop endings (no closure)
- Breath point architecture
- Swipe trigger chains (Carousels)

---

## 🔧 How It Works

### The 7-Stage Creation Pipeline

```mermaid
flowchart LR
    A[📖 Stage 1<br>Analyze] --> B[🎯 Stage 2<br>Target]
    B --> C[🦴 Stage 2.5<br>Skeleton]
    C --> D[✍️ Stage 3<br>Generate]
    D --> E[🔍 Stage 3.5<br>Coherence]
    E --> F[⚖️ Stage 4<br>Critique]
    F --> G[💾 Stage 5<br>Storage]
```

| Stage | Purpose |
|-------|---------|
| **Stage 1** | Extract psychological core (core truth + counter-truth) |
| **Stage 2** | Design mode sequence and emotional arc (Manson Protocol) |
| **Stage 2.5** | Build structural skeleton with tension/resolution chains |
| **Stage 3** | Generate format-specific content following skeleton |
| **Stage 3.5** | Audit coherence AND retention mechanics |
| **Stage 4** | Self-critique with 7-criteria evaluation + rewrite loop |
| **Stage 5** | Run hard filters and store approved content |

### Content Formats

| Format | Output | Optimization |
|--------|--------|--------------|
| 🎬 **Reels** | 15-60s scripts with hook, body, punch line | Re-engagement at 10-15s, breath points |
| 🎠 **Carousels** | 6-10 slides with swipe triggers | Slide 1 incompleteness, save triggers |
| 💬 **Quotes** | 1-3 sentence + caption | Standalone power, visual rhythm |

---

## ⚡ Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- OpenAI API key

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/prismatic-engine.git
cd prismatic-engine

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys:
#   OPENAI_API_KEY=sk-...
#   DATABASE_URL=postgresql://user:pass@localhost/prismatic

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

### First Run

```bash
# 1. Ingest content from Reddit
curl -X POST http://localhost:8000/ingestion/reddit

# 2. Classify into content atoms
curl -X POST http://localhost:8000/classification/batch

# 3. Generate weekly schedule
curl -X POST http://localhost:8000/strategy/generate-week

# 4. Run creation pipeline
curl -X POST http://localhost:8000/creation/run-pipeline

# 5. Export to Markdown
curl -X POST http://localhost:8000/delivery/export
```

---

## 📚 API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ingestion/reddit` | Harvest Reddit posts from configured subreddits |
| `POST` | `/ingestion/reservoir` | Transfer content from book/blog reservoir |
| `POST` | `/classification/batch` | Classify raw content into atoms (LLM) |
| `POST` | `/strategy/generate-week` | Generate 21-slot weekly schedule |
| `POST` | `/creation/run-pipeline` | Run 7-stage creation pipeline |
| `POST` | `/delivery/export` | Export to Markdown/Telegram |

### Schedule Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/strategy/schedule/{week}` | Get schedule for a specific week |
| `DELETE` | `/strategy/schedule/{week}` | Delete week's schedule |
| `POST` | `/strategy/schedule/{week}/reset` | Reset schedule status to SCHEDULED |

### Content Lifecycle

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/atoms` | List content atoms with filtering |
| `GET` | `/atoms/{id}` | Get specific atom details |
| `GET` | `/generated/{schedule_id}` | Get generated content for slot |

---

## 🏗️ Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRISMATIC ENGINE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐ │
│  │  Reddit  │    │   PDF    │    │   Blog   │    │ YouTube  │    │ Future │ │
│  │   API    │    │  Books   │    │ Articles │    │Transcripts│   │Sources │ │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘    └───┬────┘ │
│       │               │               │               │              │      │
│       └───────────────┴───────┬───────┴───────────────┴──────────────┘      │
│                               ▼                                              │
│                    ┌─────────────────────┐                                   │
│                    │    RAW_INGEST       │  Phase 1: Ingestion               │
│                    │   (Staging Table)   │                                   │
│                    └──────────┬──────────┘                                   │
│                               ▼                                              │
│                    ┌─────────────────────┐                                   │
│                    │   CONTENT_ATOMS     │  Phase 2: Classification          │
│                    │ (Atomic Components) │  └─ LLM: The Librarian            │
│                    └──────────┬──────────┘                                   │
│                               ▼                                              │
│      ┌──────────────┬─────────┴────────┬──────────────┐                      │
│      ▼              ▼                  ▼              ▼                      │
│  ┌───────┐    ┌───────────┐    ┌─────────────┐   ┌──────────┐                │
│  │CONTENT│    │  ANGLE    │    │   USAGE     │   │  WEEKLY  │ Phase 3:      │
│  │SCHEDULE│◄──│  MATRIX   │    │  HISTORY    │   │  SLOTS   │ Strategy      │
│  │(21/wk)│    │ (Angles)  │    │(Anti-Repeat)│   │ Template │                │
│  └───┬───┘    └───────────┘    └─────────────┘   └──────────┘                │
│      │                                                                        │
│      ▼                                                                        │
│  ┌─────────────────────────────────────────────────────────────┐             │
│  │                    7-STAGE CREATION PIPELINE                 │ Phase 4    │
│  │  ┌────┐ ┌────┐ ┌─────┐ ┌────┐ ┌─────┐ ┌────┐ ┌────┐        │             │
│  │  │ S1 │→│ S2 │→│S2.5 │→│ S3 │→│S3.5 │→│ S4 │→│ S5 │        │             │
│  │  └────┘ └────┘ └─────┘ └────┘ └─────┘ └────┘ └────┘        │             │
│  └──────────────────────────┬──────────────────────────────────┘             │
│                             ▼                                                │
│                    ┌─────────────────────┐                                   │
│                    │  GENERATED_CONTENT  │  Phase 5: Delivery                │
│                    │ (Reels/Carousel/    │  └─ Markdown + Telegram           │
│                    │  Quotes)            │                                   │
│                    └─────────────────────┘                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Database Models

| Model | Purpose |
|-------|---------|
| `EvergreenSource` | Book/blog source registry |
| `ContentReservoir` | Extracted chunks awaiting ingestion |
| `RawIngest` | Staging table for all raw content |
| `ContentAtom` | Classified atomic content units |
| `AngleMatrix` | Content generation angles |
| `ContentSchedule` | Weekly 21-slot calendar |
| `UsageHistory` | Anti-repetition tracking |
| `GeneratedContent` | Final content artifacts |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | FastAPI + SQLModel |
| **Database** | PostgreSQL 14+ with JSONB |
| **LLM** | OpenAI GPT-4 (structured outputs) |
| **Migrations** | Alembic |
| **Async** | AsyncIO with concurrency control |
| **Delivery** | Telegram Bot API + Markdown |

---

## 📖 Documentation

For comprehensive technical documentation including:
- Phase-by-phase workflows with Mermaid diagrams
- Database schema and relationships
- LLM prompt architecture
- Anti-repetition algorithms
- Retention optimization rules

**See [`docs/PRISMATIC_ENGINE_DOCUMENTATION.md`](docs/PRISMATIC_ENGINE_DOCUMENTATION.md)**

---

## 🗺️ Roadmap

- [ ] **Visual Asset Generation** — AI-generated images for Carousels
- [ ] **Instagram Auto-Publishing** — Direct posting via Graph API
- [ ] **Performance Learning Loop** — Adjust virality multipliers from engagement data
- [ ] **Multi-Account Support** — Manage multiple brand voices
- [ ] **A/B Testing Framework** — Test content variations

---

## 🤝 Contributing

Contributions are welcome! Please read the contributing guidelines before submitting a PR.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <strong>Built with 🔮 by content creators, for content creators</strong>
</p>
