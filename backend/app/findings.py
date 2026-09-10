# Retrieval over data/chroma. Filter first, embed second.
#
# The findings files are templated: every league's counter_attack block has
# near-identical prose and differs only in numbers, which sentence embeddings
# barely encode. Unfiltered similarity across those five returns a 0.02 spread
# - noise. So comparison questions retrieve ALL matching chunks and let the
# responder compare, rather than trusting rank order.
from __future__ import annotations

from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

CHROMA_DIR = Path(__file__).resolve().parents[2] / "data" / "chroma"
COLLECTION = "ontarget_findings"

TOPICS = {"xg_analysis", "pressing", "counter_attack", "seasonal_trends", "novel", "players"}

_col = None


def col():
    global _col
    if _col is None:
        if not CHROMA_DIR.exists():
            raise RuntimeError(
                str(CHROMA_DIR) + " missing - run `python scripts/build_chroma.py`")
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2")
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _col = client.get_collection(COLLECTION, embedding_function=ef)
    return _col


def _where(team=None, league=None, topic=None, kind=None, player_id=None):
    clauses = []
    if player_id is not None:
        clauses.append({"player_id": player_id})
    if team:
        clauses.append({"team": team})
    if league:
        clauses.append({"league": league})
    if topic:
        clauses.append({"topic": topic})
    if kind:
        clauses.append({"kind": kind})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def search_findings(query, team=None, league=None, topic=None,
                    compare_leagues=False, player_id=None, n=4):
    """Retrieve finding chunks.

    team     -> that team's block, exact
    league+topic -> that league's block for the topic
    compare_leagues -> ALL five league blocks for the topic (comparison mode)
    none of the above -> open similarity search
    """
    if compare_leagues:
        if topic not in TOPICS:
            raise ValueError("compare_leagues needs a valid topic")
        where = _where(topic=topic, kind="league")
        n = 5

    elif player_id is not None:
        where = _where(player_id=player_id)
        n = 1

    elif team:
        # kind filter matters now: a team name also appears on player blocks.
        where = _where(team=team, topic=topic, kind="team")
        n = 1

    else:
        where = _where(league=league, topic=topic)

    r = col().query(query_texts=[query], n_results=n, where=where)

    out = []
    for i in range(len(r["documents"][0])):
        meta = r["metadatas"][0][i]
        out.append({
            "text": r["documents"][0][i],
            "team": meta.get("team"),
            "player": meta.get("player"),
            "player_id": meta.get("player_id"),
            "position": meta.get("position"),
            "position_ambiguous": bool(meta.get("position_ambiguous", False)),
            "league": meta.get("league"),
            "topic": meta.get("topic"),
            "kind": meta.get("kind"),
            "thin_sample": bool(meta.get("thin_sample", False)),
            "seasons_tracked": meta.get("seasons_tracked"),
            "distance": r["distances"][0][i],
            "source": meta.get("source"),
        })
    return out
