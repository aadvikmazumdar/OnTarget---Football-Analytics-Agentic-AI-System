# OnTarget — AI Football Analyst

> An AI football analyst that happens to have a dashboard. The agent is the product; the dashboard is where its answers get drawn.

Top 5 European leagues, seasons 2020–2024. Everything runs locally.

---

## The Idea

SofaScore tells you what happened. OnTarget is built to answer the questions that come after:

- Does Atletico actually win games they shouldn't, or does it just feel that way?
- Which teams outperform their xG consistently, and is that finishing or chance creation?
- Does pressing intensity predict anything, or is it just correlated with being good?
- When a team goes 1-0 up, does the opponent's xG inflate because they're chasing?
- Is a defender who shoots twice as often as his peers actually playing further forward?

Several of those turned out to have answers that contradict the common assumption. They're in [Findings](#findings) below.

---

## Data

Scraped from Understat's internal XHR endpoints (`getLeagueData`, `getMatchData`) with `aiohttp`, semaphore-limited, jittered, resume-safe.

| Table | Rows |
|---|---|
| matches | 8,982 |
| shots | 224,676 |
| team-matches | 17,964 |
| rosters | 273,825 |
| player-seasons | 13,964 |
| player careers | 3,226 |

Persisted to a single DuckDB file built by `scripts/build_db.py`, which hard-fails on missing required columns rather than letting a schema drift reach the API.

---

## Findings

Each of these came out of an EDA notebook and is written to `data/rag_findings/` as a structured block the agent retrieves.

**Press resistance predicts finishing; pressing intensity doesn't.** `ppda_allowed` — how well a team resists an opponent's press — correlates with clinical finishing at r=0.394. A team's own pressing intensity sits at r=0.021. The column name reads backwards from what it measures, which is why it's the single most misread field in the dataset.

**Teams don't sit back after scoring.** Two goals up, teams generate 2.38 xG per match. Losing, they generate 1.03. The "parked bus" is mostly an artefact of who was already better.

**Form regresses harder than anyone assumes.** A 15-point spread over five matches collapses to about 5 points going forward.

**The Premier League is the most predictable of the five.** 61.5% of outcomes explainable from xG alone — the opposite of its reputation.

**xG overperformance is genuinely random match-to-match.** Model B tested three framings and found nothing, with flat feature importances across all of them. That's a result, not a failure: it means a hot finishing streak carries no predictive signal, and the product says so rather than manufacturing an explanation.

**Shot volume encodes how far forward a player operates.** Within-position spread on shots per 90: midfielders vary 4.7x between p10 and p90, defenders 3.8x, forwards only 2.4x. Advancing up the pitch is optional for the first two and definitional for the third. The distributions overlap — a defender at the 90th percentile shoots more than a median midfielder — so the metric cuts across the position label rather than restating it.

---

## The Analysis Layer

### Three tag vocabularies

Not one system, three, and conflating them produces contradictory counts:

- **`game_tag`** — 14 mutually exclusive primary classifications (Heist, Grand Robbery, Smash and Grab, GK Worldie, Early Knockout…). Canonical for counting and narrative claims.
- **`story_tag`** — 11 composites at 5.4% density (The Heist of Heists, Bottle Job, Perfect Storm, Derby Robbery). Rare enough that surfacing one is itself a finding.
- **37 property columns** — freely overlapping flags. A match can be `smash_and_grab` in its property column, `Heist` as its `game_tag`, and `Fatigue Heist` as its `story_tag`, all correctly.

The vocabulary is derived from the database schema at API startup rather than hardcoded, because three hardcoded lists in the backend had already drifted apart and silently broken six tags in the drill-down.

### Team profiles

Every team gets a five-season block: finishing identity, trend, league rank, z-scores against the same league in the same season, season progression, derby record, fatigue effect, and a pre-written insight line. Teams with a single season are flagged `thin_sample` so the agent caveats rather than asserting.

### Player profiles

Career-aggregated, keyed on `player_id` — 24 names map to more than one player, including four distinct Danilos. Position is minutes-weighted across seasons from `primary_position_hierarchy`; the naive column puts Federico Chiesa and Noni Madueke at centre-back. Players who genuinely moved between roles are flagged `position_ambiguous` (527 of 1,740).

Penalties are excluded from every finishing figure and reported separately — at ~0.76 xG each and always struck with the stronger foot, including them would inflate both the preferred-foot share and the residual of anyone on penalty duty.

Foot splits carry a 25-shot floor per cell. A weaker-foot residual on 12 shots is noise, and the block says so instead of inventing a finding.

### Metric semantics

Three columns read backwards from their names, so direction and meaning live in `backend/app/metrics.py` rather than in anyone's head:

- `ppda_allowed` — the press a team *withstands*, not the press it applies
- `xGD_defence` — `missed - xGA`, a conceding residual. For "best defence", use `xGA_per_game`
- `xGD_attack` — `scored - xG`, a finishing residual. For "best attack", use `xG_per_game`

Every leaderboard carries its own sort direction and a plain-English caption, so a user reading `xGD_defence` sees "positive is worse" at the point of use.

---

## Models

**Match outcome (XGBoost).** 51.0% accuracy against a 46.8% calibrated xG-difference baseline; log-loss 1.008 vs 1.037. Features: rank gap, rolling and expanding form, press resistance, H2H as-of-match-date — 44 in total. Class weighting lifted draw recall from 0.09 to 0.31. Every rolling feature applies `shift(1)` before windowing.

Tested and discarded: opponent tier (redundant with rank gap), counter-attack share (0.86% sparse), squad trajectory (cost 80% of training rows).

**xG overperformance (XGBoost).** A rigorous null result across three framings. Documented as a finding rather than hidden.

**Counter-attack proxy.** Understat's `FromCounter` is absent from the scraped data, so it was built from scratch — `lastAction`, zone, and timing composited into a three-tier structure (`regular_play` / `elevated_threat` / `high_confidence_counter`), validated against xG and conversion rate. The tiered version outperformed a binary flag.

---

## The Agent

```
query
  ↓
entity resolution ──────── "Spurs" → Tottenham, "last season" → 2024
  ↓
router (Llama 3.2 3B) ──── finding | lookup | analysis | prediction | reject
  ↓
  ├── finding     → Chroma retrieval only
  ├── lookup      → one tool call
  ├── analysis    → retrieval + tools, synthesised
  ├── prediction  → feature builder → Model A → evidence ledger
  └── reject      → out of scope
  ↓
responder (Mistral 7B, MLX/LoRA) → answer + evidence + viz directive
  ↓
chat panel renders the answer; dashboard canvas renders the viz
```

**Deterministic edges, not a ReAct loop.** A local 7B doing free-form tool calling on 24GB is slow and unreliable, and every retry compounds. The graph's control flow is typed: the router class and resolved slots select the node path, nodes call tools in Python, and the LLM's only job is synthesis over an assembled context block. The LoRA is trained on analyst voice, not tool syntax.

### Retrieval

ChromaDB over `data/rag_findings/` — 1,898 chunks: 132 team blocks, 1,740 player blocks, 26 league blocks. `all-MiniLM-L6-v2`, cosine distance.

**Filter first, embed second.** The findings files are templated, so every league's pressing block is near-identical prose differing only in numbers — which sentence embeddings barely encode. Unfiltered similarity across those five returns a 0.02 spread, which is noise. So retrieval resolves the entity first and filters via metadata, and embedding search only runs across the survivors. Four modes:

| Question shape | Mode |
|---|---|
| Names a player | `player_id` filter, n=1 |
| Names a team | `team` + `kind=team`, n=1 |
| Names a league and topic | `league` + `topic`, n=1 |
| Compares leagues | `topic` only, **all five**, responder compares |
| No entity | open similarity |

The comparison mode matters: a question ranking leagues can't be answered by retrieving one league's chunk, and similarity can't order them.

### Tool surface

~35 named FastAPI endpoints over DuckDB, deliberately narrow rather than a generic query interface — chosen so an agent can call them as tools with enum-validated params. They collapse into eight tool wrappers, because tool-selection accuracy degrades well before 30 options and the router is a 3B model.

---

## Stack

| Layer | Tools |
|---|---|
| Scraping | Python, aiohttp, asyncio |
| Processing | pandas, numpy |
| Storage | DuckDB (persisted, read-only, thread-local cursors) |
| Vector store | ChromaDB, all-MiniLM-L6-v2 |
| Models | XGBoost, scikit-learn |
| Backend | FastAPI |
| Frontend | React, Vite, TypeScript, Plotly |
| Agent | LangGraph, Ollama |
| Fine-tuning | MLX, LoRA, Mistral 7B |
| Hardware | MacBook Pro M5 Pro 24GB |

Design system: charcoal `#161513`, rust `#C96A4E`, olive `#8FA36E`, slate `#6E88A8` — five colours, each with one job. Newsreader for prose, IBM Plex Mono for codes and measurements. No rounded cards on grey with shadows, no gradients, no icon-per-metric, no rainbow chart series, no spinners.

---

## Structure

```
OnTarget/
├── src/                        # async scrapers
├── notebooks/
│   ├── xg_analysis.ipynb       # tags, consistency, team RAG blocks
│   ├── counter_attack.ipynb    # counter proxy, shot enrichment
│   ├── pressing_vs_results.ipynb
│   ├── seasonal_trends.ipynb
│   ├── novel_findings.ipynb
│   ├── player_analysis.ipynb   # career table, positional baselines, player RAG
│   └── prediction_models.ipynb # Models A and B
├── backend/app/
│   ├── main.py                 # ~35 endpoints
│   ├── db.py                   # thread-local cursors over one read-only connection
│   ├── tags.py                 # vocabulary derived from schema at startup
│   ├── metrics.py              # direction + semantics per metric
│   └── findings.py             # filtered Chroma retrieval
├── frontend/src/
│   ├── pages/Dashboard.tsx
│   └── components/             # 10 Plotly chart types
├── scripts/
│   ├── build_db.py             # CSVs → DuckDB, schema-checked
│   ├── build_chroma.py         # findings → 1,898 chunks
│   └── export_teams_enriched.py
├── data/
│   ├── processed/
│   └── rag_findings/           # 26 structured txt files
└── eval/
    └── eval_questions.json
```

---

## Evaluation

Three layers, run pre and post fine-tuning:

- **RAGAS** — faithfulness, answer relevancy, context precision and recall
- **Router confusion matrix** — weighted asymmetrically, since misrouting `analysis` → `lookup` produces a thin answer while the reverse only costs latency
- **LLM-as-judge** — end-to-end response quality on factual accuracy, groundedness, relevance

The eval questions were generated as a byproduct of the EDA notebooks, which means they're shaped by what's in the findings files and will inflate retrieval scores. Correcting for that needs `lookup` questions the findings can't answer and deliberate `reject` cases.

---

## Status

| Phase | |
|---|---|
| Data collection & cleaning | ✅ |
| EDA — 6 notebooks | ✅ |
| Prediction models | ✅ |
| FastAPI + DuckDB backend | ✅ |
| React dashboard | ✅ |
| Player analysis layer | ✅ |
| Chroma retrieval | ✅ |
| Feature builder + prediction endpoint | 🔨 |
| Tool layer & entity resolution | ⏳ |
| Router + LangGraph | ⏳ |
| Responder fine-tune | ⏳ |
| Eval framework | ⏳ |

---

## Setup

```bash
git clone https://github.com/aadvikmazumdar/OnTarget---Football-Analytics-Agentic-AI-System.git
cd OnTarget

conda create -n OnTarget python=3.11
conda activate OnTarget
pip install -r requirements.txt

# scrape (5 leagues × 5 seasons, plus shots and rosters)
python src/scrape_understat.py
python src/scrape_shots.py

# run notebooks, then build the stores
python scripts/build_db.py
python scripts/build_chroma.py

# backend
cd backend && python -m uvicorn app.main:app --reload

# frontend
cd frontend && npm install && npm run dev
```

`build_db.py` deletes and recreates the database file, so the backend needs a manual restart afterwards — `--reload` watches Python files, not the database.

---

## Notes

A few things this project is deliberately not:

**Not live.** Data ends in 2024. Predictions are either hypothetical fixtures as-of a season's end, or replays of real historical matches with the result hidden and then revealed — which makes the demo self-validating.

**Not a custom xG model.** xG values are Understat's. What's built on top is game-state context, phase segmentation, zone classification, and the counter-attack proxy.

**Not broad.** Five leagues, five seasons. The trade is depth: game-state adjusted analysis, a three-vocabulary tag system, positional baselines, and season-over-season consistency profiling that a 1000-competition platform has no room for.

---

*Built on a MacBook Pro M5 Pro. Everything runs locally — no external APIs, no cloud inference, no paid data feeds.*
