import dash_bootstrap_components as dbc
import dash_html_components as html
from utils import human_format, get_color_from_score


def card(target, responses, score):
    """Summary card component"""
    kpi_color = get_color_from_score(score)
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.Img(src=f"assets/img/{target.image}", className="card-img"),
                    html.H4(target.name, className="card-title"),
                    html.P(target.party, className="card-party"),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.P(
                                        f"{human_format(responses)}",
                                        className="card-text",
                                    ),
                                    html.P("INTERACTIONS", className="card-subtitle",),
                                ],
                                className="order-0 text-center",
                            ),
                            html.Div(
                                [
                                    html.P(
                                        f"{score:.0f}%",
                                        className="card-kpi",
                                        style={"color": kpi_color},
                                    ),
                                    html.P("APPROVAL RATE", className="card-subtitle",),
                                ],
                                className="order-1 text-center",
                            ),
                        ],
                        className="d-flex justify-content-between",
                    ),
                ],
                className="text-center",
            )
        ],
        style={
            "background": f"linear-gradient(to bottom, {target.color} 25%, hsl(0, 0%, 100%) 0%)"
        },
        className="card-overview",
    )


def tweet(time, image, text, sentiment, color):
    """Tweet component"""
    return dbc.Card(
        [
            html.Div(
                [
                    html.P(time, className="tweet-time"),
                    html.P(
                        [
                            "Directed at",
                            html.Img(src=f"assets/img/{image}", className="tweet-img",),
                        ],
                        className="tweet-text-img",
                    ),
                ],
                className="tweet-top",
            ),
            html.P(f"{text}", className="tweet-text",),
            html.P(
                f"{sentiment}",
                className="tweet-score badge badge-primary",
                style={"background-color": color},
            ),
        ],
        className="tweet-card",
    )
