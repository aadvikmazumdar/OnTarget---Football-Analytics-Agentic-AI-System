"""Tag vocabulary, derived from the data at startup. Never hardcode a tag list."""
from __future__ import annotations

# Columns that are VARCHAR and self-named but are NOT match tags.
_NOT_TAGS = {
    "team_name", "league", "result", "h_a", "home_team", "away_team",
    "game_tag", "story_tag", "top_player_name", "derby_name",
}

TAG_COLS: list[str] = []


def load_tags(con) -> list[str]:
    """A tag column is a VARCHAR holding its own name (e.g. 'heist'/'not_heist')."""
    global TAG_COLS

    varchar_cols = [
        r[0] for r in con.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'clinical_games' AND data_type = 'VARCHAR'
        """).fetchall()
    ]

    found = []
    for c in varchar_cols:
        if c in _NOT_TAGS:
            continue
        n = con.execute(
            f'SELECT count(*) FROM clinical_games WHERE "{c}" = ?', [c]
        ).fetchone()[0]
        if n > 0:
            found.append(c)

    TAG_COLS = sorted(found)
    return TAG_COLS