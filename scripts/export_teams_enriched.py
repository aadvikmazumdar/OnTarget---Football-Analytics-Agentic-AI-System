"""Rebuild data/processed/teams_enriched.csv with the columns features.py needs.
Reproduces notebook cells 0, 1, 9, 12, 58."""
from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"

teams_df = pd.read_csv(P / "teams.csv")
clinical_df = pd.read_csv(P / "clinical_games.csv")
matches_meta = pd.read_csv(P / "matches.csv")

# --- cell 0
teams_df["date"] = pd.to_datetime(teams_df["date"]).dt.normalize()
teams_df = teams_df.sort_values(["team_name", "date"]).reset_index(drop=True)
teams_df["matchday"] = teams_df.groupby(["team_name", "league", "year"]).cumcount() + 1

# --- cell 1
def parse_ppda(val):
    d = ast.literal_eval(val) if isinstance(val, str) else val
    return d["att"] / d["def"] if d["def"] != 0 else np.nan

teams_df["ppda_value"] = teams_df["ppda"].apply(parse_ppda)
teams_df["ppda_allowed_value"] = teams_df["ppda_allowed"].apply(parse_ppda)
teams_df.loc[teams_df["ppda_value"] > 50, "ppda_value"] = np.nan
teams_df.loc[teams_df["ppda_allowed_value"] > 50, "ppda_allowed_value"] = np.nan

# --- cell 3 (match_id join)
matches_meta["datetime"] = pd.to_datetime(matches_meta["datetime"])
matches_meta["date"] = matches_meta["datetime"].dt.normalize()

home_lookup = matches_meta[["match_id", "date", "league", "year", "home_team"]].rename(
    columns={"home_team": "team_name"})
home_lookup["h_a"] = "h"
away_lookup = matches_meta[["match_id", "date", "league", "year", "away_team"]].rename(
    columns={"away_team": "team_name"})
away_lookup["h_a"] = "a"
match_id_long = pd.concat([home_lookup, away_lookup], ignore_index=True)

teams_df = teams_df.merge(
    match_id_long, on=["date", "league", "year", "team_name", "h_a"], how="left")
assert teams_df["match_id"].isna().sum() == 0, "unmatched match_id rows"
assert len(teams_df) == 17964, f"row count changed: {len(teams_df)}"

# --- cell 9
pts_map = {"w": 3, "d": 1, "l": 0}
teams_df["match_pts"] = teams_df["result"].map(pts_map)
teams_df["pts_to_date"] = teams_df.groupby(
    ["team_name", "league", "year"])["match_pts"].transform(lambda s: s.shift(1).cumsum())
teams_df["rank_to_date"] = teams_df.groupby(
    ["league", "year", "matchday"])["pts_to_date"].rank(ascending=False, method="first")

# --- cell 12
xgd_lookup = clinical_df[["match_id", "team_name", "match_xGD"]].drop_duplicates(
    subset=["match_id", "team_name"])
teams_df = teams_df.merge(xgd_lookup, on=["match_id", "team_name"], how="left")
assert len(teams_df) == 17964, f"match_xGD merge duplicated rows: {len(teams_df)}"

# --- cell 58, widened
teams_export = teams_df.merge(
    matches_meta[["match_id", "home_team", "away_team"]], on="match_id", how="left")
teams_export["opponent"] = np.where(
    teams_export["h_a"] == "h", teams_export["away_team"], teams_export["home_team"])

export_cols = ["team_name", "league", "year", "date", "match_id", "opponent", "h_a",
               "xG", "xGA", "scored", "missed", "deep", "deep_allowed",
               "result", "matchday", "match_pts", "match_xGD",
               "rank_to_date", "pts_to_date",
               "ppda_value", "ppda_allowed_value"]

missing = [c for c in export_cols if c not in teams_export.columns]
assert not missing, f"missing from source: {missing}"

teams_export = teams_export[export_cols]
teams_export.to_csv(P / "teams_enriched.csv", index=False)

print(f"wrote {teams_export.shape[0]:,} rows x {teams_export.shape[1]} cols")
print(teams_export.columns.tolist())
