# OnTarget — Football Analytics & Agentic AI System

> End-to-end football analytics platform covering 5 European leagues across 5 seasons, combining shot-level data engineering, statistical analysis, match prediction, and a multi-model AI agent — all running locally on Apple Silicon.

---

## What is OnTarget?

OnTarget is built around a simple idea: take the kind of data Sofascore shows you after a match and go significantly deeper — not just *what* happened, but *why* it happened and *what's likely to happen next*.

Every layer of the system feeds the next. Raw match and shot data is scraped, cleaned, and analysed to produce statistical findings. Those findings train a prediction model and populate a vector database. A multi-model agent sits on top, answering natural language questions grounded in real data — not hallucinated summaries.

---

## Project Structure

```
OnTarget/
│
├── src/
│   ├── scrape_understat.py        # League/season data scraper (async, aiohttp)
│   ├── scrape_shots.py            # Per-match shot data scraper (PL 2023/24)
│   └── scrape_european.py         # CL/Europa League data via FBref (planned)
│
├── notebooks/
│   ├── 01_cleaning_and_loading.ipynb     # Data cleaning pipeline
│   ├── 02_xG_analysis.ipynb              # xG over/underperformance analysis
│   ├── 03_shot_maps.ipynb                # Shot location visualizations
│   ├── 04_player_profiles.ipynb          # Player shooting profiles
│   ├── 05_counter_attack.ipynb           # Counter-attack frequency analysis
│   ├── 06_pressing_vs_results.ipynb      # PPDA pressing intensity analysis
│   ├── 07_seasonal_trends.ipynb          # How the game has changed 2020-2024
│   └── 08_novel_finding.ipynb            # Data-driven discoveries
│
├── models/
│   ├── match_outcome_predictor.py        # XGBoost match outcome model
│   └── xG_overperformance_predictor.py   # xG overperformance model
│
├── agent/
│   ├── rag_pipeline.py                   # ChromaDB vector store + retrieval
│   ├── fine_tune/                        # Mistral 7B LoRA fine-tuning (MLX)
│   └── agent.py                          # LangGraph multi-model agent
│
├── dashboard/
│   └── dashboard.py                      # Streamlit interactive dashboard
│
├── data/
│   ├── processed/                        # Clean CSVs (tracked)
│   │   ├── matches.csv                   # 8,982 matches across 5 leagues
│   │   ├── players.csv                   # 13,964 player season records
│   │   └── teams.csv                     # Per-match team history (17,964 rows)
│   └── raw/                              # Raw JSON files (not tracked)
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Competitions & Seasons

| League | Seasons |
|--------|---------|
| Premier League | 2020/21 → 2024/25 |
| La Liga | 2020/21 → 2024/25 |
| Serie A | 2020/21 → 2024/25 |
| Bundesliga | 2020/21 → 2024/25 |
| Ligue 1 | 2020/21 → 2024/25 |
| Champions League | Planned |
| Europa League | Planned |

---

## Data

### What's collected

**League-level data** (via Understat's internal XHR API):
- Every match result, date, home/away xG for 5 leagues × 5 seasons
- Player season totals — goals, xG, assists, xA, shots, key passes, npxG, xGChain, xGBuildup
- Team per-match history — xG, xGA, ppda (pressing intensity), deep completions, result, points

**Shot-level data** (via `getMatchData` endpoint — PL 2023/24):
- Every shot with: `minute`, `X/Y coordinates`, `xG`, `result`, `situation`, `shotType`, `player`
- Match rosters with per-player xG contributions
- Covers 380 Premier League matches (~10,000+ individual shots)

### Scale

| Dataset | Rows | Columns |
|---------|------|---------|
| matches.csv | 8,982 | 17 |
| players.csv | 13,964 | 20 |
| teams.csv | 17,964 | 23 |
| shots (PL 2023/24) | ~10,000+ | 14 |

### How to regenerate the data

```bash
# activate environment
conda activate OnTarget

# scrape league/season data (5 leagues × 5 seasons)
python src/scrape_understat.py

# scrape shot-level data (PL 2023/24, 380 matches)
python src/scrape_shots.py

# run cleaning notebook
jupyter notebook notebooks/01_cleaning_and_loading.ipynb
```

---

## Data Engineering

The scraper reverse-engineers Understat's internal XHR API — the same endpoint the browser calls when you visit a league page. There is no official API. The discovery process involved inspecting Chrome DevTools Network tab, identifying the `getLeagueData/{league}/{season}` and `getMatchData/{match_id}` endpoints, and replicating the exact headers the browser sends to avoid 404 responses.

Key engineering decisions:
- `aiohttp` for async HTTP requests — handles 25 league/season combinations efficiently
- `X-Requested-With: XMLHttpRequest` + `Referer` headers required to authenticate requests
- `json.load()` required for teams data — `pd.read_json()` misinterprets the dict-keyed structure
- 1 second delay between requests to avoid rate limiting

---

## Analysis

### xG Over/Underperformance
Which teams consistently score more or fewer goals than their xG predicts, and what does that tell us about finishing quality vs goalkeeper quality?

### Counter-Attack Frequency
Using the `situation` field in shot data (`FastBreak` vs `OpenPlay` vs `SetPiece`) — does counter-attack frequency differ significantly across leagues? Does the Bundesliga really counter more than the Premier League?

### Pressing Intensity vs Results
Understat's `ppda` (passes allowed per defensive action) measures how aggressively a team presses. Does high pressing intensity actually correlate with better results across 5 seasons?

### Seasonal Trends 2020-2024
Has the game become more or less open? Shots per game, xG per game, goals per game trends across all 5 leagues over 5 seasons.

### Novel Finding
One non-obvious finding discovered in the data — to be confirmed during analysis.

---

## Prediction Models

### Match Outcome Predictor (XGBoost)
Predicts win/draw/loss from pre-match features:
- Rolling xG (last 5 matches, home/away split)
- Form — points from last 5/10 matches
- Head-to-head record
- Pressing intensity (ppda)
- Deep completions
- Home/away factor

### xG Overperformance Predictor
Predicts whether a team will over or underperform their xG based on team style features — shot quality by zone, pressing stats, historical overperformance trend.

---

## Visualizations

Built with `mplsoccer` and `matplotlib`:

- **Shot maps** — every shot in a match or season plotted on a pitch, sized by xG, coloured by outcome
- **Goal minute heatmaps** — when do goals happen across a league/season?
- **Player radar charts** — compare multiple players across xG, xA, shots, key passes, npxG
- **xG timeline** — how xG accumulated minute by minute for both teams in a match
- **Team shot heatmaps** — aggregated shot locations across a full season on one pitch
- **xG over/underperformance tracker** — actual goals vs xG over time per team

All visualizations are available interactively via the Streamlit dashboard.

---

## Agent Layer

A multi-model agentic system that answers natural language football questions grounded in real data.

### Architecture

```
User Query
    → Model 1: Llama 3.2 3B (router)
        → classifies query intent
        → selects tools: RAG / DB query / prediction model
        → formats tool calls as structured JSON
    → Tools execute
        → ChromaDB returns relevant analysis findings
        → DuckDB queries processed CSVs
        → XGBoost returns match prediction
    → Model 2: Mistral 7B (fine-tuned responder)
        → receives query + all tool results
        → synthesises natural language response grounded in data
    → User sees answer
```

### Example queries the agent handles
- *"Which Premier League team has the biggest xG overperformance in 2023/24?"*
- *"Which Bundesliga striker has the best shot quality from inside the box?"*
- *"Predict Arsenal vs Manchester City this weekend"*
- *"How has pressing intensity changed in the Premier League from 2020 to 2024?"*
- *"Find me players similar to Mohamed Salah based on shot profile"*

### Fine-tuning
Mistral 7B fine-tuned via LoRA on Apple Silicon (M5 Pro) using MLX. Training data consists of football Q&A pairs formatted as tool-use instruction examples — grounding the model's responses in the actual data pipeline rather than general football knowledge.

---

## Tech Stack

| Layer | Tools |
|-------|-------|
| Data Collection | Python, aiohttp, asyncio |
| Data Processing | pandas, numpy |
| Analysis | pandas, scipy |
| Visualization | mplsoccer, matplotlib, seaborn, plotly |
| Prediction | XGBoost, scikit-learn |
| Vector Store | ChromaDB |
| LLM Fine-tuning | MLX, LoRA, Mistral 7B |
| Agent Orchestration | LangGraph, LangChain |
| Local LLM Serving | Ollama |
| Dashboard | Streamlit |
| Hardware | MacBook Pro M5 Pro 24GB |

---

## Setup

```bash
# clone the repo
git clone https://github.com/aadvikmazumdar/OnTarget.git
cd OnTarget

# create conda environment
conda create -n OnTarget python=3.11
conda activate OnTarget

# install dependencies
pip install -r requirements.txt

# scrape data
python src/scrape_understat.py

# run cleaning notebook
jupyter notebook

# launch dashboard
streamlit run dashboard/dashboard.py
```

---

## Current Status

| Phase | Status |
|-------|--------|
| Data Collection — League/Season | ✅ Complete |
| Data Collection — Shot Level | 🔄 In Progress |
| Data Cleaning & Loading | ✅ Complete |
| EDA & Analysis Notebooks | 🔄 In Progress |
| Prediction Models | ⏳ Planned |
| Visualizations & Dashboard | ⏳ Planned |
| Agent Layer | ⏳ Planned |

---

## Why OnTarget?

Most football analytics projects use a Kaggle CSV and plot a bar chart. OnTarget starts from raw HTML, reverse-engineers an undocumented API, collects shot-level data across thousands of matches, and builds analysis that surfaces non-obvious patterns — then makes all of it queryable through a natural language agent running entirely locally.

The goal was never to replicate what Sofascore already shows you. It was to go deeper than what any off-the-shelf sports platform surfaces.
