import asyncio
import aiohttp
import json
from pathlib import Path

LEAGUES = {
    "premier_league": "EPL",
    "la_liga":        "La_liga",
    "serie_a":        "Serie_A",
    "bundesliga":     "Bundesliga",
    "ligue_1":        "Ligue_1",
}

SEASONS = [2020, 2021, 2022, 2023, 2024]

BASE_URL = "https://understat.com/getLeagueData"


def save_raw_data(data, league_key, data_type, season):
    folder = Path(f"data/raw/understat/{league_key}")
    folder.mkdir(parents=True, exist_ok=True)
    file_path = folder / f"{data_type}_{season}.json"
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Saved: {file_path}")


async def fetch_league_data(session, league_name, season):
    url = f"{BASE_URL}/{league_name}/{season}"
    print(f"Fetching: {url}")

    headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": f"https://understat.com/league/{league_name}/{season}",
    "X-Requested-With": "XMLHttpRequest",
}

    try:
        async with session.get(url, headers=headers) as response:
            print(f"Status: {response.status}")
            if response.status == 200:
                data = await response.json(content_type=None)
                return data
            else:
                print(f"Error {response.status}")
                return None
    except Exception as e:
        print(f"Request failed: {e}")
        return None


async def scrape_league(league_key, season):
    league_name = LEAGUES[league_key]

    print(f"\nScraping: {league_name} {season}/{season+1}")
    print("=" * 40)

    async with aiohttp.ClientSession() as session:
        data = await fetch_league_data(session, league_name, season)

        if not data:
            print("Failed to fetch data")
            return

        teams   = data.get("teams", {})
        players = data.get("players", [])
        dates   = data.get("dates", [])

        print(f"Teams:   {len(teams)}")
        print(f"Players: {len(players)}")
        print(f"Matches: {len(dates)}")

        save_raw_data(teams,   league_key, "teams",   season)
        save_raw_data(players, league_key, "players", season)
        save_raw_data(dates,   league_key, "matches", season)


async def scrape_all():
    for league_key in LEAGUES:
        for season in SEASONS:
            await scrape_league(league_key, season)
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(scrape_all())