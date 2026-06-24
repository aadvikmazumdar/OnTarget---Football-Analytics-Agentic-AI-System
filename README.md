# OnTarget — AI Football Analyst

> An AI football analyst that happens to have a dashboard. Not another stats site — a system that thinks about the game the way an analyst does.

---

## The Idea

SofaScore tells you what happened. OnTarget tells you why it happened, how unusual it was, and what's likely to happen next.

The starting point was a simple frustration: every public football platform shows you the same surface-level stats. xG totals, possession percentages, pass completion rates. What none of them do is ask the harder questions:

- Does Atletico Madrid actually win games they shouldn't, or does it just feel that way?
- Which teams consistently outperform their xG — and is it finishing quality or something about how they create chances?
- When a team goes 1-0 up, does the opponent's xGA artificially inflate because they're chasing the game?
- Does pressing intensity actually predict xG overperformance, or is it just correlated with good teams?
- Are teams that spend most of a match trailing creating lower quality chances — or just more desperate ones?

OnTarget is built to answer those questions. The AI layer makes all of it queryable in natural language.

---

## What Makes This Different From SofaScore

| | SofaScore | OnTarget |
|--|-----------|----------|
| Data breadth | 1000+ competitions | 5 leagues, 5 seasons, deep |
| Live data | ✅ | ❌ |
| xG per match | ✅ | ✅ |
| xGD consistency across seasons | ❌ | ✅ |
| Game-state adjusted xG | ❌ | ✅ |
| Opponent-quality adjusted xGD | ❌ | ✅ |
| 20-tag game classification system | ❌ | ✅ |
| Composite story tags per match | ❌ | ✅ |
| Counter-attack conversion by league | ❌ | ✅ |
| Shot quality by phase (Q1-AT) | ❌ | ✅ |
| Derby performance tracking | ❌ | ✅ |
| Fixture fatigue signal | ❌ | ✅ |
| Pressing → xGD correlation | ❌ | ✅ |
| League predictability index | ❌ | ✅ |
| Natural language queries | ❌ | ✅ |
| Agent controls dashboard filters | ❌ | ✅ |

SofaScore is for fans who want scores. OnTarget is for people who want to understand the game analytically.

---

## The Analysis Layer 
### Game Classification System — 20 Primary Tags Every match row is tagged with a primary game label based on xG vs goals relationships. Tags are assigned via a reversed priority loop — the most dramatic story wins. 
| Tag | Definition | 
|-----|-----------|
| **Perfect Heist** | Won away, xGA exceeded xG by 1.0+ |
| **Grand Heist** | Won while xGA exceeded xG by 1.0+ | 
| **Grand Robbery** | Lost while xG exceeded xGA by 1.0+ |
| **Cruel** | Grand robbery, away from home |
| **Heist** | Won while being dominated on xG |
| **Robbery** | Lost while dominating xG |
| **Ultra Clinical** | Outscored xG by 1.5+ goals |
| **Dominant Win** | Won with xG exceeding xGA by 1.5+ |
| **GK Worldie** | GK saved 1.5+ goals above xGA |
| **GK Nightmare** | GK conceded 1.5+ goals above xGA |
| **Heroic Defence** | Clean sheet despite xGA 1.5+ |
| **Fortress** | Heist at home |
| **Home Bottled** | Home team failed to win despite xG dominance |
| **Momentum Collapse** | Led on xG at home but defence gave away 1.5+ above xGA |
| **False Dominance** | Lost despite marginally dominating xG, terrible finishing |
| **Smash and Grab** | Won with under 0.8 xG — pure efficiency |
| **Early Knockout** | Dominated Q1, won the match |
| **Clinical** | Scored more than xG suggested |
| **Wasteful** | Scored less than xG suggested |
| **Normal** | No dramatic pattern |

## The Agent Is the Product

The dashboard is visual context. The agent is the interface.

```
"Which Bundesliga team has been most clinical away from home over 3 seasons?"
→ Agent retrieves from pre-computed findings
→ Answer with z-score context and season progression

"Show me Bayern's counter-attack shots from 2022"
→ Shot map renders instantly on the dashboard
→ Agent appends insight on conversion rate vs open play

"Show all Bottle Job games in the Premier League"
→ Filtered table of matches where home teams dominated xG but collapsed
→ Ranked by magnitude of the capitulation

"Is Arsenal on a heist streak?"
→ Rolling form vs xGD divergence check
→ Agent flags whether current form is sustainable

"Predict Arsenal vs Man City this weekend"
→ W/D/L probabilities + predicted xG
→ Derby flag, fatigue flag, H2H profile auto-shown

"Now compare that to last season"
→ Conversation memory resolves "that" without restating context
```

---

## The Analysis Layer

### Game Classification System

Every match is tagged with a primary story label and a composite story tag — the most dramatic narrative wins. Tags range from **Perfect Heist** and **Grand Robbery** to **Bottle Job**, **The Heist of Heists**, and **Game of the Season**.

Visit the dashboard to explore which tags define your team.

### xG Consistency Rating

Every team gets a 5-season analytical profile — not just a single xGD number. Finishing identity, trend direction, league rank, z-scores, season progression, derby performance, fatigue effect, and a pre-written analyst insight line. The kind of profile a club's data team would build internally.

### Game-State Adjusted xG

Standard xG models are context-blind. OnTarget's shot model accounts for game state at the time of each shot — making it more analytically honest than Understat's own model. A team sitting deep at 2-0 up concedes high-xG shots for tactical reasons, not defensive failure. The model knows the difference.

### Phase Analysis (Q1 → Q2 → Q3 → Q4 → AT)

Every match divided into five phases. Shot quality, conversion rates, game state distribution, and momentum signals computed per phase per team per league — including added time, where the data tells a specific story about desperation vs composure.

### Fixture Intelligence

Fatigue tracking (matches played within 3 days) and derby classification (15 named derbies across all 5 leagues) are built into every analysis. The match predictor surfaces both automatically.

---

## Novel Findings

Several non-obvious questions answered by the data that no public platform has published. Visit the Novel Findings page on the dashboard to see the results — with annotated charts and the data behind each conclusion.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      OnTarget Platform                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Streamlit Dashboard (dark theme)                          │
│   ├── League Overview                                       │
│   ├── Team Deep Dive                                        │
│   │   ├── Season Summary                                    │
│   │   ├── Per-Game Clinical Rating  ← unique tab            │
│   │   ├── Heist Games               ← unique tab            │
│   │   ├── Story Tags                ← unique tab            │
│   │   ├── Derby Performance         ← unique tab            │
│   │   ├── Fatigue Analysis          ← unique tab            │
│   │   └── Form vs xGD Divergence    ← unique tab            │
│   ├── Player Profile                                        │
│   │   ├── Z-score anomaly                                   │
│   │   ├── Peak season detection                             │
│   │   └── Trajectory label                                  │
│   ├── Shot Intelligence                                     │
│   ├── Match Predictor                                       │
│   ├── Novel Findings                                        │
│   └── 💬 Agent (floating, always visible)                   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                    24 Chart Boilerplates                     │
│   Agent fills params dict → renders instantly               │
│   Never writes plot code — only fills parameters            │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                     Agent Layer (LangGraph)                  │
│   ├── Router: Llama 3.2 3B — intent classification          │
│   ├── RAG: ChromaDB over 21 structured findings files       │
│   ├── DuckDB: live SQL on shots + rosters at runtime        │
│   ├── predict_match(): XGBoost + derby/fatigue context      │
│   ├── render_chart(): triggers any of 24 boilerplates       │
│   ├── update_dashboard_filter(): controls UI state          │
│   ├── get_derby_analysis(): derby performance tool          │
│   ├── get_anomaly_players(): z-score freak finder           │
│   ├── get_form_divergence(): heist streak detector          │
│   └── Responder: Mistral 7B fine-tuned via MLX/LoRA         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                      Prediction Models                       │
│   ├── match_outcome_predictor (XGBoost) — W/D/L             │
│   │   Rolling xG, PPDA, ppda_cv, derby/fatigue flags,       │
│   │   form_xGD_divergence, home advantage decomposition      │
│   ├── xg_shot_model — game-state + rebound aware P(goal)    │
│   └── xg_overperformance_predictor (XGBoost) — binary       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                       Data Layer                             │
│   ├── 224k shots — phase, game_state, cross_side,           │
│   │   shot_zone, is_cross enrichment                        │
│   ├── 273k rosters — match_id added at source               │
│   ├── clinical_games.csv — 20 game tags, 11 story tags,     │
│   │   phase columns, derby/fatigue flags                     │
│   └── data/rag_findings/ — 21 structured txt files          │
│       analyst-grade fact blocks per team/league/season       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### RAG vs DuckDB — Clean Separation

| Query type | Route |
|------------|-------|
| Team season stats, consistency, game tags | RAG |
| League comparisons, novel findings | RAG |
| Derby performance, fatigue effect | RAG |
| Player/shot granular queries | DuckDB |
| Story tag lookups, flag filters | DuckDB |
| Match prediction | Model |
| Visual queries | Boilerplate |

---

## Evaluation Framework

Three-layer eval stack run pre and post fine-tuning:

**Layer 1 — RAGAS** (RAG pipeline quality)
Faithfulness, answer relevancy, context precision, context recall.

**Layer 2 — Router Confusion Matrix** (Llama 3B routing accuracy)
30 test queries with known correct tool selections. Surfaces exactly where the router fails.

**Layer 3 — LLM-as-Judge** (end-to-end response quality)
Claude scores each agent response 1-5 on factual accuracy, groundedness, and relevance.

Target: 80%+ on all three layers. Delta pre/post fine-tuning in the README on completion.

---

## Project Structure

```
OnTarget/
├── src/
│   ├── scrape_understat.py         # Async league/season scraper (aiohttp)
│   └── scrape_shots.py             # Per-match shot + roster scraper
│
├── notebooks/
│   ├── 01_cleaning_and_loading.ipynb
│   ├── 02_xG_analysis.ipynb        # Game classification, story tags,
│   │                               # consistency ratings, RAG findings
│   ├── 03_counter_attack.ipynb
│   ├── 04_pressing_vs_results.ipynb
│   ├── 05_seasonal_trends.ipynb
│   └── 06_novel_finding.ipynb
│
├── models/
│   ├── match_outcome_predictor.py
│   ├── xg_shot_model.py
│   └── xg_overperformance_predictor.py
│
├── charts/
│   └── boilerplates.py             # 24 chart functions, params dict interface
│
├── agent/
│   ├── rag_pipeline.py
│   ├── agent.py                    # LangGraph multi-model agent
│   └── fine_tune/                  # Mistral 7B LoRA (MLX)
│
├── dashboard/
│   └── dashboard.py
│
├── data/
│   ├── processed/                  # Clean CSVs (tracked in git)
│   └── rag_findings/               # 21 structured txt files
│
└── eval/
    └── eval_questions.json         # 30 questions with known answers
```

---

## Tech Stack

| Layer | Tools |
|-------|-------|
| Data Collection | Python, aiohttp, asyncio |
| Data Processing | pandas, numpy |
| Analysis | pandas, scipy, DuckDB |
| Visualization | mplsoccer, matplotlib, plotly |
| Prediction | XGBoost, scikit-learn |
| Vector Store | ChromaDB, nomic-embed-text |
| LLM Fine-tuning | MLX, LoRA, Mistral 7B |
| Agent Orchestration | LangGraph |
| Local LLM Serving | Ollama |
| Dashboard | Streamlit |
| Hardware | MacBook Pro M5 Pro 24GB |

---

## Setup

```bash
git clone https://github.com/aadvikmazumdar/OnTarget---Football-Analytics-Agentic-AI-System.git
cd OnTarget

conda create -n OnTarget python=3.11
conda activate OnTarget
pip install -r requirements.txt

# scrape data (5 leagues × 5 seasons + shots/rosters)
python src/scrape_understat.py
python src/scrape_shots.py

# run notebooks in order (01 → 06)
jupyter notebook

# launch dashboard
streamlit run dashboard/dashboard.py

# start Ollama models (for agent)
ollama pull llama3.2:3b
ollama pull mistral:7b
ollama pull nomic-embed-text
```

---

## Current Status

| Phase | Status |
|-------|--------|
| Data Collection | ✅ Complete |
| Data Cleaning & Engineering | ✅ Complete |
| EDA — xG Analysis (notebook 02) | ✅ Complete |
| EDA — Counter Attack (notebook 03) | ⏳ Planned |
| EDA — Pressing vs Results (notebook 04) | ⏳ Planned |
| EDA — Seasonal Trends (notebook 05) | ⏳ Planned |
| EDA — Novel Findings (notebook 06) | ⏳ Planned |
| Prediction Models | ⏳ Planned |
| Dashboard + 24 Boilerplates | ⏳ Planned |
| Agent Layer | ⏳ Planned |
| Evaluation | ⏳ Planned |

---

## Demo

*Screen recording coming on completion — 2-3 minutes of the agent answering real football questions, triggering live dashboard filters, and predicting a match with derby and fatigue context.*

---

*Built on a MacBook Pro M5 Pro. Everything runs locally — no external APIs, no cloud inference, no paid data feeds.*
