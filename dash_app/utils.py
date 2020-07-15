def human_format(num):
    """Returns a formated number depending on digits (e.g., 30K instead of 30,000)"""
    num = float("{:.2g}".format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return "{}{}".format(
        "{:f}".format(num).rstrip("0").rstrip("."),
        ["", "K", "M", "B", "T"][magnitude],
    )


def get_color_from_score(score):
    """Returns color depending on the score"""
    color = "hsl(184, 77%, 34%)"
    if score < 20:
        color = "hsl(360, 67%, 44%)"
    elif score < 50:
        color = "hsl(360, 71%, 66%)"
    elif score < 80:
        color = "hsl(185, 57%, 50%)"
    return color
