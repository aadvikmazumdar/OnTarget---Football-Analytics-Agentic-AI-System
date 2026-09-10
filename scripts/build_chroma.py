# Parse data/rag_findings/ into Chroma.
# Team blocks and league blocks are separate chunk kinds; metadata carries
# team/league/topic so retrieval can filter deterministically before falling
# back to embedding similarity. The files are templated - every league's
# pressing block has near-identical structure - so pure vector search
# confuses them. Filter first.
from __future__ import annotations

import re
import shutil
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

ROOT = Path(__file__).resolve().parents[1]
FINDINGS = ROOT / "data" / "rag_findings"
CHROMA_DIR = ROOT / "data" / "chroma"
COLLECTION = "ontarget_findings"

LEAGUES = ["premier_league", "la_liga", "serie_a", "bundesliga", "ligue_1"]
TOPICS = ["xg_analysis", "pressing", "counter_attack", "seasonal_trends", "players"]


def parse_filename(name):
    # xg_analysis_premier_league.txt -> (xg_analysis, premier_league)
    stem = name.replace(".txt", "")
    if stem == "novel_findings":
        return "novel", None
    for topic in TOPICS:
        if stem.startswith(topic + "_"):
            league = stem[len(topic) + 1:]
            return topic, (league if league in LEAGUES else None)
    return None, None


def split_xg_analysis(text):
    # Return (league summary header, list of team blocks)
    if "TEAM PROFILES:" in text:
        header, body = text.split("TEAM PROFILES:", 1)
    else:
        return text.strip(), []
    blocks = [b.strip() for b in body.split("---") if "TEAM:" in b]
    return header.strip(), blocks


def split_players(text):
    # Return (league summary header, list of player blocks)
    if "PLAYER PROFILES:" in text:
        header, body = text.split("PLAYER PROFILES:", 1)
    else:
        return text.strip(), []
    blocks = [b.strip() for b in body.split("---") if "PLAYER:" in b]
    return header.strip(), blocks


def player_metadata(block):
    meta = {}
    m = re.search(r"PLAYER:\s*([^|]+?)\s*\|", block)
    if m:
        meta["player"] = m.group(1).strip()
    m = re.search(r"ID:\s*(\d+)", block)
    if m:
        meta["player_id"] = int(m.group(1))
    m = re.search(r"LEAGUE:\s*([a-z_0-9]+)", block)
    if m:
        meta["league"] = m.group(1).strip()
    m = re.search(r"TEAM:\s*([^|\n]+)", block)
    if m:
        meta["team"] = m.group(1).strip()
    m = re.search(r"POSITION:\s*([A-Z]+)", block)
    if m:
        meta["position"] = m.group(1).strip()
    meta["position_ambiguous"] = "AMBIGUOUS" in block
    m = re.search(r"MINUTES:\s*(\d+)", block)
    if m:
        meta["minutes"] = int(m.group(1))
    m = re.search(r"VERDICT:\s*(.+)", block)
    if m:
        meta["verdict"] = m.group(1).strip()[:200]
    return meta


def team_metadata(block):
    meta = {}
    m = re.search(r"TEAM:\s*([^|]+?)\s*\|", block)
    if m:
        meta["team"] = m.group(1).strip()
    m = re.search(r"LEAGUE:\s*([a-z_0-9]+)", block)
    if m:
        meta["league"] = m.group(1).strip()
    m = re.search(r"SEASONS TRACKED:\s*(\d+)", block)
    if m:
        meta["seasons_tracked"] = int(m.group(1))
    m = re.search(r"SAMPLE:\s*(\w+)", block)
    if m:
        meta["sample"] = m.group(1).strip()
        meta["thin_sample"] = m.group(1).strip() == "single_season"
    m = re.search(r"VERDICT:\s*(.+)", block)
    if m:
        meta["verdict"] = m.group(1).strip()[:200]
    return meta


def build():
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    col = client.create_collection(name=COLLECTION, embedding_function=ef,
                                   metadata={"hnsw:space": "cosine"})

    docs, metas, ids = [], [], []

    for path in sorted(FINDINGS.glob("*.txt")):
        topic, league = parse_filename(path.name)
        if topic is None:
            print("  skip (unrecognised) " + path.name)
            continue
        text = path.read_text()

        if topic == "xg_analysis":
            header, blocks = split_xg_analysis(text)
            docs.append(header)
            metas.append({"kind": "league", "topic": topic, "league": league,
                          "source": path.name})
            ids.append(topic + "_" + str(league) + "_summary")

            for b in blocks:
                meta = team_metadata(b)
                if "team" not in meta:
                    continue
                meta.update({"kind": "team", "topic": topic,
                             "league": meta.get("league", league),
                             "source": path.name})
                docs.append(b)
                metas.append(meta)
                ids.append(topic + "_" + meta["league"] + "_" +
                           meta["team"].replace(" ", "_"))
        elif topic == "players":
            header, blocks = split_players(text)
            docs.append(header)
            metas.append({"kind": "league", "topic": topic, "league": league,
                          "source": path.name})
            ids.append(topic + "_" + str(league) + "_summary")

            for b in blocks:
                meta = player_metadata(b)
                if "player_id" not in meta:
                    continue
                meta.update({"kind": "player", "topic": topic,
                             "league": meta.get("league", league),
                             "source": path.name})
                docs.append(b)
                metas.append(meta)
                ids.append("player_" + str(meta["player_id"]))

        else:
            docs.append(text.strip())
            m = {"kind": "league", "topic": topic, "source": path.name}
            if league:
                m["league"] = league
            metas.append(m)
            ids.append(topic + "_" + (league or "all"))

    col.add(documents=docs, metadatas=metas, ids=ids)

    n_team = sum(1 for m in metas if m["kind"] == "team")
    n_league = sum(1 for m in metas if m["kind"] == "league")
    n_thin = sum(1 for m in metas if m.get("thin_sample"))
    n_player = sum(1 for m in metas if m["kind"] == "player")
    n_amb = sum(1 for m in metas if m.get("position_ambiguous"))
    print("")
    print("  " + str(len(docs)) + " chunks -> " + str(CHROMA_DIR))
    print("  team blocks:   " + str(n_team) + "  (" + str(n_thin) + " single-season)")
    print("  league blocks: " + str(n_league))
    print("  player blocks: " + str(n_player) + "  (" + str(n_amb) + " ambiguous position)")

    teams = sorted({m["team"] for m in metas if m["kind"] == "team"})
    print("  distinct teams: " + str(len(teams)))
    assert len(ids) == len(set(ids)), "duplicate chunk ids"


if __name__ == "__main__":
    build()
