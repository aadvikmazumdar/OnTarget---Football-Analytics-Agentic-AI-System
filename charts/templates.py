import plotly.express as px
import pandas as pd

def time_series_line(data, x, y, color=None, title=None, hover_cols=None):
    fig = px.line(data, x=x, y=y, color=color, title=title, markers=True, hover_data=hover_cols)
    fig.update_layout(hovermode='closest')
    return fig

def scatter_with_trend(data: pd.DataFrame, x: str, y: str, color: str = None,
                        hover_cols: list = None, title: str = None, trendline: str = 'ols'):
    """
    Generic scatter plot with an optional trendline. Works with any dataframe
    containing two numeric columns; color can split by a categorical column
    (e.g. league, tier) to compare groups.
    """
    fig = px.scatter(
        data, x=x, y=y, color=color, hover_data=hover_cols,
        title=title, trendline=trendline
    )
    return fig

def grouped_bar(data: pd.DataFrame, x: str, y: str, color: str = None,
                hover_cols: list = None, title: str = None, orientation: str = 'v'):
    """
    Generic grouped/stacked bar chart. x is typically a categorical column
    (team, league), y is a numeric count/rate, color splits into groups.
    """
    fig = px.bar(
        data, x=x, y=y, color=color, hover_data=hover_cols,
        title=title, orientation=orientation, barmode='group'
    )
    return fig


def tag_frequency_bar(data: pd.DataFrame, tag_col: str, group_col: str = None,
                       title: str = None):
    """
    Counts occurrences of a boolean tag column (e.g. 'heist', 'chaos', 'dead_rubber'
    from clinical_games), optionally broken down by a grouping column like team or league.
    Expects `tag_col` values to already be filtered/converted to boolean True/False.
    """
    if group_col:
        counts = data.groupby(group_col)[tag_col].sum().reset_index().rename(columns={tag_col: 'count'})
        fig = px.bar(counts, x=group_col, y='count', title=title or f'{tag_col} frequency by {group_col}')
    else:
        count = data[tag_col].sum()
        fig = px.bar(x=[tag_col], y=[count], title=title or f'{tag_col} frequency')
    return fig

from mplsoccer import Pitch
import matplotlib.pyplot as plt

def shot_pitch_map(data: pd.DataFrame, x_col='X', y_col='Y', title=None):
    """
    Plots shot locations on a pitch. Assumes X, Y are normalized 0-1
    (Understat convention) and rescales to Opta's 0-100 pitch scale.
    """
    pitch = Pitch(pitch_type='opta', pitch_color='#0e1117', line_color='white')
    fig, ax = pitch.draw(figsize=(10, 7))

    # rescale 0-1 normalized coords to Opta's 0-100 scale
    x_scaled = data[x_col] * 100
    y_scaled = data[y_col] * 100

    pitch.scatter(x_scaled, y_scaled, ax=ax, color='#4A90D9', edgecolors='white', s=40, alpha=0.6)
    if title:
        ax.set_title(title, color='white', fontsize=14)
    fig.patch.set_facecolor('#0e1117')
    return fig

import plotly.graph_objects as go

def plotly_pitch_map(data: pd.DataFrame, x_col='X', y_col='Y', hover_cols=None, title=None):
    """
    Interactive shot map on a drawn pitch (Plotly shapes), using normalized 0-1
    Understat-style coordinates directly — no rescaling needed since we draw
    the pitch outline in the same 0-1 space.
    """
    fig = go.Figure()

    # pitch outline (0-1 normalized space, matching shot coordinate convention)
    pitch_lines = [
        dict(type='rect', x0=0, y0=0, x1=1, y1=1, line=dict(color='white', width=2)),
        dict(type='line', x0=0.5, y0=0, x1=0.5, y1=1, line=dict(color='white', width=1)),
        dict(type='rect', x0=0.85, y0=0.21, x1=1, y1=0.79, line=dict(color='white', width=1)),  # penalty box (approx)
        dict(type='rect', x0=0.96, y0=0.37, x1=1, y1=0.63, line=dict(color='white', width=1)),  # six-yard box (approx)
    ]

    fig.update_layout(shapes=pitch_lines, plot_bgcolor='#0e1117', paper_bgcolor='#0e1117',
                       xaxis=dict(range=[0, 1], visible=False),
                       yaxis=dict(range=[0, 1], visible=False, scaleanchor='x'),
                       title=title, showlegend=False)

    fig.add_trace(go.Scatter(
        x=data[x_col], y=data[y_col], mode='markers',
        marker=dict(size=9, color='#4A90D9', line=dict(width=1, color='white')),
        customdata=data[hover_cols] if hover_cols else None,
        hovertemplate=(
            '<br>'.join([f'{col}: %{{customdata[{i}]}}' for i, col in enumerate(hover_cols)]) + '<extra></extra>'
            if hover_cols else None
        )
    ))

    return fig