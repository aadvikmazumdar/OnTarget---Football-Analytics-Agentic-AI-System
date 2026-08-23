from __future__ import annotations

import asyncio
import aiohttp
import json
import random
from pathlib import Path

import pandas as pd


LEAGUES = ["premier_league", "la_liga", "serie_a", "bundesliga", "ligue_1"]
SEASONS = ["2020", "2021", "2022", "2023", "2024"]

MATCHES_CSV  = "data/processed/matches.csv"
BASE_URL     = "https://understat.com/getMatchData"

CONCURRENCY  = 5
DELAY_MIN    = 0.5
DELAY_MAX    = 1.5


def get_match_ids(df: pd.DataFrame, league: str, season: str) -> list[int]:
    mask = (df["league"] == league) & (df["year"] == int(season))
    return df.loc[mask, "match_id"].tolist()


def output_path(league: str, season: str, match_id: int) -> Path:
    return Path(f"data/raw/shots/{league}/{season}/{match_id}.json")


def already_scraped(league: str, season: str, match_id: int) -> bool:
    return output_path(league, season, match_id).exists()


async def fetch_match(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    league: str,
    season: str,
    match_id: int,
) -> tuple[int, str, str, dict | None | bool]:
    if already_scraped(league, season, match_id):
        return match_id, league, season, None  # None = skipped

    url = f"{BASE_URL}/{match_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": f"https://understat.com/match/{match_id}",
        "X-Requested-With": "XMLHttpRequest",
    }

    async with semaphore:
        await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json(content_type=None)
                    return match_id, league, season, data
                else:
                    print(f"  [ERROR] {match_id} ({league} {season}) — HTTP {response.status}")
                    return match_id, league, season, False
        except Exception as e:
            print(f"  [ERROR] {match_id} ({league} {season}) — {e}")
            return match_id, league, season, False


def save_match(league: str, season: str, match_id: int, data: dict):
    path = output_path(league, season, match_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


async def scrape_all(df: pd.DataFrame):
    semaphore = asyncio.Semaphore(CONCURRENCY)
    saved = skipped = failed = 0

    tasks = []
    for league in LEAGUES:
        for season in SEASONS:
            ids = get_match_ids(df, league, season)
            print(f"  {league} {season}: {len(ids)} matches")
            for mid in ids:
                tasks.append((league, season, mid))

    print(f"\nTotal matches: {len(tasks)}")
    print("=" * 40)

    async with aiohttp.ClientSession() as session:
        coros = [fetch_match(session, semaphore, l, s, mid) for l, s, mid in tasks]

        for coro in asyncio.as_completed(coros):
            match_id, league, season, result = await coro

            if result is None:
                skipped += 1
            elif result is False:
                failed += 1
            else:
                save_match(league, season, match_id, result)
                saved += 1
                shot_count = len(result.get("shots", {}).get("h", [])) + len(result.get("shots", {}).get("a", []))
                print(f"  [OK] {match_id} ({league} {season}) — shots: {shot_count}")

    print(f"\nDone — saved: {saved}, skipped: {skipped}, failed: {failed}")


if __name__ == "__main__":
    print("Scraping shots: all leagues, all seasons")
    print("=" * 40)

    df = pd.read_csv(MATCHES_CSV)
    asyncio.run(scrape_all(df))