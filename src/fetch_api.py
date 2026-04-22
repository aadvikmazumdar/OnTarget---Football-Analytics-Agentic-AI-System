#This file handles all communication with the API-Football services

#loading all dependencies
import requests
import json
import os
import time
from dotenv import load_dotenv
from pathlib import Path

# loading .env file 
load_dotenv()

#Config
API_KEY = os.getenv("API_FOOTBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {"x-apisports-key": API_KEY}

COMPETITIONS = {
    "premier_league": {"id": 39, "name": "Premier League"},
    "la_liga": {"id": 140, "name": "La Liga"},
    "serie_a": {"id": 135, "name": "Serie A"},
    "bundesliga": {"id": 78, "name": "Bundesliga"},
    "ligue_1": {"id": 61, "name": "Ligue 1"},
    "champions_league": {"id": 2, "name": "Champions League"},
    "europa_league": {"id": 3, "name": "Europa League"},
    "conference_league": {"id": 848, "name": "Conference League"},
}

SEASON = [2020,2021,2022,2023,2024]

#Helpers

def make_request(endpoint,params):
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.get(url, headers = HEADERS, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error{response.status_code} for {endpoint}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Request Failed: {e}")
        return None

def save_raw_data(data,competition_key,data_type,season):
    folder = Path(f"data/raw/api_football/{competition_key}")
    folder.mkdir(parents=True,exist_ok = True)
    file_path = folder / f"{data_type}_{season}.json"
    with open(file_path, 'w') as f:
        json.dump(data,f,indent = 2)
    print(f"saved: {file_path}")

# main fetch functions

def fetch_fixtures(competition_key, season):
    competition = COMPETITIONS[competition_key]
    print(f"Fetching Fixtures: {competition['name']} {season}...")

    params ={
        "league": competition["id"],
        "season": season
    }

    data = make_request("/fixtures",params)

    if data:
        save_raw_data(data,competition_key,"fixtures",season)
        return data.get("response", [])
    return []

def fetch_fixture_events(fixture_id):
    params = {
        "fixture": fixture_id
    }
    data = make_request("/fixtures/events", params)
    if data:
        return data.get("response",[])
    return []

def fetch_all_goals(competition_key,season):
    competition = COMPETITIONS[competition_key]
    print(f"\nStarting: {competition['name']} {season}")
    print("-" * 40)

    fixtures = fetch_fixtures(competition_key,season)

    if not fixtures:
        print("No fixtures found")
        return []
    
    print(f"Found {len(fixtures)} fixtures")

    all_goals = []

    for i, fixture in enumerate(fixtures):
        fixture_id = fixture["fixture"]["id"]
        events = fetch_fixture_events(fixture_id)

        for event in events:
            if event.get("type") == "Goal":
                goal = {
                    "fixture_id": fixture_id,
                    "league": competition["name"],
                    "competition_key": competition_key,
                    "season": season,
                    "minute": event["time"]["elapsed"],
                    "extra_time": event["time"].get("extra"),
                    "team": event["team"]["name"],
                    "player": event["player"]["name"],
                    "assist": event["assist"]["name"] if event.get("assist") else None,
                    "goal_type": event["detail"],
                    "home_team": fixture["teams"]["home"]["name"],
                    "away_team": fixture["teams"]["away"]["name"],
                    "home_goals": fixture["goals"]["home"],
                    "away_goals": fixture["goals"]["away"],
                }
                all_goals.append(goal)
                
        time.sleep(0.5)
        if(i+1) % 10 == 0:
            print(f"processed {i+1}/{len(fixtures)} fixtures...")
    #debugging
    print(f"\nDebug - First Fixture ID: {fixtures[0]['fixture']['id']}")
    test_events = fetch_fixture_events(fixtures[0]['fixture']['id'])
    print(f"Events Returned: {len(test_events)}")
    print(f"First event: {test_events[0] if test_events else 'EMPTY'}")
    save_raw_data(all_goals,competition_key,"goals",season)
    print(f"total goals found: {len(all_goals)}")
    return all_goals

if __name__ == "__main__":
    print("GoalMap - Data Collection")
    print("=" * 40)
    goals = fetch_all_goals("premier_league",2023)
    print(f"\nDone, Collected {len(goals)} goals")


