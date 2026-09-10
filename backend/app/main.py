from __future__ import annotations

from contextlib import asynccontextmanager
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .metrics import METRICS, INVERTED_SEMANTICS

from .db import db
from . import tags as tagmod


def df_to_records(df):
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].astype(str)
    df = df.replace([float('inf'), float('-inf')], pd.NA)
    return df.astype(object).where(pd.notna(df), None).to_dict(orient='records')




@asynccontextmanager
async def lifespan(app: FastAPI):
    tagmod.load_tags(db())
    print(f"[startup] {len(tagmod.TAG_COLS)} tag columns detected")
    yield


app = FastAPI(title="OnTarget API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/tags")
def list_tags():
    return tagmod.TAG_COLS


@app.get("/api/teams")
def list_teams():
    df = db().execute("SELECT DISTINCT team_name FROM teams ORDER BY 1").df()
    return df['team_name'].tolist()


@app.get("/api/leagues")
def list_leagues():
    return db().execute("SELECT DISTINCT league FROM teams ORDER BY 1").df()['league'].tolist()


@app.get("/api/seasons")
def all_seasons():
    return db().execute("SELECT DISTINCT year FROM teams ORDER BY year").df()['year'].tolist()


@app.get("/api/teams-by-league")
def teams_by_league(league: str | None = None, year: int | None = None):
    q = "SELECT DISTINCT team_name FROM teams WHERE 1=1"
    params = []
    if league:
        q += " AND league = ?"
        params.append(league)
    if year is not None:
        q += " AND year = ?"
        params.append(year)
    q += " ORDER BY 1"
    return db().execute(q, params).df()['team_name'].tolist()


@app.get("/api/teams/{team_name}/seasons")
def team_seasons(team_name: str):
    df = db().execute(
        "SELECT DISTINCT year FROM shots WHERE team_name = ? ORDER BY year",
        [team_name]).df()
    return df['year'].tolist()


@app.get("/api/teams/{team_name}/league")
def team_league(team_name: str, year: int):
    df = db().execute(
        "SELECT DISTINCT league FROM teams WHERE team_name = ? AND year = ?",
        [team_name, year]).df()
    return df['league'].tolist()[0] if len(df) else None


@app.get("/api/teams/{team_name}/league-any")
def team_league_any(team_name: str):
    df = db().execute("""
        SELECT league FROM teams WHERE team_name = ?
        GROUP BY league ORDER BY count(*) DESC, league LIMIT 1
    """, [team_name]).df()
    return df['league'].tolist()[0] if len(df) else None


@app.get("/api/teams/{team_name}/opponents")
def team_opponents(team_name: str, year: int | None = None, side: str = "taken"):
    if side == "conceded":
        q = "SELECT DISTINCT team_name AS opp FROM shots WHERE opponent_team = ?"
    else:
        q = "SELECT DISTINCT opponent_team AS opp FROM shots WHERE team_name = ?"
    params = [team_name]
    if year is not None:
        q += " AND year = ?"
        params.append(year)
    q += " ORDER BY 1"
    return db().execute(q, params).df()['opp'].tolist()


@app.get("/api/teams/{team_name}/xg-trend")
def team_xg_trend(team_name: str):
    df = db().execute("""
        SELECT date, xG, xGA, opponent, rank_to_date
        FROM teams
        WHERE team_name = ?
        ORDER BY date
    """, [team_name]).df()
    return df_to_records(df)


@app.get("/api/teams/{team_name}/form")
def team_form(team_name: str, year: int | None = None):
    q = """SELECT date, year, xG, xGA, opponent, result, rank_to_date
           FROM teams WHERE team_name = ?"""
    params = [team_name]
    if year is not None:
        q += " AND year = ?"
        params.append(year)
    q += " ORDER BY date"
    return df_to_records(db().execute(q, params).df())


@app.get("/api/league-average-xg")
def league_average_xg(league: str, year: int):
    df = db().execute(
        "SELECT AVG(xG) AS avg_xg, AVG(xGA) AS avg_xga FROM teams WHERE league = ? AND year = ?",
        [league, year]).df()
    return df_to_records(df)[0]


@app.get("/api/league-average-xg-all")
def league_average_xg_all(league: str):
    df = db().execute(
        "SELECT AVG(xG) AS avg_xg, AVG(xGA) AS avg_xga FROM teams WHERE league = ?",
        [league]).df()
    return df_to_records(df)[0]


@app.get("/api/press-resistance")
def press_resistance():
    df = db().execute("""
        SELECT
            team_name, league, year,
            AVG(ppda_allowed_value) AS avg_ppda_allowed,
            SUM(scored) AS total_scored,
            SUM(xG) AS total_xG
        FROM teams
        GROUP BY team_name, league, year
    """).df()
    df['clinical_rate'] = df['total_scored'] / df['total_xG']
    return df_to_records(df)


@lru_cache(maxsize=256)
def _shots_cached(team_name: str, year: int | None, opponent: str | None, conceded: bool):
    col = "opponent_team" if conceded else "team_name"
    other = "team_name" if conceded else "opponent_team"
    q = (f"SELECT X, Y, xG, result, situation, player, date, {other} AS other_team "
         f"FROM shots WHERE {col} = ?")
    params = [team_name]
    if year is not None:
        q += " AND year = ?"
        params.append(year)
    if opponent is not None:
        q += f" AND {other} = ?"
        params.append(opponent)
    return df_to_records(db().execute(q, params).df())


@app.get("/api/teams/{team_name}/shots")
def team_shots(team_name: str, year: int | None = None, opponent: str | None = None):
    return _shots_cached(team_name, year, opponent, False)


@app.get("/api/teams/{team_name}/shots-conceded")
def team_shots_conceded(team_name: str, year: int | None = None, opponent: str | None = None):
    return _shots_cached(team_name, year, opponent, True)


@app.get("/api/matches/{match_id}/shots")
def match_shots(match_id: int, team_name: str):
    df = db().execute("""
        SELECT X, Y, xG, result, situation, player, date, opponent_team AS other_team
        FROM shots WHERE match_id = ? AND team_name = ?
    """, [match_id, team_name]).df()
    return df_to_records(df)


@app.get("/api/teams/{team_name}/shot-quality")
def shot_quality(team_name: str, year: int | None = None):
    q = "SELECT xG, game_state, situation, counter_tier FROM shots WHERE team_name = ?"
    params = [team_name]
    if year is not None:
        q += " AND year = ?"
        params.append(year)
    return df_to_records(db().execute(q, params).df())


@app.get("/api/teams/{team_name}/zone-matrix")
def zone_matrix(team_name: str, year: int | None = None):
    q = """SELECT shot_zone, situation, COUNT(*) AS shots, AVG(xG) AS avg_xg,
           SUM(CASE WHEN result = 'Goal' THEN 1 ELSE 0 END) AS goals
           FROM shots WHERE team_name = ?"""
    params = [team_name]
    if year is not None:
        q += " AND year = ?"
        params.append(year)
    q += " GROUP BY shot_zone, situation"
    return df_to_records(db().execute(q, params).df())


@app.get("/api/teams/{team_name}/tags")
def team_tags(team_name: str, year: int | None = None):
    cols = ', '.join(f'"{c}"' for c in tagmod.TAG_COLS)
    q = f"SELECT date, {cols} FROM clinical_games WHERE team_name = ?"
    params = [team_name]
    if year is not None:
        q += " AND year = ?"
        params.append(year)
    q += " ORDER BY date"
    df = db().execute(q, params).df()

    counts = {c: int((df[c] == c).sum()) for c in tagmod.TAG_COLS}

    df['date'] = df['date'].astype(str)
    timeline = []
    for _, row in df.iterrows():
        active = [c for c in tagmod.TAG_COLS if row[c] == c]
        if active:
            timeline.append({'date': row['date'], 'tags': active})

    return {'counts': counts, 'timeline': timeline}


@app.get("/api/teams/{team_name}/matches-by-tag")
def matches_by_tag(team_name: str, tag: str, year: int | None = None):
    if tag not in tagmod.TAG_COLS:
        raise HTTPException(404, f"Unknown tag '{tag}'. See /api/tags.")
    q = f"""SELECT match_id, date, home_team, away_team, scored, missed, xG, xGA,
            result, game_tag, story_tag
            FROM clinical_games WHERE team_name = ? AND "{tag}" = ?"""
    params = [team_name, tag]
    if year is not None:
        q += " AND year = ?"
        params.append(year)
    q += " ORDER BY date"
    return df_to_records(db().execute(q, params).df())


@app.get("/api/teams/{team_name}/profile")
def team_profile(team_name: str, year: int | None = None):
    q = """SELECT team_name, league, year, xGD_attack_zscore, xGD_defence_zscore,
           clinical_rate_zscore, heist_rate_zscore, robbery_rate_zscore
           FROM team_season WHERE team_name = ?"""
    params = [team_name]
    if year is not None:
        q += " AND year = ?"
        params.append(year)
    return df_to_records(db().execute(q, params).df())


@app.get("/api/consistency")
def consistency(league: str | None = None):
    q = """SELECT team_name, league, seasons_played, avg_xGD_attack,
           best_xGD_attack_season, worst_xGD_attack_season, attack_verdict, defence_verdict
           FROM consistency WHERE seasons_played > 1"""
    params = []
    if league:
        q += " AND league = ?"
        params.append(league)
    q += " ORDER BY avg_xGD_attack DESC"
    return df_to_records(db().execute(q, params).df())


@app.get("/api/leaderboard")
def leaderboard(metric: str = "xGD_attack", league: str | None = None,
                year: int | None = None, limit: int | None = None,
                order: str | None = None):
    spec = METRICS.get(metric)
    if spec is None:
        raise HTTPException(
            404, f"Unknown metric '{metric}'. Allowed: {sorted(METRICS)}")

    # order overrides the metric's natural direction, so "worst defences" is
    # reachable as well as "best".
    if order:
        direction = "DESC" if order.lower() == "desc" else "ASC"
    else:
        direction = "DESC" if spec["higher_is_better"] else "ASC"

    q = f'SELECT team_name, league, year, "{metric}" AS value FROM team_season WHERE 1=1'
    params = []
    if league:
        q += " AND league = ?"
        params.append(league)
    if year is not None:
        q += " AND year = ?"
        params.append(year)
    q += f' ORDER BY "{metric}" {direction}'
    if limit:
        q += f" LIMIT {int(limit)}"

    return {
        "metric": metric,
        "label": spec["label"],
        "plain": spec["plain"],
        "gloss": spec["gloss"],
        "higher_is_better": spec["higher_is_better"],
        "rows": df_to_records(db().execute(q, params).df()),
    }


@app.get("/api/metrics")
def list_metrics():
    return [{"metric": k, **v} for k, v in METRICS.items()]


@app.get("/api/landing/game-state")
def landing_game_state():
    df = db().execute("""
        SELECT game_state, AVG(match_xg) AS avg_xg, COUNT(*) AS matches FROM (
            SELECT match_id, team_name, game_state, SUM(xG) AS match_xg
            FROM shots GROUP BY match_id, team_name, game_state
        ) GROUP BY game_state ORDER BY avg_xg DESC
    """).df()
    return df_to_records(df)


@app.get("/api/landing/form-regression")
def landing_form_regression():
    df = db().execute("""
        WITH ordered AS (
            SELECT team_name, league, year, date,
                   CASE result WHEN 'w' THEN 3 WHEN 'd' THEN 1 ELSE 0 END AS pts,
                   ROW_NUMBER() OVER (PARTITION BY team_name, league, year ORDER BY date) AS mn
            FROM teams
        ),
        windows AS (
            SELECT team_name, league, year, mn,
                   SUM(pts) OVER (PARTITION BY team_name, league, year ORDER BY mn
                                  ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS cur5,
                   SUM(pts) OVER (PARTITION BY team_name, league, year ORDER BY mn
                                  ROWS BETWEEN 5 FOLLOWING AND 9 FOLLOWING) AS next5,
                   COUNT(*) OVER (PARTITION BY team_name, league, year ORDER BY mn
                                  ROWS BETWEEN 5 FOLLOWING AND 9 FOLLOWING) AS n_next
            FROM ordered
        )
        SELECT cur5, AVG(next5) AS avg_next5, COUNT(*) AS n
        FROM windows
        WHERE mn >= 5 AND n_next = 5
        GROUP BY cur5 ORDER BY cur5
    """).df()
    return df_to_records(df)


@app.get("/api/landing/press-scatter")
def landing_press_scatter():
    df = db().execute("""
        SELECT team_name, league, year,
               AVG(ppda_allowed_value) AS avg_ppda_allowed,
               SUM(scored) AS total_scored, SUM(xG) AS total_xG
        FROM teams GROUP BY team_name, league, year
    """).df()
    df['clinical_rate'] = df['total_scored'] / df['total_xG']
    return df_to_records(df[['avg_ppda_allowed', 'clinical_rate', 'team_name', 'year']])


@app.get("/api/landing/tag-counts")
def landing_tag_counts(limit: int = 20):
    out = []
    for c in tagmod.TAG_COLS:
        n = db().execute(
            f'SELECT count(*) AS n FROM clinical_games WHERE "{c}" = ?', [c]
        ).df()['n'][0]
        out.append({'tag': c, 'count': int(n)})
    out.sort(key=lambda r: -r['count'])
    return out[:limit] if limit else out


@app.get("/api/tags/{tag}/leaderboard")
def tag_leaderboard(tag: str, league: str | None = None, year: int | None = None,
                    source: str = "property", order: str = "desc",
                    rank_by: str = "count", min_games: int = 10,
                    limit: int | None = None):
    """Rank teams by how often a tag applies.

    source='property' -> one of the 37 overlapping flag columns
    source='game_tag' -> one of the 14 mutually exclusive primary classifications
    source='story_tag' -> one of the 11 composite narrative tags
    """
    if source == "property":
        if tag not in tagmod.TAG_COLS:
            raise HTTPException(404, f"Unknown tag '{tag}'. See /api/tags.")
        pred = f'"{tag}" = ?'
        pred_param = tag
    elif source in ("game_tag", "story_tag"):
        pred = f'"{source}" = ?'
        pred_param = tag
    else:
        raise HTTPException(400, "source must be property, game_tag or story_tag")

    if rank_by not in ("count", "rate"):
        raise HTTPException(400, "rank_by must be count or rate")
    direction = "DESC" if order.lower() == "desc" else "ASC"

    q = f"""
        SELECT team_name, league, year,
               COUNT(*) AS games,
               SUM(CASE WHEN {pred} THEN 1 ELSE 0 END) AS "count",
               ROUND(SUM(CASE WHEN {pred} THEN 1 ELSE 0 END) * 1.0 / COUNT(*), 4) AS rate
        FROM clinical_games
        WHERE 1=1
    """
    params = [pred_param, pred_param]
    if league:
        q += " AND league = ?"
        params.append(league)
    if year is not None:
        q += " AND year = ?"
        params.append(year)

    q += f" GROUP BY team_name, league, year HAVING COUNT(*) >= {int(min_games)}"
    q += f' ORDER BY "{rank_by}" {direction}, team_name'
    if limit:
        q += f" LIMIT {int(limit)}"

    return df_to_records(db().execute(q, params).df())


@app.get("/api/own-goals")
def own_goals(league: str | None = None, year: int | None = None,
              team: str | None = None):
    """Own goals conceded (team_name = the side that scored into its own net)
    and benefited from (opponent_team). Counts are small - a typical team-season
    is 3-4 - so single-season differences are mostly noise. Aggregate across
    seasons before drawing conclusions."""
    where, params = ["result = 'OwnGoal'"], []
    if league:
        where.append("league = ?")
        params.append(league)
    if year is not None:
        where.append("year = ?")
        params.append(year)
    w = " AND ".join(where)

    conceded = db().execute(f"""
        SELECT team_name, league, year, count(*) AS own_goals_conceded
        FROM shots WHERE {w} GROUP BY 1,2,3
    """, params).df()

    benefited = db().execute(f"""
        SELECT opponent_team AS team_name, league, year,
               count(*) AS own_goals_benefited
        FROM shots WHERE {w} GROUP BY 1,2,3
    """, params).df()

    merged = conceded.merge(benefited, on=["team_name", "league", "year"], how="outer")
    merged = merged.fillna({"own_goals_conceded": 0, "own_goals_benefited": 0})
    merged["net"] = merged["own_goals_benefited"] - merged["own_goals_conceded"]

    if team:
        merged = merged[merged["team_name"] == team]

    merged = merged.sort_values("own_goals_conceded", ascending=False)

    league_avg = float(conceded["own_goals_conceded"].mean()) if len(conceded) else 0.0

    return {
        "league_avg_conceded": round(league_avg, 2),
        "caveat": "Own goals are rare (~0.09 per team-match). Single-season "
                  "differences are largely variance, not defensive quality.",
        "rows": df_to_records(merged),
    }


# ---------------------------------------------------------------- players
#
# Reads players_career, built by notebooks/player_analysis.ipynb. Everything
# keys on id, never player_name: 24 names map to more than one player.
#
# Shot volume is meaningless without its positional cohort - 1.0 per 90 is high
# for a defender and low for a forward - so single-player responses always carry
# the distribution alongside the value.

PLAYER_METRICS = {
    "shots_per90":       ("Shots per 90", True),
    "npg_per90":         ("Non-penalty goals per 90", True),
    "npxg_per90":        ("Non-penalty xG per 90", True),
    "np_residual":       ("Finishing residual (npG - npxG)", None),
    "np_residual_per90": ("Finishing residual per 90", None),
    "avg_shot_xg":       ("Average xG per shot", True),
    "np_conversion":     ("Conversion rate", True),
    "xa_per90":          ("xA per 90", True),
    "kp_per90":          ("Key passes per 90", True),
    "xgchain_per90":     ("xGChain per 90", True),
    "xgbuildup_per90":   ("xGBuildup per 90", True),
}


@app.get("/api/players/search")
def player_search(q: str, limit: int = 15):
    df = db().execute("""
        SELECT id, player_name, main_team, main_league, position, minutes, seasons
        FROM players_career
        WHERE lower(player_name) LIKE lower(?)
        ORDER BY minutes DESC LIMIT ?
    """, ["%" + q + "%", limit]).df()
    return df_to_records(df)


@app.get("/api/players/leaderboard")
def player_leaderboard(metric: str = "shots_per90", position: str | None = None,
                       league: str | None = None, team: str | None = None,
                       limit: int = 25, order: str = "desc",
                       min_minutes: int = 2700):
    if metric not in PLAYER_METRICS:
        raise HTTPException(404, f"Unknown metric. Allowed: {sorted(PLAYER_METRICS)}")
    label, higher_better = PLAYER_METRICS[metric]
    direction = "DESC" if order.lower() == "desc" else "ASC"

    q = f"""SELECT id, player_name, main_team, main_league, position,
                   minutes, np_shots, np_goals, key_passes, assists, position_ambiguous,
                   "{metric}" AS value,
                   "{metric}_pct" AS percentile
            FROM players_career
            WHERE "{metric}" IS NOT NULL AND minutes >= ?"""
    params = [min_minutes]
    if position:
        q += " AND position = ?"
        params.append(position)
    if league:
        q += " AND main_league = ?"
        params.append(league)
    if team:
        q += " AND main_team = ?"
        params.append(team)
    q += f' ORDER BY "{metric}" {direction} LIMIT {int(limit)}'

    return {
        "metric": metric, "label": label, "higher_is_better": higher_better,
        "rows": df_to_records(db().execute(q, params).df()),
    }


@app.get("/api/players/distribution")
def player_distribution(metric: str = "shots_per90", position: str = "F",
                        min_minutes: int = 2700):
    """Full cohort values for one metric, for plotting a histogram."""
    if metric not in PLAYER_METRICS:
        raise HTTPException(404, f"Unknown metric. Allowed: {sorted(PLAYER_METRICS)}")
    df = db().execute(f"""
        SELECT "{metric}" AS value FROM players_career
        WHERE position = ? AND "{metric}" IS NOT NULL AND minutes >= ?
    """, [position, min_minutes]).df()
    return {"metric": metric, "position": position,
            "label": PLAYER_METRICS[metric][0],
            "n": len(df),
            "values": df["value"].tolist()}


@app.get("/api/players/{player_id}")
def player_detail(player_id: int):
    df = db().execute("SELECT * FROM players_career WHERE id = ?", [player_id]).df()
    if not len(df):
        raise HTTPException(404, f"No player with id {player_id}")
    row = df_to_records(df)[0]

    pos = row["position"]
    cohort = db().execute("""
        SELECT count(*) n,
               round(quantile_cont(shots_per90, 0.10), 3) shots_p10,
               round(median(shots_per90), 3)              shots_p50,
               round(quantile_cont(shots_per90, 0.90), 3) shots_p90,
               round(median(np_residual_per90), 4)        resid_p50
        FROM players_career WHERE position = ?
    """, [pos]).df()

    return {"player": row, "cohort": df_to_records(cohort)[0]}


@app.get("/api/teams/{team_name}/squad")
def team_squad(team_name: str):
    df = db().execute("""
        SELECT id, player_name, position, pos_share, minutes, seasons, games,
               np_shots, np_goals, np_residual, shots_per90, shots_per90_pct,
               xa_per90, footedness, finishing_verdict, volume_verdict,
               creation_verdict, trend_verdict
        FROM players_career WHERE main_team = ?
        ORDER BY minutes DESC
    """, [team_name]).df()
    return df_to_records(df)


@app.get("/api/players/metrics")
def player_metrics():
    return [{"metric": k, "label": v[0], "higher_is_better": v[1]}
            for k, v in PLAYER_METRICS.items()]
