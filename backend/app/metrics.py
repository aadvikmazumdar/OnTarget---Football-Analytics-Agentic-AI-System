"""Metric semantics: sort direction + what the number actually means.

Several columns in team_season read backwards from their names. This module is
the single source of truth for direction and meaning, so anything generating
prose downstream (agent responses, tooltips) can't invert them.
"""
from __future__ import annotations

METRICS = {
    "xGD_attack": {
        "plain": "Did they score more goals than their chances deserved? Positive means clinical finishing.",
        "higher_is_better": True,
        "label": "Finishing residual (attack)",
        "gloss": "Goals scored minus xG. Measures finishing, not chance creation. "
                 "A team can rank highly here while creating very little.",
        "formula": "scored - xG",
    },
    "xGD_defence": {
        "plain": "Did they concede more goals than the chances against them deserved? Positive is worse.",
        "higher_is_better": False,
        "label": "Conceding residual (defence)",
        "gloss": "Goals conceded minus xGA. Positive means conceding more than the "
                 "chances warranted. Not a measure of chances conceded - for that, "
                 "use xGA_per_game.",
        "formula": "missed - xGA",
    },
    "clinical_rate": {
        "plain": "How often they finished their chances well.",
        "higher_is_better": True,
        "label": "Clinical rate",
        "gloss": "Share of matches classified as clinical finishing.",
        "formula": None,
    },
    "heist_rate": {
        "plain": "How often they won despite being outplayed. Usually luck, not skill.",
        "higher_is_better": True,
        "label": "Heist rate",
        "gloss": "Share of matches won while losing the xG battle. High values "
                 "usually indicate variance rather than repeatable skill.",
        "formula": None,
    },
    "robbery_rate": {
        "plain": "How often they took points against the run of play.",
        "higher_is_better": True,
        "label": "Robbery rate",
        "gloss": "Share of matches where points were taken against the run of play.",
        "formula": None,
    },
    "wasteful_rate": {
        "plain": "How often they missed chances they should have scored.",
        "higher_is_better": False,
        "label": "Wasteful rate",
        "gloss": "Share of matches where finishing fell short of chances created.",
        "formula": None,
    },
    "xG_per_game": {
        "plain": "How many good chances they create per match. Higher means a better attack.",
        "higher_is_better": True,
        "label": "xG per game",
        "gloss": "Chance creation volume and quality. This is the attacking-quality "
                 "metric, unlike xGD_attack.",
        "formula": "xG / games_played",
    },
    "xGA_per_game": {
        "plain": "How many good chances they allow per match. Lower means a better defence.",
        "higher_is_better": False,
        "label": "xGA per game",
        "gloss": "Chance quality conceded. This is the defensive-quality metric - "
                 "the right column for 'best defence' questions.",
        "formula": "xGA / games_played",
    },
    "goals_per_game": {
        "plain": "Goals scored per match.",
        "higher_is_better": True,
        "label": "Goals per game",
        "gloss": "Actual scoring rate.",
        "formula": "scored / games_played",
    },
    "conceded_per_game": {
        "plain": "Goals let in per match.",
        "higher_is_better": False,
        "label": "Conceded per game",
        "gloss": "Actual conceding rate.",
        "formula": "missed / games_played",
    },
    "xGD_per_game": {
        "plain": "Chances created minus chances allowed, per match. The best single measure of team strength.",
        "higher_is_better": True,
        "label": "xG difference per game",
        "gloss": "Net expected-goal difference. The best single-number proxy for "
                 "underlying team strength.",
        "formula": "(xG - xGA) / games_played",
    },
}

# Columns whose names invert or obscure their meaning.
INVERTED_SEMANTICS = {
    "ppda_allowed_value": "Measures the press a team withstands, not the press it "
                          "applies. High means the opponent's press is not "
                          "disrupting them.",
    "xGD_defence": "A conceding residual, not chances conceded. For 'best defence', "
                   "use xGA_per_game.",
    "xGD_attack": "A finishing residual, not chance creation. For 'best attack', "
                  "use xG_per_game.",
}
