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

OnTarget is built to answer those questions — grounded in 224,000 shots, 8,982 matches, and 5 seasons of data across Europe's top 5 leagues. The AI layer makes all of it queryable in natural language.

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
| Heist/robbery game classification | ❌ | ✅ |
| Counter-attack conversion by league | ❌ | ✅ |
| Shot quality by phase (Q1-AT) | ❌ | ✅ |
| Pressing → xGD correlation | ❌ | ✅ |
| Natural language queries | ❌ | ✅ |
| Agent controls dashboard filters | ❌ | ✅ |

SofaScore is for fans who want scores. OnTarget is for people who want to understand the game analytically.

---

## The Agent Is the Product

The dashboard is visual context. The agent is the interface.

```
"Which Bundesliga team has been most clinical away from home over 3 seasons?"
→ RAG retrieval over pre-computed findings
→ "RasenBallsport Leipzig: +0.8 avg xGD away, 3/5 seasons positive, +1.2σ above league avg"

"Show me Bayern's counter-attack shots from 2022"
→ render_chart("shot_map", {team: "Bayern Munich", season: "2022",
   situation: "FromCounter", league: "bundesliga"})
→ Shot map renders instantly
→ "Bayern attempted 41 counter-attack shots in 2022, averaging 0.19 xG/shot
   vs their open play rate of 0.13 — transition football creates better chances"

"Predict Arsenal vs Man City this weekend"
→ Shot-level xG model + match outcome predictor
→ W/D/L probabilities + predicted scoreline + H2H historical xG profile

"Now compare that to last season"
→ Conversation memory resolves "that" without restating context
```

---

## The Analysis Layer

### Game Classification System

Every match is tagged with a primary story label based on the xG vs goals relationship:

| Tag | Definition |
|-----|-----------|
| **Perfect Heist** | Won away, xGA exceeded xG by 1.0+ |
| **Grand Heist** | Won while xGA exceeded xG by 1.0+ |
| **Grand Robbery** | Lost while xG exceeded xGA by 1.0+ |
| **GK Worldie** | GK saved 1.5+ goals above xGA |
| **Dominant Win** | Won with xG exceeding xGA by 1.5+ |
| **Heroic Defence** | Clean sheet despite xGA 1.5+ |
| **Chaos Game** | Total goals exceeded total xG by 50%+ |
| **Ghost Game** | Total goals less than 50% of total xG |
| **Home Bottled** | Home team failed to win despite xG dominance |

These tags power the **Heist Games** and **Per-Game Clinical Rating** tabs — surfaces no public platform shows.

### xG Consistency Rating

Rather than a single-season xGD figure, every team in the dataset gets a 5-season profile:

```
TEAM: Atletico Madrid | LEAGUE: la_liga
FINISHING IDENTITY: counter-attacking/heist specialists | TREND: declining
ATTACK: avg_xGD_attack=+2.41 | clinical_rate=49.0% | seasons_overperforming=4/5
DEFENCE: avg_xGD_defence=-4.53 | seasons_solid=4/5
LEAGUE RANK: avg_xGD_attack_rank=1st of 20 | avg_heist_rank=1st of 20
Z-SCORES: xGD_attack=+1.8σ | heist_rate=+2.1σ | xGD_defence=-1.6σ
SEASON_PROGRESSION: 2020: +9.3 → 2021: +3.1 → 2022: +1.2 → 2023: +3.7 → 2024: -4.3
INSIGHT: Atletico are La Liga's premier heist specialists — 2.1σ above league
average heist rate, combining elite defensive xG suppression with clinical
counter-attacking. Declining trend since 2020 peak.
```

### Game-State Adjusted xG

Standard xG models are context-blind. A team 2-0 up in the 85th minute will concede high-xG shots because they're sitting deep — not because their defence is poor. OnTarget's shot model accounts for game state at the time of each shot, making it more analytically honest than Understat's own model.

### Phase Analysis

Every match is divided into five phases — Q1 (0-25), Q2 (26-45), Q3 (46-70), Q4 (71-90), AT (90+). For each phase across each team and league:

- Shot volume and xG per shot
- Game state distribution (how many shots taken when losing vs winning)
- Does shot quality improve or decline as the game progresses? (momentum signal)
- Do high-PPDA teams generate more Q1 chances? (pressing → early phase chances)

### Cross & Transition Analysis

- Cross volume by flank (left/right) and phase
- xG per cross-assisted shot vs open play shots
- Counter-attack conversion rates by league — does the Bundesliga really counter more efficiently than Serie A?
- lastAction breakdown — what happened immediately before each shot

---

## The Novel Findings

Two questions explored that no public platform has published answers to:

**1. Does scoring first artificially inflate opponent xGA?**
When a team goes 1-0 up, the opponent chases the game. This should inflate their xGA in Q3+Q4 independent of actual defensive quality — making the winning team look defensively weaker than they are. The data tests this directly.

**2. Does PPDA predict xG overperformance?**
The hypothesis: pressing teams win the ball higher up the pitch, generating shorter-distance shots with higher xG. If confirmed, PPDA becomes a leading indicator of finishing efficiency, not just a style metric.

---

## Data Scale

| Dataset | Rows | Covers |
|---------|------|--------|
| matches.csv | 8,982 | 5 leagues × 5 seasons |
| players.csv | 13,964 | Season-level player stats |
| teams.csv | 35,928 | Per-match team history (2 rows per match) |
| shots.csv | 224,676 | All 5 leagues, all 5 seasons |
| rosters.csv | 273,825 | Per-match player contributions |
| clinical_games.csv | 17,964 | Per-match flags and game tags |

All data scraped from Understat's internal XHR API — the same endpoints the browser calls, reverse-engineered via Chrome DevTools.

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
│   │   └── Heist Games               ← unique tab            │
│   ├── Player Profile                                        │
│   ├── Shot Intelligence                                     │
│   ├── Match Predictor                                       │
│   ├── Novel Findings                                        │
│   └── 💬 Agent (floating, always visible)                   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                    21 Chart Boilerplates                     │
│   shot_map, xgd_bar, timeline, radar, heatmap, trend,       │
│   heist_table, home_away_split, h2h_xg, clinical_scatter,  │
│   player_bar, player_trend, situation_bar, game_tag_dist,   │
│   zscore_dist, phase_bar, phase_heatmap, cross_map,         │
│   momentum_line, player_position_scatter, winger_profile    │
│   Agent fills params dict → renders instantly               │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                     Agent Layer (LangGraph)                  │
│   ├── Router: Llama 3.2 3B — intent classification          │
│   ├── Tool 1: RAG over data/rag_findings/ (ChromaDB)        │
│   ├── Tool 2: DuckDB — live SQL on shots + rosters CSVs     │
│   ├── Tool 3: predict_match() — XGBoost model               │
│   ├── Tool 4: render_chart() — triggers boilerplate          │
│   ├── Tool 5: update_dashboard_filter() — controls UI       │
│   └── Responder: Mistral 7B fine-tuned via MLX/LoRA         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                      Prediction Models                       │
│   ├── match_outcome_predictor (XGBoost) — W/D/L             │
│   ├── xg_shot_model (XGBoost) — game-state aware P(goal)    │
│   └── xg_overperformance_predictor (XGBoost) — binary       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                       Data Layer                             │
│   ├── 224k shots — enriched with phase, game_state,         │
│   │   cross_side, shot_zone, is_cross                       │
│   ├── clinical_games.csv — game tags, magnitude columns      │
│   ├── team_season + consistency — z-scores, ranks           │
│   └── data/rag_findings/ — 10 structured text files         │
│       pre-computed fact blocks per team/league/season        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### RAG vs DuckDB — Clean Separation

| Query type | Route | Example |
|------------|-------|---------|
| Team season stats | RAG | "Liverpool's xGD in 2023" |
| League comparisons | RAG | "Which league converts counters best?" |
| Consistency ratings | RAG | "Most systematic overperformer in Bundesliga" |
| Novel findings | RAG | "Does scoring first predict wins?" |
| Player/shot granular | DuckDB | "Salah's shots from inside the box in 2022" |
| Match prediction | Model | "Predict Arsenal vs City" |
| Visual query | Boilerplate | "Show me Bayern's shot map" |

---

## Evaluation Framework

Three-layer eval stack run pre and post fine-tuning:

**Layer 1 — RAGAS** (RAG pipeline quality)
Faithfulness, answer relevancy, context precision, context recall.

**Layer 2 — Router Confusion Matrix** (Llama 3B routing accuracy)
30 test queries with known correct tool selections across DuckDB / RAG / predictor / chart / filter / comparison. Surfaces exactly where the router fails.

**Layer 3 — LLM-as-Judge** (end-to-end response quality)
Claude scores each agent response 1-5 on factual accuracy, groundedness, and relevance. Same 30-question eval set.

Target: 80%+ on all three layers. Delta pre/post fine-tuning validates whether fine-tuning helped. All three metrics in the README on completion.

---

## Project Structure

```
OnTarget/
├── src/
│   ├── scrape_understat.py         # Async league/season scraper (aiohttp)
│   └── scrape_shots.py             # Per-match shot data scraper
│
├── notebooks/
│   ├── 01_cleaning_and_loading.ipynb
│   ├── 02_xG_analysis.ipynb        # xGD, consistency, game tags, clinical/heist
│   ├── 03_counter_attack.ipynb     # Situation, phase, cross, lastAction analysis
│   ├── 04_pressing_vs_results.ipynb
│   ├── 05_seasonal_trends.ipynb    # Player per-90s, avg position, z-scores
│   └── 06_novel_finding.ipynb      # Scoring first + PPDA → overperformance
│
├── models/
│   ├── match_outcome_predictor.py
│   ├── xg_shot_model.py
│   └── xg_overperformance_predictor.py
│
├── charts/
│   └── boilerplates.py             # 21 chart functions, params dict interface
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
│   └── rag_findings/               # Structured fact blocks (10 txt files)
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

# scrape data (5 leagues × 5 seasons + shots)
python src/scrape_understat.py
python src/scrape_shots.py

# run notebooks in order
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
| EDA — Counter Attack (notebook 03) | 🔄 In Progress |
| EDA — Pressing vs Results (notebook 04) | ⏳ Planned |
| EDA — Seasonal Trends (notebook 05) | ⏳ Planned |
| EDA — Novel Findings (notebook 06) | ⏳ Planned |
| Prediction Models | ⏳ Planned |
| Dashboard + Boilerplates | ⏳ Planned |
| Agent Layer | ⏳ Planned |
| Evaluation | ⏳ Planned |

---

## Demo

*Screen recording coming on completion — 2-3 minutes of the agent answering real football questions, triggering live dashboard filters, and predicting a match with confidence scores.*

---

*Built on a MacBook Pro M5 Pro. Everything runs locally — no external APIs, no cloud inference, no paid data feeds.*
