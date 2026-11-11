"""Model A feature builder.

Extracted from notebooks/prediction_models.ipynb so training and serving share one
implementation. The notebook imports from here and retrains; the API calls
build_features() for a single fixture. Two copies of this logic would drift
silently and degrade predictions with nothing failing.

Target is model_h2h / feature_cols_h2h (44 features) - 51.0% accuracy,
log-loss 1.008 - not the 39-feature final_model.

Three things that are easy to get wrong and are asserted here:

1. rank_to_date is CROSS-SECTIONAL. It ranks a team's points against every other
   team in the league at the same matchday number, so a single fixture cannot be
   featurised from two teams' rows alone - the whole league-season is needed.

2. Rank ties break with method='first', which depends on row order. The training
   frame is sorted by (team_name, date), so ties resolve alphabetically. A
   different sort here means silently different ranks and drifting predictions.

3. Every rolling and expanding feature is computed from matches strictly EARLIER
   than the fixture. In training that is shift(1) before windowing; at inference
   it is the as_of filter. The golden test proves the two paths agree.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- spec

ROLL_METRICS = [
    "ppda_value", "ppda_allowed_value",
    "scored", "missed",
    "xG", "xGA",
    "deep", "deep_allowed",
]

GROUP_COLS = ["team_name", "league", "year"]
SORT_COLS = ["team_name", "date"]

ROLL_WINDOW = 5
ROLL_MIN = 5
EXPANDING_MIN = 3

H2H_COLS = [
    "h2h_matches",
    "h2h_this_home_win_rate",
    "h2h_draw_rate",
    "h2h_this_away_win_rate",
    "h2h_xg_diff",
]

# Imputed when the pair has never met. h2h_matches stays 0 - that is already
# meaningful and needs no fill.
H2H_DEFAULTS = {
    "h2h_this_home_win_rate": 0.333,
    "h2h_draw_rate": 0.333,
    "h2h_this_away_win_rate": 0.333,
    "h2h_xg_diff": 0.0,
}

PTS_MAP = {"w": 3, "d": 1, "l": 0}

FEATURE_COLS = (
    [f"home_{m}_roll5" for m in ROLL_METRICS]
    + [f"away_{m}_roll5" for m in ROLL_METRICS]
    + [f"home_{m}_expanding" for m in ROLL_METRICS]
    + [f"away_{m}_expanding" for m in ROLL_METRICS]
    + [
        "home_rank", "away_rank", "rank_gap",
        "home_rolling_pts_5", "away_rolling_pts_5",
        "home_form_xGD_divergence", "away_form_xGD_divergence",
    ]
    + H2H_COLS
)

assert len(FEATURE_COLS) == 44, f"expected 44 features, got {len(FEATURE_COLS)}"

TARGET_NAMES = ["away_win", "draw", "home_win"]  # 0, 1, 2

MODEL_DIR = Path(__file__).resolve().parents[2] / "models"
MODEL_PATH = MODEL_DIR / "match_outcome.joblib"
FEATURE_NAMES_PATH = MODEL_DIR / "feature_names.json"

XGB_PARAMS = dict(
    objective="multi:softprob",
    num_class=3,
    max_depth=3,
    learning_rate=0.03,
    n_estimators=200,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    eval_metric="mlogloss",
)


# --------------------------------------------------------------------- team frame

def load_teams(con) -> pd.DataFrame:
    """teams_enriched, sorted and with matchday. The sort is load-bearing: rank
    ties break by row order, so a different sort changes ranks."""
    df = con.execute("""
        SELECT team_name, league, year, date, match_id, opponent, h_a,
               xG, xGA, scored, missed, deep, deep_allowed,
               result, match_pts, match_xGD,
               ppda_value, ppda_allowed_value
        FROM teams
    """).df()

    df["date"] = pd.to_datetime(df["date"]).dt.normalize()

    # A team playing twice on one date makes row order ambiguous: the batch path
    # shifts by row, the serving path filters by date, and they silently disagree.
    dup = df.duplicated(GROUP_COLS + ["date"], keep=False)
    assert not dup.any(), (
        f"{int(dup.sum())} team-rows share a (team, league, year, date) with another "
        f"match - rolling features would differ between training and serving:\n"
        f"{df.loc[dup, GROUP_COLS + ['date', 'match_id']].head(10).to_string()}"
    )

    df = df.sort_values(SORT_COLS).reset_index(drop=True)
    df["matchday"] = df.groupby(GROUP_COLS).cumcount() + 1

    # match_pts is exported from the notebook, but recompute defensively - a stale
    # export would silently shift every points-based feature.
    recomputed = df["result"].map(PTS_MAP)
    if df["match_pts"].isna().any() or not recomputed.equals(
        df["match_pts"].astype(recomputed.dtype)
    ):
        df["match_pts"] = recomputed

    return df


def add_point_in_time(df: pd.DataFrame) -> pd.DataFrame:
    """Rolling and expanding features, each shifted so a match never sees itself."""
    df = df.copy()
    grouped = df.groupby(GROUP_COLS)

    for metric in ROLL_METRICS:
        df[f"{metric}_roll{ROLL_WINDOW}"] = grouped[metric].transform(
            lambda s: s.shift(1).rolling(window=ROLL_WINDOW, min_periods=ROLL_MIN).mean()
        )
        df[f"{metric}_expanding"] = grouped[metric].transform(
            lambda s: s.shift(1).expanding(min_periods=EXPANDING_MIN).mean()
        )

    grouped = df.groupby(GROUP_COLS)
    df["pts_to_date"] = grouped["match_pts"].transform(lambda s: s.shift(1).cumsum())
    df["rolling_pts_5"] = grouped["match_pts"].transform(
        lambda s: s.shift(1).rolling(5, min_periods=5).sum()
    )
    df["rolling_xGD_5"] = grouped["match_xGD"].transform(
        lambda s: s.shift(1).rolling(5, min_periods=5).sum()
    )
    df["form_xGD_divergence"] = df["rolling_pts_5"] - df["rolling_xGD_5"]

    # Cross-sectional: points at equal games played, ranked within the league.
    # Not a league table as of the calendar date - teams reach matchday 10 on
    # different days - but it is the better football quantity and it is what the
    # model was trained on.
    df["rank_to_date"] = df.groupby(["league", "year", "matchday"])["pts_to_date"].rank(
        ascending=False, method="first"
    )
    return df


def build_team_frame(con) -> pd.DataFrame:
    df = add_point_in_time(load_teams(con))
    assert df[SORT_COLS].reset_index(drop=True).equals(
        df.sort_values(SORT_COLS)[SORT_COLS].reset_index(drop=True)
    ), "team frame lost its sort - rank ties will differ from training"
    return df


# -------------------------------------------------------------------------- H2H

def _pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted([a, b]))


def compute_h2h(matches: pd.DataFrame) -> pd.DataFrame:
    """One chronological pass. Each meeting is appended to history AFTER being
    used, so a match only ever sees earlier meetings. Past meetings are
    re-expressed from the CURRENT home team's perspective, which is why this
    cannot be a simple groupby."""
    matches = matches.sort_values("date").reset_index(drop=True)
    history: dict[tuple, list] = {}
    records = []

    for _, row in matches.iterrows():
        key = _pair_key(row["home_team"], row["away_team"])
        past = history.get(key, [])

        if not past:
            records.append({
                "match_id": row["match_id"], "h2h_matches": 0,
                "h2h_this_home_win_rate": np.nan, "h2h_draw_rate": np.nan,
                "h2h_this_away_win_rate": np.nan, "h2h_xg_diff": np.nan,
            })
        else:
            this_home, this_away = row["home_team"], row["away_team"]
            home_wins = sum(1 for m in past if m["winner"] == this_home)
            draws = sum(1 for m in past if m["winner"] == "draw")
            away_wins = len(past) - home_wins - draws
            records.append({
                "match_id": row["match_id"],
                "h2h_matches": len(past),
                "h2h_this_home_win_rate": home_wins / len(past),
                "h2h_draw_rate": draws / len(past),
                "h2h_this_away_win_rate": away_wins / len(past),
                "h2h_xg_diff": float(
                    np.mean([m["xg"][this_home] for m in past])
                    - np.mean([m["xg"][this_away] for m in past])
                ),
            })

        winner = (row["home_team"] if row["target"] == 2
                  else row["away_team"] if row["target"] == 0 else "draw")
        past.append({
            "winner": winner,
            "xg": {row["home_team"]: row["home_xG"], row["away_team"]: row["away_xG"]},
        })
        history[key] = past

    return pd.DataFrame(records)


def h2h_asof(con, home: str, away: str, as_of: pd.Timestamp) -> dict:
    """Same quantities as compute_h2h, for a fixture that is not in the table.

    Compares against the normalised date, matching build_match_frame - otherwise a
    19:15 kickoff on the as_of date would be counted here and excluded there.
    """
    past = con.execute("""
        SELECT home_team, away_team, home_goals, away_goals, home_xG, away_xG
        FROM matches
        WHERE date_trunc('day', datetime) < ?
          AND ((home_team = ? AND away_team = ?) OR (home_team = ? AND away_team = ?))
        ORDER BY datetime
    """, [as_of, home, away, away, home]).df()

    if not len(past):
        return {"h2h_matches": 0, **H2H_DEFAULTS}

    home_wins = draws = 0
    xg_home, xg_away = [], []
    for _, m in past.iterrows():
        if m["home_goals"] > m["away_goals"]:
            winner = m["home_team"]
        elif m["home_goals"] < m["away_goals"]:
            winner = m["away_team"]
        else:
            winner = "draw"
        if winner == home:
            home_wins += 1
        elif winner == "draw":
            draws += 1
        xg_home.append(m["home_xG"] if m["home_team"] == home else m["away_xG"])
        xg_away.append(m["home_xG"] if m["home_team"] == away else m["away_xG"])

    n = len(past)
    return {
        "h2h_matches": n,
        "h2h_this_home_win_rate": home_wins / n,
        "h2h_draw_rate": draws / n,
        "h2h_this_away_win_rate": (n - home_wins - draws) / n,
        "h2h_xg_diff": float(np.mean(xg_home) - np.mean(xg_away)),
    }


# ------------------------------------------------------------------ match frame

def build_match_frame(con) -> pd.DataFrame:
    """Full training frame: one row per match, 44 features plus target."""
    teams = build_team_frame(con)

    per_side = (
        [f"{m}_roll{ROLL_WINDOW}" for m in ROLL_METRICS]
        + [f"{m}_expanding" for m in ROLL_METRICS]
        + ["rank_to_date", "rolling_pts_5", "form_xGD_divergence"]
    )

    def side(h_a: str, prefix: str, team_col: str) -> pd.DataFrame:
        rows = teams[teams["h_a"] == h_a]
        return rows[["match_id", "league", "year", "team_name", "result"] + per_side].rename(
            columns={
                "team_name": team_col,
                "result": f"{prefix}_result",
                "rank_to_date": f"{prefix}_rank",
                **{c: f"{prefix}_{c}" for c in per_side if c != "rank_to_date"},
            }
        )

    matches = side("h", "home", "home_team").merge(
        side("a", "away", "away_team"), on=["match_id", "league", "year"], how="inner"
    )
    assert len(matches) == len(teams) // 2, (
        f"match join changed row count: {len(matches)} from {len(teams)} team-rows"
    )

    matches["rank_gap"] = matches["away_rank"] - matches["home_rank"]

    meta = con.execute("""
        SELECT match_id, datetime AS date, home_goals, away_goals, home_xG, away_xG
        FROM matches
    """).df()
    meta["date"] = pd.to_datetime(meta["date"]).dt.normalize()

    matches = matches.merge(meta, on="match_id", how="left")
    assert matches["date"].notna().all(), "match_id join to matches table missed rows"

    matches["target"] = np.select(
        [matches["home_goals"] > matches["away_goals"],
         matches["home_goals"] == matches["away_goals"]],
        [2, 1], default=0,
    )

    matches = matches.sort_values("date").reset_index(drop=True)
    matches = matches.merge(compute_h2h(matches), on="match_id", how="left")
    for col, fill in H2H_DEFAULTS.items():
        matches[col] = matches[col].fillna(fill)

    return matches


def train_test_split_by_date(matches: pd.DataFrame, quantile: float = 0.8):
    """Chronological, no shuffling. The 0.8 quantile lands on 2024-05-19, which is
    a season boundary - the test set is effectively the whole 2024 season."""
    split_date = matches["date"].quantile(quantile)
    train = matches[matches["date"] < split_date].copy()
    test = matches[matches["date"] >= split_date].copy()
    return train, test, split_date


# ------------------------------------------------------------------- inference

def _team_history(teams: pd.DataFrame, team: str, as_of: pd.Timestamp,
                  league: str | None, year: int | None) -> pd.DataFrame:
    h = teams[(teams["team_name"] == team) & (teams["date"] < as_of)]
    if league:
        h = h[h["league"] == league]
    if year is not None:
        h = h[h["year"] == year]
    return h.sort_values("date")


def _side_features(hist: pd.DataFrame) -> dict:
    """Trailing features from matches strictly before the fixture.

    Equivalent to reading the shifted transform at the next matchday - no shift
    is applied because the fixture itself is not in hist.
    """
    f = {}
    n = len(hist)

    for metric in ROLL_METRICS:
        vals = hist[metric]
        win = vals.tail(ROLL_WINDOW)
        # Match pandas rolling/expanding(min_periods=k): the window needs k VALID
        # values, not k rows. Masked PPDA outliers are NaN, and counting rows would
        # return a mean over fewer values than training ever allowed.
        f[f"{metric}_roll{ROLL_WINDOW}"] = (
            float(win.mean()) if len(win) == ROLL_WINDOW and win.notna().sum() >= ROLL_MIN
            else np.nan
        )
        f[f"{metric}_expanding"] = (
            float(vals.mean()) if vals.notna().sum() >= EXPANDING_MIN else np.nan
        )

    f["pts_to_date"] = float(hist["match_pts"].sum()) if n else np.nan
    f["matchday"] = n + 1

    if n >= 5:
        pts5 = float(hist["match_pts"].tail(5).sum())
        xgd5 = float(hist["match_xGD"].tail(5).sum())
        f["rolling_pts_5"] = pts5
        f["form_xGD_divergence"] = pts5 - xgd5
    else:
        f["rolling_pts_5"] = np.nan
        f["form_xGD_divergence"] = np.nan

    return f


def _rank_at(teams: pd.DataFrame, league: str, year: int, matchday: int,
             team: str, pts: float) -> tuple[float, int]:
    """Rank this team's points against every team in the league at the same
    matchday number. Returns (rank, matchday_used).

    If nobody has reached that matchday - a fixture as-of the end of a season -
    falls back to the highest available matchday, i.e. final standings. The
    caller is told which was used, because rank_gap is the model's single
    strongest feature and a fallback is worth surfacing.
    """
    season = teams[(teams["league"] == league) & (teams["year"] == year)]
    if not len(season):
        return np.nan, matchday

    available = season["matchday"].max()
    md = matchday if matchday <= available else int(available)

    cohort = season[season["matchday"] == md][["team_name", "pts_to_date", "match_pts"]].copy()
    if not len(cohort):
        return np.nan, md
    if md != matchday:
        cohort["pts_to_date"] = cohort["pts_to_date"] + cohort["match_pts"]
    cohort = cohort[["team_name", "pts_to_date"]]

    cohort = cohort[cohort["team_name"] != team]
    cohort = pd.concat(
        [cohort, pd.DataFrame([{"team_name": team, "pts_to_date": pts}])],
        ignore_index=True,
    )
    # Ties break by row order in training, and the frame is sorted by team_name.
    cohort = cohort.sort_values("team_name").reset_index(drop=True)
    cohort["rank"] = cohort["pts_to_date"].rank(ascending=False, method="first")

    hit = cohort[cohort["team_name"] == team]
    return (float(hit["rank"].iloc[0]) if len(hit) else np.nan), md


def build_features(con, home: str, away: str, as_of=None,
                   league: str | None = None, year: int | None = None,
                   teams: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """Feature row for one fixture.

    as_of defaults to the day after both teams' last played match, which makes
    this a hypothetical next fixture. Pass a historical date to replay a real
    match - the caller can then join the actual result for display.

    Returns (single-row DataFrame in FEATURE_COLS order, context dict).
    """
    if teams is None:
        teams = build_team_frame(con)

    known = set(teams["team_name"].unique())
    for t in (home, away):
        if t not in known:
            raise ValueError(f"unknown team: {t!r}")

    if as_of is None:
        last = teams[teams["team_name"].isin([home, away])]["date"].max()
        as_of = pd.Timestamp(last) + pd.Timedelta(days=1)
    as_of = pd.Timestamp(as_of).normalize()

    if league is None or year is None:
        recent = teams[(teams["team_name"] == home) & (teams["date"] < as_of)]
        if not len(recent):
            raise ValueError(f"no matches for {home!r} before {as_of.date()}")
        last_row = recent.sort_values("date").iloc[-1]
        league = league or last_row["league"]
        year = year if year is not None else int(last_row["year"])

    home_hist = _team_history(teams, home, as_of, league, year)
    away_hist = _team_history(teams, away, as_of, league, year)

    hf = _side_features(home_hist)
    af = _side_features(away_hist)

    home_rank, home_md = _rank_at(teams, league, year, hf["matchday"], home, hf["pts_to_date"])
    away_rank, away_md = _rank_at(teams, league, year, af["matchday"], away, af["pts_to_date"])

    row: dict = {}
    for metric in ROLL_METRICS:
        for suffix in (f"_roll{ROLL_WINDOW}", "_expanding"):
            row[f"home_{metric}{suffix}"] = hf[f"{metric}{suffix}"]
            row[f"away_{metric}{suffix}"] = af[f"{metric}{suffix}"]

    row["home_rank"] = home_rank
    row["away_rank"] = away_rank
    row["rank_gap"] = (
        (away_rank - home_rank)
        if pd.notna(home_rank) and pd.notna(away_rank) else np.nan
    )
    row["home_rolling_pts_5"] = hf["rolling_pts_5"]
    row["away_rolling_pts_5"] = af["rolling_pts_5"]
    row["home_form_xGD_divergence"] = hf["form_xGD_divergence"]
    row["away_form_xGD_divergence"] = af["form_xGD_divergence"]
    row.update(h2h_asof(con, home, away, as_of))

    X = pd.DataFrame([row])[FEATURE_COLS]

    context = {
        "home_team": home, "away_team": away,
        "as_of": as_of.date().isoformat(),
        "league": league, "year": int(year),
        "home_matches_played": len(home_hist),
        "away_matches_played": len(away_hist),
        "home_matchday": hf["matchday"], "away_matchday": af["matchday"],
        "rank_matchday_used": {"home": home_md, "away": away_md},
        "rank_fallback": bool(home_md != hf["matchday"] or away_md != af["matchday"]),
        "missing_features": [c for c in FEATURE_COLS if pd.isna(X.iloc[0][c])],
    }
    return X, context


# ------------------------------------------------------------------- artefacts

# ------------------------------------------------------------------- artefacts

def save_model(model, path: Path | None = None) -> None:
    import joblib
    # Refuse to save a model that was not trained on exactly FEATURE_COLS, in
    # order. Otherwise feature_names.json (written from FEATURE_COLS) would
    # vouch for a model it does not describe, and load_model would pass.
    names = list(getattr(model, "feature_names_in_", []))
    if names != FEATURE_COLS:
        raise RuntimeError(
            f"model was trained on {len(names)} columns, not FEATURE_COLS "
            f"({len(FEATURE_COLS)}) - refusing to save"
        )
    path = path or MODEL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    FEATURE_NAMES_PATH.write_text(json.dumps(FEATURE_COLS, indent=2))


def load_model(path: Path | None = None):
    """Loads the model and hard-fails if the saved feature order no longer matches
    FEATURE_COLS. Silent column reordering is the failure mode this prevents:
    XGBoost accepts the frame and returns plausible, wrong probabilities."""
    import joblib
    path = path or MODEL_PATH
    if not path.exists():
        raise RuntimeError(f"{path} missing - retrain from the notebook")
    saved = json.loads(FEATURE_NAMES_PATH.read_text())
    if saved != FEATURE_COLS:
        first_bad = next(
            (i for i, (a, b) in enumerate(zip(saved, FEATURE_COLS)) if a != b), "length"
        )
        raise RuntimeError(
            "feature order drift between saved model and features.py:\n"
            f"  saved: {len(saved)} cols\n  current: {len(FEATURE_COLS)} cols\n"
            f"  first mismatch at {first_bad}"
        )
    return joblib.load(path)


def predict(con, home: str, away: str, as_of=None, model=None,
            teams: pd.DataFrame | None = None) -> dict:
    model = model or load_model()
    X, ctx = build_features(con, home, away, as_of=as_of, teams=teams)
    proba = model.predict_proba(X)[0]
    return {
        **ctx,
        "probabilities": {
            "away_win": float(proba[0]),
            "draw": float(proba[1]),
            "home_win": float(proba[2]),
        },
        "predicted": TARGET_NAMES[int(np.argmax(proba))],
    }