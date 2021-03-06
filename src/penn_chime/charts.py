
from datetime import datetime
from math import ceil
from typing import Dict, Optional, Union

from altair import Chart
import pandas as pd
import numpy as np

from .constants import DATE_FORMAT
from .parameters import Parameters
from .hc_actuals import ADMISSIONS_COLUMNS, CENSUS_COLUMNS


def get_actual_columns_and_colors(possible_columns, projections_df, actuals_df, p, alt):
    actuals_plot_columns = []
    actuals_color_domain = []
    actuals_colors_defaults = ['black', '#4C78A8', '#F58518', '#E45756']
    if "daily_regional_infections" in possible_columns:
        actuals_colors_defaults = ['#4C78A8']
    actuals_color_range=[]
    combined = projections_df.merge(actuals_df, on="date", how="left")
    # combined = combined.rename(columns=p.actuals_labels)
    for index, possible_column in enumerate(possible_columns):
        if possible_column in actuals_df.columns:
            actuals_plot_columns.append(possible_column)
            actuals_color_domain.append(possible_column)
            actuals_color_range.append(actuals_colors_defaults[index])
    actuals_color = alt.Color("Actual:N", scale=alt.Scale(domain=actuals_color_domain, range=actuals_color_range))
    return combined, actuals_plot_columns, actuals_color
        
def get_proj_columns_and_colors(df, p, alt):
    # departments
    df = df.rename(columns={
        "total": p.labels["total"],
        "non_icu": p.labels["non_icu"],
        "icu": p.labels["icu"],
        "ventilators": p.labels["ventilators"],
    })
    plot_columns = [
        p.labels["total"],
        p.labels["non_icu"],
        p.labels["icu"],
        p.labels["ventilators"]
    ]

    proj_color = alt.Color(
        "Projected:N",
        sort=plot_columns,
        scale=alt.Scale(
            domain=plot_columns,
            range=['black', '#4C78A8', '#F58518', '#E45756'],
        )
    )
    return df, plot_columns, proj_color

def build_admits_chart(
    *,
    alt,
    admits_floor_df: pd.DataFrame,
    p: Parameters,
    actuals: Union[pd.DataFrame, None],
) -> Chart:
    """Build admits chart."""
    y_scale = alt.Scale()
    if p.max_y_axis_set:
        y_scale.domain = (0, p.max_y_axis)
        y_scale.clamp = True

    admits_floor_df, plot_columns, proj_color = get_proj_columns_and_colors(
        admits_floor_df, p, alt)

    x = dict(shorthand="date:T", title="Date", axis=alt.Axis(format=(DATE_FORMAT)))
    y = dict(shorthand="value:Q", title="Daily admissions", scale=y_scale)
    tooltip=[alt.Tooltip("utcmonthdate(date):O", title="Date", format=(DATE_FORMAT)), alt.Tooltip("value:Q", format=".0f"), "Projected:N"]
    lines = (
        alt.Chart()
        .transform_fold(fold=plot_columns, as_=["Projected", "value"])
        .encode(x=alt.X(**x), y=alt.Y(**y), color=proj_color, tooltip=tooltip)
        .mark_line()
        .properties(
            title={
                "text": "Projected Number of Daily COVID-19 Admissions"
            }
        )
    )
    bar = (
        alt.Chart()
        .encode(x=alt.X(**x))
        .transform_filter(alt.datum.day == 0)
        .mark_rule(color="black", opacity=0.35, size=2)
    )
    charts = [lines, bar]
    if actuals is not None:
        admits_floor_df, actuals_plot_columns, actuals_color = get_actual_columns_and_colors(
            ADMISSIONS_COLUMNS, admits_floor_df, actuals, p, alt,
        )
        actuals_tooltip=[alt.Tooltip("utcmonthdate(date):O", title="Date", format=(DATE_FORMAT)), alt.Tooltip("value:Q", format=".0f"), "Actual:N"]
        actuals_lines = (
            alt.Chart()
            .transform_fold(fold=actuals_plot_columns, as_=["Actual", "value"])
            .encode(x=alt.X(**x), y=alt.Y(**y), color=actuals_color, tooltip=actuals_tooltip)
            .mark_line(point=True, opacity=1.)
        )
        charts.append(actuals_lines)

    return alt.layer(*charts, data=admits_floor_df).resolve_scale(color="independent")



def build_census_chart(
    *,
    alt,
    census_floor_df: pd.DataFrame,
    p: Parameters,
    actuals: Union[pd.DataFrame, None],
) -> Chart:
    """Build census chart."""
    y_scale = alt.Scale()
    if p.max_y_axis_set:
        y_scale.domain = (0, p.max_y_axis)
        y_scale.clamp = True

    census_floor_df, plot_columns, proj_color = get_proj_columns_and_colors(
        census_floor_df, p, alt)

    x = dict(shorthand="date:T", title="Date", axis=alt.Axis(format=(DATE_FORMAT)))
    y = dict(shorthand="value:Q", title="Census", scale=y_scale)
    tooltip = [alt.Tooltip("utcmonthdate(date):O", title="Date", format=(DATE_FORMAT)), alt.Tooltip("value:Q", format=".0f", title="Census"), "Projected:N"]

    # TODO fix the fold to allow any number of dispositions
    lines = (
        alt.Chart()
        .transform_fold(fold=plot_columns, as_=["Projected", "value"])
        .encode(x=alt.X(**x), y=alt.Y(**y), color=proj_color, tooltip=tooltip)
        .mark_line()
        .properties(
            title={
                "text": "Projected Census of COVID-19 Patients",
                "subtitle": "Accounts for Arrivals and Discharges."
            }
        )
    )
    bar = (
        alt.Chart()
        .encode(x=alt.X(**x))
        .transform_filter(alt.datum.day == 0)
        .mark_rule(color="black", opacity=0.35, size=2)
    )
    charts = [lines, bar]
    if actuals is not None:
        census_floor_df, actuals_plot_columns, actuals_color = get_actual_columns_and_colors(
            CENSUS_COLUMNS, census_floor_df, actuals, p, alt,
        )
        actuals_tooltip=[alt.Tooltip("utcmonthdate(date):O", title="Date", format=(DATE_FORMAT)), alt.Tooltip("value:Q", format=".0f", title="Census"), "Actual:N"]
        actuals_lines = (
            alt.Chart()
            .transform_fold(fold=actuals_plot_columns, as_=["Actual", "value"])
            .encode(x=alt.X(**x), y=alt.Y(**y), color=actuals_color, tooltip=actuals_tooltip)
            .mark_line(point=True, opacity=1.)
        )
        charts.append(actuals_lines)
    return alt.layer(*charts, data=census_floor_df).resolve_scale(color="independent")


def build_sim_sir_w_date_chart(
    *,
    alt,
    sim_sir_w_date_floor_df: pd.DataFrame,
    actuals: Union[pd.DataFrame, None],
    p: Parameters,
) -> Chart:
    """Build sim sir w date chart."""
    y_scale = alt.Scale()

    plot_columns = ["susceptible", "infected", "recovered"]
    x = dict(shorthand="date:T", title="Date", axis=alt.Axis(format=(DATE_FORMAT)))
    y = dict(shorthand="value:Q", title="Count", scale=y_scale)
    color = "Projected:N"
    tooltip = [alt.Tooltip("utcmonthdate(date):O", title="Date", format=(DATE_FORMAT)), alt.Tooltip("value:Q", format=".0f"), "Projected:N"]

    # TODO fix the fold to allow any number of dispositions
    lines = (
        alt.Chart()
        .transform_fold(fold=plot_columns, as_=["Projected", "value"])
        .encode(x=alt.X(**x), y=alt.Y(**y), color=color, tooltip=tooltip)
        .mark_line()
        .properties(
            title={
                "text": "Number of Regional Susceptible, Infected, and Recovered Individuals"
            }
        )
    )
    bar = (
        alt.Chart()
        .encode(x=alt.X(**x))
        .transform_filter(alt.datum.day == 0)
        .mark_rule(color="black", opacity=0.35, size=2)
    )
    charts = [lines, bar]
    if actuals is not None:
        sim_sir_w_date_floor_df, actuals_plot_columns, actuals_color = get_actual_columns_and_colors(
            ["daily_regional_infections"], sim_sir_w_date_floor_df, actuals, p, alt,
        )
        actuals_tooltip=[alt.Tooltip("utcmonthdate(date):O", title="Date", format=(DATE_FORMAT)), alt.Tooltip("value:Q", format=".0f"), "Actual:N"]
        actuals_lines = (
            alt.Chart()
            .transform_fold(fold=actuals_plot_columns, as_=["Actual", "value"])
            .encode(x=alt.X(**x), y=alt.Y(**y), color=actuals_color, tooltip=actuals_tooltip)
            .mark_line(point=True, opacity=1.)
        )
        charts.append(actuals_lines)
    return alt.layer(*charts, data=sim_sir_w_date_floor_df).resolve_scale(color="independent")

def build_beds_chart(
    alt, 
    beds_floor_df: pd.DataFrame, 
    parameters: Parameters,
) -> Chart:
    """docstring"""
    y_scale = alt.Scale()
    if parameters.max_y_axis_set:
        y_scale.domain = (-parameters.max_y_axis, parameters.max_y_axis)
        y_scale.clamp = True

    beds_floor_df, beds_columns, proj_color = get_proj_columns_and_colors(
        beds_floor_df, parameters, alt)
    beds_floor_df["zero"] = 0
    x = dict(shorthand="date:T", title="Date", axis=alt.Axis(format=(DATE_FORMAT)))
    y = dict(shorthand="value:Q", title="COVID-19 Capacity", scale=y_scale)
    tooltip = ["Projected:N", alt.Tooltip("value:Q", format=".0f")]
    tooltip = [alt.Tooltip("utcmonthdate(date):O", title="Date", format=(DATE_FORMAT)), alt.Tooltip("value:Q", format=".0f"), "Projected:N"]

    
    beds = (
        alt.Chart()
        .transform_fold(fold=beds_columns, as_=["Projected", "value"])
        .encode(x=alt.X(**x), y=alt.Y(**y), color=proj_color, tooltip=tooltip)
        .mark_line()
        .properties(
            title={
                "text": "Projected Number of Available COVID-19 Beds",
                "subtitle": "Accounts for Arrivals and Discharges."
            }
        )
    )
    bar = (
        alt.Chart()
        .encode(x=alt.X(**x))
        .transform_filter(alt.datum.day == 0)
        .mark_rule(color="black", opacity=0.35, size=2)
    )
    hbar = (
        alt.Chart()
        .transform_fold(fold=["zero"])
        .encode(x=alt.X(**x), y=alt.Y("value:Q"))
        .mark_line(point=False, color="black", strokeDash=[5,3], opacity=0.35,)
    )
    return alt.layer(beds, bar, hbar, data=beds_floor_df)


def build_ppe_chart(
    *,
    alt,
    ppe_floor_df: pd.DataFrame,
    p: Parameters,
    plot_columns: str,
) -> Chart:
    """Build ppe chart."""
    k = list(p.ppe_labels.keys())[3:]
    if plot_columns not in k:
        raise ValueError("PPE type must be in %s" % (k))

    y_scale = alt.Scale()
    if p.max_y_axis_set:
        y_scale.domain = (0, p.max_y_axis)
        y_scale.clamp = True
    
    # labels
    chart_title = p.ppe_labels[plot_columns]["label"]
    y_axis_label = "Required " + chart_title
    # departments
    ppe_floor_df = ppe_floor_df.rename(columns={
        p.ppe_labels[plot_columns]["col1_name"]: p.ppe_labels["total"],
        p.ppe_labels[plot_columns]["col2_name"]: p.ppe_labels["non_icu"],
        p.ppe_labels[plot_columns]["col3_name"]:p.ppe_labels["icu"],
    })
    plot_columns = [
        p.ppe_labels["total"],
        p.ppe_labels["non_icu"],
        p.ppe_labels["icu"],
    ]
    # Set colors
    proj_color = alt.Color(
        "Department:N", 
        sort=plot_columns,
        scale = alt.Scale(
            domain=plot_columns,
            range=['black', '#4C78A8', '#F58518'],
        )
    )
    x = dict(shorthand="date:T", title="Date",
             axis=alt.Axis(format=(DATE_FORMAT)))
    y = dict(shorthand="value:Q", title=y_axis_label, scale=y_scale)
    tooltip = [alt.Tooltip("utcmonthdate(date):O", title="Date", format=(
        DATE_FORMAT)), alt.Tooltip("value:Q", format=".0f", title=chart_title), "Department:N"]

    # TODO fix the fold to allow any number of dispositions
    lines = (
        alt.Chart(title=chart_title)
        .transform_fold(fold=plot_columns, as_=["Department", "value"])
        .encode(x=alt.X(**x), y=alt.Y(**y), color=proj_color, tooltip=tooltip)
        .mark_line()
    )
    bar = (
        alt.Chart()
        .encode(x=alt.X(**x))
        .transform_filter(alt.datum.day == 0)
        .mark_rule(color="black", opacity=0.35, size=2)
    )
    charts = [lines, bar]
    return (
        alt.layer(*charts, data=ppe_floor_df)
        .resolve_scale(color="independent")
        .configure_title(fontSize=18)
    )

def build_staffing_chart(
    *,
    alt,
    staffing_floor_df: pd.DataFrame,
    p: Parameters,
    plot_columns: str,
) -> Chart:
    """Build staffing chart."""
    k = list(p.staffing_labels.keys())[3:]
    if plot_columns not in k:
        raise ValueError("Staffing role must be in %s" % (k))

    y_scale = alt.Scale()
    if p.max_y_axis_set:
        y_scale.domain = (0, p.max_y_axis)
        y_scale.clamp = True

    # labels
    chart_title = p.staffing_labels[plot_columns]["label"]
    y_axis_label = "Required " + chart_title
    # departments
    staffing_floor_df = staffing_floor_df.rename(columns={
        p.staffing_labels[plot_columns]["col1_name"]: p.staffing_labels["total"],
        p.staffing_labels[plot_columns]["col2_name"]: p.staffing_labels["non_icu"],
        p.staffing_labels[plot_columns]["col3_name"]: p.staffing_labels["icu"],
    })
    plot_columns = [
        p.staffing_labels["total"], 
        p.staffing_labels["non_icu"],
        p.staffing_labels["icu"],
    ] 
    # Set colors
    proj_color = alt.Color(
        "Department:N",
        sort=plot_columns,
        scale=alt.Scale(
            domain=plot_columns,
            range=['black', '#4C78A8', '#F58518'],
        )
    )
    x = dict(shorthand="date:T", title="Date",
             axis=alt.Axis(format=(DATE_FORMAT)))
    y = dict(shorthand="value:Q", title=y_axis_label, scale=y_scale)
    tooltip = [alt.Tooltip("utcmonthdate(date):O", title="Date", format=(
        DATE_FORMAT)), alt.Tooltip("value:Q", format=".0f", title=chart_title), "Department:N"]

    # TODO fix the fold to allow any number of dispositions
    lines = (
        alt.Chart(title=chart_title)
        .transform_fold(fold=plot_columns, as_=["Department", "value"])
        .encode(x=alt.X(**x), y=alt.Y(**y), color=proj_color, tooltip=tooltip)
        .mark_line()
    )
    bar = (
        alt.Chart()
        .encode(x=alt.X(**x))
        .transform_filter(alt.datum.day == 0)
        .mark_rule(color="black", opacity=0.35, size=2)
    )
    charts = [lines, bar]
    return (
        alt.layer(*charts, data=staffing_floor_df)
        .resolve_scale(color="independent")
        .configure_title(fontSize=18)
    )

def build_descriptions(
    *,
    chart: Chart,
    labels: dict,
) -> str:
    """

    :param chart: The alt chart to be used in finding max points
    :param suffix: The assumption is that the charts have similar column names.
                   The census chart adds " Census" to the column names.
                   Make sure to include a space or underscore as appropriate
    :return: Returns a multi-line string description of the results
    """
    messages = ["Based upon **projections**:\n"]

    cols = ["Total", "Non-ICU", "ICU", "Ventilators"]
    asterisk = False
    day = "date" if "date" in chart.data.columns else "day"

    for col in cols:
        if chart.data[col].idxmax() + 1 == len(chart.data):
            asterisk = True

        # todo: bring this to an optional arg / i18n
        on = datetime.strftime(chart.data[day][chart.data[col].idxmax()], "%b %d")

        messages.append(
            "* {} {:,} patients on {}{}".format(
                labels[col],
                ceil(chart.data[col].max()),
                on,
                "*" if asterisk else "",
            )
        )

    if asterisk:
        messages.append("* _The max is at the upper bound of the data, and therefore may not be the actual max_")
    return "  \n".join(messages)

def build_bed_descriptions(
    *,
    chart: Chart,
    labels: dict,
) -> str:
    """

    :param chart: The alt chart to be used in finding max points
    :param suffix: The assumption is that the charts have similar column names.
                   The census chart adds " Census" to the column names.
                   Make sure to include a space or underscore as appropriate
    :return: Returns a multi-line string description of the results
    """
    messages = []

    cols = ["Total", "Non-ICU", "ICU", "Ventilators"]
    asterisk = False
    
    # Add note if lines overlap.
    if sum(np.where(chart.data["Total"] == chart.data["ICU"], 1, 0)) > 1 or \
         sum(np.where(chart.data["Total"] == chart.data["Non-ICU"], 1, 0)) > 1:
        messages.append("_The overlapping lines represent non-ICU patients being housed in the ICU or vice versa._")

    for col in cols:
        if np.nanmin(chart.data[col]) > 0:
            asterisk = True
            messages.append("_{} are never exhausted._".format(labels[col]))
            continue

        on = chart.data["date"][chart.data[col].le(0).idxmax()]
        on = datetime.strftime(on, "%b %d")  # todo: bring this to an optional arg / i18n

        messages.append(
            "* {} are exhausted on {}".format(
                labels[col],
                on,
            )
        )

    return "  \n".join(messages)


def build_ppe_descriptions(
    *,
    chart: Chart,
    label: str,
) -> str:
    """
    """
    messages = []

    cols = ["Total", "Non-ICU", "ICU"]
    asterisk = False
    day = "date" if "date" in chart.data.columns else "day"

    for col in cols:
        if chart.data[col].idxmax() + 1 == len(chart.data):
            asterisk = True

        # todo: bring this to an optional arg / i18n
        on = datetime.strftime(
            chart.data[day][chart.data[col].idxmax()], "%b %d")

        messages.append(
            "* {} {} peak at {:,}/day on {}{}".format(
                col,
                label,
                ceil(chart.data[col].max()),
                on,
                "*" if asterisk else "",
            )
        )

    if asterisk:
        messages.append(
            "* _The max is at the upper bound of the data, and therefore may not be the actual max_")
    return "  \n".join(messages)

def build_staffing_descriptions(
    *,
    chart: Chart,
    label: str,
    shift_duration: int,
) -> str:
    """
    """
    messages = []

    cols = ["Total", "Non-ICU", "ICU"]
    asterisk = False
    day = "date" if "date" in chart.data.columns else "day"

    messages.append("_Based on {}-hour shift._".format(shift_duration))

    for col in cols:
        if chart.data[col].idxmax() + 1 == len(chart.data):
            asterisk = True

        # todo: bring this to an optional arg / i18n
        on = datetime.strftime(
            chart.data[day][chart.data[col].idxmax()], "%b %d")

        messages.append(
            "* {} {} peak at {:,} shifts/day on {}{}".format(
                col,
                label,
                ceil(chart.data[col].max()),
                on,
                "*" if asterisk else "",
            )
        )

    if asterisk:
        messages.append(
            "* _The max is at the upper bound of the data, and therefore may not be the actual max_")
    return "  \n".join(messages)

def build_table(
    *,
    df: pd.DataFrame,
    labels: Dict[str, str],
    modulo: int = 1,
) -> pd.DataFrame:
    table_df = df[np.mod(df.day, modulo) == 0].copy()
    table_df.date = table_df.date.dt.strftime(DATE_FORMAT)
    table_df.rename(labels)
    # Remove non_icu_after_icu column when printing
    if "non_icu_after_icu" in table_df.columns:
        table_df = table_df.drop(columns="non_icu_after_icu")

    if "masks_n95_icu" in table_df.columns:
        table_df = table_df[[
            "day",
            "date",
            "masks_n95_total",
            "masks_n95_non_icu",
            "masks_n95_icu",
            "masks_surgical_total",
            "masks_surgical_non_icu",
            "masks_surgical_icu",
            "face_shield_total",
            "face_shield_non_icu",
            "face_shield_icu",
            "gloves_total",
            "gloves_non_icu",
            "gloves_icu",
            "gowns_total",
            "gowns_non_icu",
            "gowns_icu",
            "other_ppe_total",
            "other_ppe_non_icu",
            "other_ppe_icu",
        ]]
    if "nurses_icu" in table_df.columns:
        table_df = table_df[[
            "day",
            "date",
            "nurses_total",
            "nurses_non_icu",
            "nurses_icu",
            "physicians_total",
            "physicians_non_icu",
            "physicians_icu",
            "advanced_practice_providers_total",
            "advanced_practice_providers_non_icu",
            "advanced_practice_providers_icu",
            "healthcare_assistants_total",
            "healthcare_assistants_non_icu",
            "healthcare_assistants_icu",
        ]]
    return table_df
