"""Build data/ontarget.duckdb from data/processed/. Rerun after any notebook re-export."""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
DB_PATH = ROOT / "data" / "ontarget.duckdb"

TABLES = {
    "matches":            "matches.csv",
    "teams":              "teams_enriched.csv",
    "teams_raw":          "teams.csv",
    "shots":              "shots_enriched.csv",
    "clinical_games":     "clinical_games.csv",
    "team_season":        "team_season.csv",
    "team_season_ha":     "team_season_ha.csv",
    "consistency":        "consistency.csv",
    "players":            "players_enriched.csv",
    "rosters":            "rosters.csv",
    "league_fingerprint": "league_fingerprint.csv",
}

REQUIRED = {
    "teams": ["team_name", "league", "year", "date", "match_id", "h_a", "opponent",
              "xG", "xGA", "scored", "missed", "deep", "deep_allowed",
              "result", "matchday", "match_pts", "match_xGD",
              "rank_to_date", "pts_to_date", "ppda_value", "ppda_allowed_value"],
    "matches": ["match_id", "datetime", "league", "year", "home_team", "away_team",
                "home_goals", "away_goals", "home_xG", "away_xG"],
    "clinical_games": ["match_id", "team_name", "date", "year", "game_tag", "story_tag"],
}


def build():
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = duckdb.connect(str(DB_PATH))

    for table, fname in TABLES.items():
        path = PROCESSED / fname
        if not path.exists():
            print(f"  SKIP  {table:<20} ({fname} not found)")
            continue
        con.execute(
            f"CREATE TABLE {table} AS "
            f"SELECT * FROM read_csv_auto('{path}', sample_size=-1)"
        )
        n = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        print(f"  ok    {table:<20} {n:>8,} rows")

    # indexes on the hot join/filter keys
    for tbl, col in [("teams", "team_name"), ("teams", "match_id"),
                     ("shots", "team_name"), ("shots", "match_id"),
                     ("clinical_games", "team_name"), ("clinical_games", "match_id"),
                     ("matches", "match_id")]:
        try:
            con.execute(f"CREATE INDEX idx_{tbl}_{col} ON {tbl}({col})")
        except Exception as e:
            print(f"  warn  index {tbl}.{col}: {e}")

    problems = []
    for table, cols in REQUIRED.items():
        have = {r[0] for r in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
            [table]).fetchall()}
        if not have:
            problems.append(f"{table}: table missing entirely")
            continue
        missing = [c for c in cols if c not in have]
        if missing:
            problems.append(f"{table}: missing {missing}")

    from sys import path as _p
    _p.insert(0, str(ROOT / "backend"))
    from app.tags import load_tags
    tags = load_tags(con)
    print(f"\n  {len(tags)} tag columns detected")
    print("  " + ", ".join(tags))

    con.close()

    if problems:
        print("\nSCHEMA CHECK FAILED")
        for p in problems:
            print("  " + p)
        sys.exit(1)
    print(f"\nok -> {DB_PATH}")


if __name__ == "__main__":
    build()