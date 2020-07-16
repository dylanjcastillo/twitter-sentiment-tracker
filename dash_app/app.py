import sqlite3

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import pandas as pd
from dash.dependencies import Input, Output
from components import card, tweet
from utils import human_format, get_color_from_score
from pathlib import Path
import logging


UPDATE_INTERVAL = 30
ROOT_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT_DIR / "database" / "tweets.db"
TARGETS_DF = pd.read_csv(ROOT_DIR / "accounts.csv")

external_stylesheets = [
    dbc.themes.BOOTSTRAP,
    "assets/style.css",
    {
        "href": "https://fonts.googleapis.com/css2?"
        "family=Lato:wght@400;500;600;700;800&display=swap",
        "rel": "stylesheet",
    },
]

app = dash.Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server

app.title = "Tweets Scorer: Analyze sentiment of tweets in real-time"
app.layout = html.Div(
    [
        dbc.Jumbotron(
            [
                dbc.Container(
                    [
                        html.H1("Tweets Scorer", className="title-jumbotron"),
                        html.P(
                            "Analyze the sentiment of tweets in real-time",
                            className="text-jumbotron",
                        ),
                    ]
                ),
            ],
            className="jumbotron-fluid",
        ),
        dbc.Container(
            [
                dbc.Card(
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.P(
                                        "0",
                                        id="total-responses",
                                        className="total-responses",
                                    ),
                                    html.P("INTERACTIONS", className="total-subtitle",),
                                ],
                                className="order-0 text-center",
                            ),
                            html.Div(
                                [
                                    html.P(
                                        "0%",
                                        id="total-approval",
                                        className="total-score",
                                    ),
                                    html.P("AVG. APPROVAL", className="total-subtitle",),
                                ],
                                className="order-1 text-center",
                            ),
                            html.Div(
                                [
                                    dcc.Checklist(
                                        options=[
                                            {"label": "  Exclude Retweets", "value": 1},
                                        ],
                                        value=[],
                                        id="exclude-rt-checkbox",
                                        className="exclude-rt-checkbox text-center",
                                    ),
                                    dcc.Dropdown(
                                        id="total-dropdown",
                                        options=[
                                            {"label": "Last 15 minutes", "value": 15},
                                            {"label": "Last hour", "value": 60},
                                            {"label": "Last 24 hours", "value": 1440},
                                        ],
                                        value=15,
                                        clearable=False,
                                        searchable=False,
                                    ),
                                ],
                                className="d-flex flex-column justify-content-between "
                                "total-dropdowns order-2 my-md-auto",
                            ),
                        ],
                        className="d-flex flex-column flex-sm-row align-items-center "
                        "justify-content-around flex-wrap",
                    ),
                    className="top-card mx-auto",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.P(
                                    "Summary",
                                    className="title-summary text-center text-sm-left mt-1",
                                ),
                                html.Div(
                                    id="summary-cards",
                                    className="d-flex flex-wrap flex-column flex-sm-row "
                                    "justify-content-sm-center justify-content-md-end",
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                html.P(
                                    "Latest Interactions",
                                    className="title-summary text-center text-sm-left mt-4 mt-sm-1",
                                ),
                                html.Div(id="summary-tweets"),
                            ]
                        ),
                    ],
                    id="summary-container",
                    className="""d-flex flex-column align-items-center align-items-md-start
                                 flex-md-row justify-content-sm-around mt-4""",
                ),
                dcc.Interval(
                    id="overview-interval",
                    interval=UPDATE_INTERVAL * 1000,  # in milliseconds
                    n_intervals=0,
                ),
            ],
            id="cards-container",
        ),
    ]
)


@app.callback(
    Output("summary-tweets", "children"),
    [
        Input("overview-interval", "n_intervals"),
        Input("total-dropdown", "value"),
        Input("exclude-rt-checkbox", "value"),
    ],
)
def update_tweets(n, time_range, exclude_rt):
    conn = sqlite3.connect(DATABASE_PATH)
    time_range = 15 if time_range not in (15, 60, 1440) else time_range * 100
    filter_rt = True if exclude_rt == [1] else False
    query = f"""
    select
        target as target,
        tweet_timestamp as tweet_timestamp,
        full_text as full_text,
        sentiment as score
    from tweets
    where
        datetime(tweet_timestamp) >= datetime('now', '-{time_range} minutes')
        {"and IS_RT = 0" if filter_rt else ""}
    order by datetime(tweet_timestamp) desc
    limit 5;
    """
    df = pd.read_sql_query(query, conn)
    df["tweet_timestamp"] = pd.to_datetime(df.tweet_timestamp.values)
    tweets = []
    for _, row in df.iterrows():
        time = row["tweet_timestamp"].strftime("%T - %b %-d, %Y")
        img = TARGETS_DF.loc[TARGETS_DF.id == row["target"]]["image"].item()
        if row["score"] < 0.5:
            color = "hsl(360, 67%, 44%)"
            sentiment = "NEGATIVE"
        else:
            color = "hsl(184, 77%, 34%)"
            sentiment = "POSITIVE"
        tweets.append(tweet(time, img, row["full_text"], sentiment, color))
    return html.Div(tweets)


@app.callback(
    [
        Output("summary-cards", "children"),
        Output("total-responses", "children"),
        Output("total-approval", "children"),
        Output("total-approval", "style"),
    ],
    [
        Input("overview-interval", "n_intervals"),
        Input("total-dropdown", "value"),
        Input("exclude-rt-checkbox", "value"),
    ],
)
def update_cards(n, time_range, exclude_rt):
    conn = sqlite3.connect(DATABASE_PATH)
    time_range = 15 if time_range not in (15, 60, 1440) else time_range * 100
    filter_rt = True if exclude_rt == [1] else False
    query = f"""
    select
        target as target,
        count(*) as responses,
        avg(sentiment) * 100 as sentiment
    from tweets
    where
        datetime(tweet_timestamp) >= datetime('now', '-{time_range} minutes')
        {"and IS_RT = 0" if filter_rt else ""}
        group by target;
    """
    df = pd.read_sql_query(query, conn)
    cards = []
    for target in TARGETS_DF.itertuples():
        try:
            responses = df.loc[df.target == target.id, "responses"].item()
            sentiment_score = df.loc[df.target == target.id, "sentiment"].item()
            cards.append(card(target, responses, sentiment_score))
        except Exception:
            pass
    total_responses_num = df.responses.sum()
    total_responses = human_format(total_responses_num)
    total_approval_num = 0
    try:
        total_approval_num = np.nanmean(df.sentiment)
    except Exception:
        pass
    total_approval = f"{total_approval_num:.0f}%"
    approval_style = {"color": get_color_from_score(total_approval_num)}
    return cards, total_responses, total_approval, approval_style


if __name__ == "__main__":
    logging.basicConfig(
        filename="./logs/dash_app.log", filemode="w", level=logging.DEBUG
    )
    app.run_server(host="0.0.0.0", debug=True, port=8050)
