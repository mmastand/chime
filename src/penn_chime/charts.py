
from datetime import datetime
from math import ceil
from typing import Dict, Optional

from altair import Chart
import pandas as pd
import numpy as np

from .constants import DATE_FORMAT
from .parameters import Parameters


def build_admits_chart(
    *,
    alt,
    admits_floor_df: pd.DataFrame,
    max_y_axis: Optional[int] = None,
) -> Chart:
    """Build admits chart."""
    y_scale = alt.Scale()
    if max_y_axis is not None:
        y_scale.domain = (0, max_y_axis)

    x = dict(shorthand="date:T", title="Date", axis=alt.Axis(format=(DATE_FORMAT)))
    y = dict(shorthand="value:Q", title="Daily admissions", scale=y_scale)
    color = alt.Color("key:N", sort = ["total", "icu", "ventilators"])
    tooltip=["date:T", alt.Tooltip("value:Q", format=".0f", title="Admit"), "key:N"]

    # TODO fix the fold to allow any number of dispositions
    points = (
        alt.Chart()
        .transform_fold(fold=["total", "icu", "ventilators"])
        .encode(x=alt.X(**x), y=alt.Y(**y), color=color, tooltip=tooltip)
        .mark_line(point=True)
    )
    bar = (
        alt.Chart()
        .encode(x=alt.X(**x))
        .transform_filter(alt.datum.day == 0)
        .mark_rule(color="black", opacity=0.35, size=2)
    )
    return alt.layer(points, bar, data=admits_floor_df)



def build_census_chart(
    *,
    alt,
    census_floor_df: pd.DataFrame,
    max_y_axis: Optional[int] = None,
) -> Chart:
    """Build census chart."""
    y_scale = alt.Scale()
    if max_y_axis:
        y_scale.domain = (0, max_y_axis)

    x = dict(shorthand="date:T", title="Date", axis=alt.Axis(format=(DATE_FORMAT)))
    y = dict(shorthand="value:Q", title="Census", scale=y_scale)
    color = alt.Color("key:N", sort = ["total", "icu", "ventilators"])
    tooltip = ["date:T", alt.Tooltip("value:Q", format=".0f", title="Census"), "key:N"]

    # TODO fix the fold to allow any number of dispositions
    points = (
        alt.Chart()
        .transform_fold(fold=["total", "icu", "ventilators"])
        .encode(x=alt.X(**x), y=alt.Y(**y), color=color, tooltip=tooltip)
        .mark_line(point=True)
    )
    bar = (
        alt.Chart()
        .encode(x=alt.X(**x))
        .transform_filter(alt.datum.day == 0)
        .mark_rule(color="black", opacity=0.35, size=2)
    )
    return alt.layer(points, bar, data=census_floor_df)


def build_sim_sir_w_date_chart(
    *,
    alt,
    sim_sir_w_date_floor_df: pd.DataFrame,
    max_y_axis: Optional[int] = None,
) -> Chart:
    """Build sim sir w date chart."""
    y_scale = alt.Scale()
    if max_y_axis is not None:
        y_scale.domain = (0, max_y_axis)

    x = dict(shorthand="date:T", title="Date", axis=alt.Axis(format=(DATE_FORMAT)))
    y = dict(shorthand="value:Q", title="Count", scale=y_scale)
    color = "key:N"
    tooltip = ["key:N", "value:Q"]

    # TODO fix the fold to allow any number of dispositions
    points = (
        alt.Chart()
        .transform_fold(fold=["susceptible", "infected", "recovered"])
        .encode(x=alt.X(**x), y=alt.Y(**y), color=color, tooltip=tooltip)
        .mark_line()
    )
    bar = (
        alt.Chart()
        .encode(x=alt.X(**x))
        .transform_filter(alt.datum.day == 0)
        .mark_rule(color="black", opacity=0.35, size=2)
    )
    return alt.layer(points, bar, data=sim_sir_w_date_floor_df)

def build_beds_chart(
    alt, 
    beds_floor_df: pd.DataFrame, 
    max_y_axis: Optional[int] = None,
) -> Chart:
    """docstring"""
    y_scale = alt.Scale()
    if max_y_axis is not None:
        y_scale.domain = (0, max_y_axis)

    x = dict(shorthand="date:T", title="Date", axis=alt.Axis(format=(DATE_FORMAT)))
    y = dict(shorthand="value:Q", title="COVID-19 Capacity", scale=y_scale)
    color = alt.Color("key:N", sort = ["total", "icu", "ventilators"])
    tooltip = ["key:N", "value:Q"]
    
    # census["line"] = 0
    # TODO fix the fold to allow any number of dispositions
    beds = (
        alt.Chart()
        .transform_fold(fold=["total", "icu", "ventilators"])
        .mark_line(point=True)
        .encode(x=alt.X(**x), y=alt.Y(**y), color=color, tooltip=tooltip)
        .mark_line()
    )
    # Horizontal line at 0
    # hline = alt.Chart(census.head(plot_projection_days)
    # ).transform_fold(
    #     fold=["line"]
    # ).mark_line(
    #     point=False,
    #     color="black",
    #     strokeDash=[5,3],
    #     opacity=.5,
    # ).encode(
    #     x=alt.X(**x_kwargs),
    #     y=alt.Y("value:Q"),
    # )
    # # Vertical line on today
    # v_line_location = "0"
    # if parameters.as_date:
    #     today = datetime.date.today()
    #     v_line_location = f"datetime({today.year}, {today.month - 1}, {today.day})" # Because Altair uses vega which has 0-based month indexes
    # vline = alt.Chart(census.head(plot_projection_days)
    # ).mark_rule(
    #     strokeDash=[5,3],
    #     opacity=.05, # This doesn't seem to do anything
    # ).encode(
    #     x="v_line_location:T" if parameters.as_date else "v_line_location:Q"
    # ).transform_calculate(v_line_location=v_line_location)

    # return beds + vline + hline, beds
    return alt.layer(beds, data=beds_floor_df)
def build_descriptions(
    *,
    chart: Chart,
    labels: Dict[str, str],
    suffix: str = ""
) -> str:
    """

    :param chart: The alt chart to be used in finding max points
    :param suffix: The assumption is that the charts have similar column names.
                   The census chart adds " Census" to the column names.
                   Make sure to include a space or underscore as appropriate
    :return: Returns a multi-line string description of the results
    """
    messages = []

    cols = ["total", "icu", "ventilators"]
    asterisk = False
    day = "date" if "date" in chart.data.columns else "day"

    for col in cols:
        if chart.data[col].idxmax() + 1 == len(chart.data):
            asterisk = True

        # todo: bring this to an optional arg / i18n
        on = datetime.strftime(chart.data[day][chart.data[col].idxmax()], "%b %d")

        messages.append(
            "{} {:,} on {}{}".format(
                labels[col],
                ceil(chart.data[col].max()),
                on,
                "*" if asterisk else "",
            )
        )

    if asterisk:
        messages.append("_* The max is at the upper bound of the data, and therefore may not be the actual max_")
    return "\n\n".join(messages)


def build_table(
    *,
    df: pd.DataFrame,
    labels: Dict[str, str],
    modulo: int = 1,
) -> pd.DataFrame:
    table_df = df[np.mod(df.day, modulo) == 0].copy()
    table_df.date = table_df.date.dt.strftime(DATE_FORMAT)
    table_df.rename(labels)
    return table_df
