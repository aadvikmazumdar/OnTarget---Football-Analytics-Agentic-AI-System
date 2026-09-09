import streamlit as st
import duckdb
import pandas as pd

st.set_page_config(page_title="OnTarget", layout="wide")

@st.cache_resource
def get_connection():
    con = duckdb.connect(database=':memory:')
    con.execute("CREATE TABLE matches AS SELECT * FROM read_csv_auto('data/processed/matches.csv')")
    con.execute("CREATE TABLE teams AS SELECT * FROM read_csv_auto('data/processed/teams_enriched.csv')")
    con.execute("CREATE TABLE shots AS SELECT * FROM read_csv_auto('data/processed/shots_enriched.csv')")
    con.execute("CREATE TABLE clinical_games AS SELECT * FROM read_csv_auto('data/processed/clinical_games.csv')")
    con.execute("CREATE TABLE team_season AS SELECT * FROM read_csv_auto('data/processed/team_season.csv')")
    con.execute("CREATE TABLE consistency AS SELECT * FROM read_csv_auto('data/processed/consistency.csv')")
    return con

con = get_connection()

st.title("OnTarget — Football Analytics")
st.write("Dashboard skeleton — chart templates coming next.")

from charts.templates import time_series_line, scatter_with_trend

# --- Chart 1: Team xG Trend ---
st.subheader("Team xG Trend")

team_options = con.execute("SELECT DISTINCT team_name FROM teams ORDER BY 1").df()['team_name']
team_choice = st.selectbox("Team", team_options)

team_data = con.execute("""
    SELECT date, xG, xGA, opponent, rank_to_date
    FROM teams
    WHERE team_name = ?
    ORDER BY date
""", [team_choice]).df()

fig = time_series_line(
    team_data, x='date', y='xG', title=f'{team_choice} — xG Over Time',
    hover_cols=['opponent', 'rank_to_date']
)
st.plotly_chart(fig, use_container_width=True)

# --- Chart 2: Press Resistance vs Clinical Finishing ---
st.subheader("Press Resistance vs Clinical Finishing")

press_data = con.execute("""
    SELECT
        team_name,
        league,
        year,
        AVG(ppda_allowed_value) AS avg_ppda_allowed,
        SUM(scored) AS total_scored,
        SUM(xG) AS total_xG
    FROM teams
    GROUP BY team_name, league, year
""").df()

press_data['clinical_rate'] = press_data['total_scored'] / press_data['total_xG']

fig2 = scatter_with_trend(
    press_data, x='avg_ppda_allowed', y='clinical_rate',
    hover_cols=['team_name', 'league', 'year'],
    title='Press Resistance (PPDA Allowed) vs Clinical Finishing Rate'
)
st.plotly_chart(fig2, use_container_width=True)

from charts.templates import tag_frequency_bar

st.subheader("Heist Frequency by Team")

heist_data = con.execute("""
    SELECT team_name, league, heist
    FROM clinical_games
""").df()

# flags are strings like 'heist'/'not_heist' — convert to boolean before counting
heist_data['heist'] = heist_data['heist'] == 'heist'

fig3 = tag_frequency_bar(
    heist_data, tag_col='heist', group_col='team_name',
    title='Heist Count by Team (All Seasons)'
)
st.plotly_chart(fig3, use_container_width=True)

from charts.templates import plotly_pitch_map

st.subheader("Shot Location Explorer")

col1, col2, col3 = st.columns(3)

with col1:
    shot_team = st.selectbox("Team", team_options, key='shot_team')

years_for_team = con.execute(
    "SELECT DISTINCT year FROM shots WHERE team_name = ? ORDER BY year", [shot_team]
).df()['year']

with col2:
    shot_years = st.multiselect("Season(s)", years_for_team, default=list(years_for_team), key='shot_years')

players_for_selection = con.execute(
    "SELECT DISTINCT player FROM shots WHERE team_name = ? AND year IN ({}) ORDER BY player".format(
        ','.join(['?'] * len(shot_years))
    ), [shot_team] + list(shot_years)
).df()['player'] if shot_years else pd.Series([], dtype=str)

with col3:
    shot_player = st.selectbox("Player (optional)", ['All players'] + list(players_for_selection), key='shot_player')

# single-match dropdown, dependent on team + years (+ player if chosen)
match_filter_query = "SELECT DISTINCT match_id, date, opponent_team FROM shots WHERE team_name = ? AND year IN ({})".format(
    ','.join(['?'] * len(shot_years))
)
match_params = [shot_team] + list(shot_years)
if shot_player != 'All players':
    match_filter_query += " AND player = ?"
    match_params.append(shot_player)
match_filter_query += " ORDER BY date"

matches_for_selection = con.execute(match_filter_query, match_params).df()
matches_for_selection['label'] = matches_for_selection['date'].astype(str) + ' vs ' + matches_for_selection['opponent_team']

match_choice = st.selectbox(
    "Specific match (optional)", ['All matches'] + list(matches_for_selection['label']), key='shot_match'
)

# build the final filtered query
base_query = "SELECT X, Y, date, player, result, situation, opponent_team FROM shots WHERE team_name = ? AND year IN ({})".format(
    ','.join(['?'] * len(shot_years))
)
params = [shot_team] + list(shot_years)

if shot_player != 'All players':
    base_query += " AND player = ?"
    params.append(shot_player)

if match_choice != 'All matches':
    chosen_match_id = matches_for_selection[matches_for_selection['label'] == match_choice]['match_id'].iloc[0]
    base_query += " AND match_id = ?"
    params.append(int(chosen_match_id))

shot_explorer_data = con.execute(base_query, params).df()

st.write(f"Showing {len(shot_explorer_data)} shots")
fig5 = plotly_pitch_map(
    shot_explorer_data, hover_cols=['date', 'player', 'opponent_team', 'result', 'situation'],
    title=f'{shot_team} — Shot Locations'
)
st.plotly_chart(fig5, use_container_width=True)

st.dataframe(shot_explorer_data[['date', 'player', 'opponent_team', 'result', 'situation']].sort_values('date', ascending=False))