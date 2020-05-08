import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime, date, timedelta
import streamlit as st

def get_chart_segments(d):
    segs = d.loc[d.groupby('seg').date.idxmin()]
    segs = segs[["date", "seg"]]
    d = d.merge(segs, on="seg", how="left")
    d = d.rename(columns={"date_y": "date_group", "date_x": "date"})

    db_seg = []
    for row in d.itertuples():
        if pd.isnull(row.date_group):
            db_seg.append("dic")
        else:
            db_seg.append(
                f'{row.date_group.strftime("%m/%d/%Y")}: {row.dbT: .3f}')
    return db_seg

def get_names_for_display():
    pcn = {
        'cases': 'Daily Cases',
        'cumCases': 'Cumulative Cases',
        "mthd": "Method",
        "dbT": "Doubling Time",
        "Rt_prd_spln": "Log-Spline",
        "Rt_prd_ets": "Exponential Smoothing",
        "Rt_prd_loess": "Loess",
        "Rt_prd_lin": "Linear",
        "dbT_prd_spln": "Log-Spline",
        "dbT_prd_ets": "Exponential Smoothing",
        "dbT_prd_loess": "Loess",
        "dbT_prd_lin": "Linear",
        "b": "Beta",
        "s": "Susceptible",
        "i": "Infected",
        "r": "Recovered",
        "n": "n",
        "rst": "rst",
    }
    return(pcn)

def display_forecast_charts(d):
    dbT = plot_dynamic_doubling_fit(d)
    Rt = plot_Rt_fit(d)
    st.altair_chart(dbT, use_container_width=True)
    st.altair_chart(Rt, use_container_width=True)

def plot_dynamic_doubling_fit(d):
    DATE_FORMAT = "%b %d"
    y_scale = alt.Scale(
    #    domain=(0, 70),
    #    clamp=True,
    )
    
    # Drop Rt columns
    d = d.drop(columns=["Rt_prd_lin", "Rt_prd_spln",
                        "Rt_prd_ets", "Rt_prd_loess"])

    # Only show 60 days into future
    d = d.loc[d.date <= (datetime.today() + timedelta(days=60))]

    # Add fcst column
    d["fcst"] = np.where(d.cases.isnull(), 1, 0)
    
    # Zero cases where we have forecast
    d.dbT.loc[d.fcst == 1] = np.nan
    # Zero forecasts where we have actuals
    d.dbT_prd_ets.loc[d.fcst == 0] = np.nan
    d.dbT_prd_loess.loc[d.fcst == 0] = np.nan
    d.dbT_prd_spln.loc[d.fcst == 0] = np.nan
    d.dbT_prd_lin.loc[d.fcst == 0] = np.nan
    
    # Names for display
    pcn = get_names_for_display()
    d = d.rename(columns=pcn)
    plot_columns = ["Exponential Smoothing", "Loess", "Log-Spline", "Linear"]

    # Chart title
    title = "Doubling Time"

    # Forecast Chart
    x = dict(shorthand="date:T", title="Date", axis=alt.Axis(format=(DATE_FORMAT)))
    y = dict(shorthand="Fit:Q", title="Doubling Time (days)", scale=y_scale)
    tooltip = [alt.Tooltip("utcmonthdate(date):O", title="Date", format=(
        DATE_FORMAT)), alt.Tooltip("Fit:Q", format=".2f", title="Doubling Time (days)"), "Forecast Method:N"]
    color = alt.Color("Forecast Method:N",
                    scale=alt.Scale(scheme="dark2",
                                    domain=plot_columns))
    fc = (alt.Chart(data=d, title=title)
        .transform_fold(fold=plot_columns, as_=["Forecast Method", "Fit"],)
        .encode(x=alt.X(**x), y=alt.Y(**y), color=color, tooltip=tooltip, size=alt.value(3))
        .mark_line()
        )

    # Points
    tooltip = [alt.Tooltip("utcmonthdate(date):O", title="Date", format=(
        DATE_FORMAT)), alt.Tooltip("Doubling Time:Q", format=".2f", title="Doubling Time (days)")]
    db_points = (
        alt.Chart(data=d)
        .encode(x="date:T", y="Doubling Time:Q", tooltip=tooltip,)
        .mark_point(filled=True, color="black")
    )  
    # Points
    db_line = (
        alt.Chart(data=d)
        .encode(x="date:T", y="Doubling Time:Q")
        .mark_line(color="black")
    )

    bar = (
        alt.Chart(data=d)
        .encode(x=alt.X(**x))
        .transform_filter(alt.datum.day == 0)
        .mark_rule(color="black", opacity=0.35, size=2)
    )

    chart = [db_points, db_line, fc, bar]
    chart = alt.layer(*chart, data=d).configure_legend(symbolStrokeWidth=4, symbolSize=300, labelFontSize=12, titleFontSize=12)
    return(chart)

def plot_Rt_fit(d):
    DATE_FORMAT = "%b %d"
    y_scale = alt.Scale(
           domain = (0, 20),
           clamp = True,
    )

    # Drop dbT columns
    d = d.drop(columns=["dbT_prd_lin", "dbT_prd_spln", 
                        "dbT_prd_ets", "dbT_prd_loess"])

    # Only show 60 days into future
    # d = d.loc[d.date <= (datetime.today() + timedelta(days=14))]

    # Add fcst column
    d["fcst"] = np.where(d.Rt.isnull(), 1, 0)

    # Zero cases where we have forecast
    d.Rt.loc[d.fcst == 1] = np.nan
    # Zero forecasts where we have actuals
    d.Rt_prd_ets.loc[d.fcst == 0] = np.nan
    d.Rt_prd_loess.loc[d.fcst == 0] = np.nan
    d.Rt_prd_spln.loc[d.fcst == 0] = np.nan
    d.Rt_prd_lin.loc[d.fcst == 0] = np.nan

    # Names for display
    pcn = get_names_for_display()
    d = d.rename(columns=pcn)
    plot_columns = ["Exponential Smoothing", "Loess", "Log-Spline", "Linear"]


    # Chart title
    title = "Reproduction Rate"

    d["one"] = 1

    # Lines
    x = dict(shorthand="date:T", title="Date", axis=alt.Axis(format=(DATE_FORMAT)))
    y = dict(shorthand="Fit:Q", title="Reproduction Rate", scale=y_scale)
    tooltip = [alt.Tooltip("utcmonthdate(date):O", title="Date", format=(
        DATE_FORMAT)), alt.Tooltip("Fit:Q", format=".2f", title="Reproduction Rate"), "Forecast Method:N"]
    color = alt.Color("Forecast Method:N",
                      scale=alt.Scale(scheme="dark2",
                                      domain=plot_columns))

    fc = (
        alt.Chart(data=d, title=title)
        .transform_fold(fold=plot_columns, as_=["Forecast Method", "Fit"])
        .encode(x=alt.X(**x), y=alt.Y(**y), color=color, tooltip=tooltip, size=alt.value(3))
        .mark_line(strokeDash=[16, 3])
    )
    
    # Points
    tooltip = [alt.Tooltip("utcmonthdate(date):O", title="Date", format=(
        DATE_FORMAT)), alt.Tooltip("Rt:Q", format=".2f", title="Reproduction Rate")]
    rt_points = (
        alt.Chart(data=d)
        .encode(x="date:T", y="Rt:Q")
        .mark_point(color="black", fill="black")
    )  
    # Points
    rt_line = (
        alt.Chart(data=d)
        .encode(x="date:T", y="Rt:Q")
        .mark_line(color="black")
    )

    # Confidence bands
    conf = (
        alt.Chart(data=d)
        .mark_area(opacity=0.4, color='gray')
        .encode(x="date:T", y="RtLCL:Q", y2="RtUCL:Q")
    )

    # Dashed Line
    dash = (
        alt.Chart(data=d)
        .encode(x=alt.X(**x), y=alt.Y("one:Q"))
        .mark_line(color="black", opacity=0.35, size=2, strokeDash=[5, 3])
    )

    bar = (
        alt.Chart(data=d)
        .encode(x=alt.X(**x))
        .transform_filter(alt.datum.day == 0)
        .mark_rule(color="black", opacity=0.35, size=2)
    )

    p = (
        alt.layer(fc, rt_line, rt_points, conf, dash, bar)
        .configure_legend(symbolStrokeWidth=4, symbolSize=300, symbolDash=[8, 3], labelFontSize=12, titleFontSize=12)
    )
    return(p)


def display_daily_cases_forecast_chart(d):
    DATE_FORMAT = "%b %d"
    y_scale = alt.Scale(
        #    domain = (0, 40),
        #    clamp = True,
    )
    #  Drop dbT columns so that the plotting fucntion doesn't choke on them when renaming.s
    d = d.drop(columns=["dbT_prd_spln", "dbT_prd_ets", "dbT_prd_loess", "dbT_prd_lin"])
    
    # Only show x days into future
    # d = d.loc[d.date <= (datetime.today() + timedelta(days=60))]
    
    # Add fcst column
    d["fcst"] = np.where(d.cases.isnull(), 1, 0)

    # Zero cases where we have forecast
    d.cases.loc[d.fcst == 1] = np.nan
    # Zero infected where we have county
    d.n.loc[d.fcst == 0] = np.nan

    # Names for display
    pcn = get_names_for_display()
    d = d.rename(columns=pcn)
    # Specific to this function
    d["Actual"] = d["Daily Cases"]
    d["Projected"] = d["n"]
    
    # Chart title
    title = "Projected Regional Daily Cases"  # Get method to fit actuals and forecast
    act_fc = d.mSIR.iloc[0].split(",")
    inf_spr = "Reproduction Number" #act_fc[0]
    fc_mth = act_fc[1][1:] # Remove first space.
    subtitle = str("Model Generated from\n" + inf_spr + " and " + fc_mth)

    line_color_type = {
        "Doubling Time": {
            "chart": [16, 0],
            "legend": [16, 0],
        },
        "Reproduction Number": {
            "chart": [16, 3],
            "legend": [8, 3],
        },
        "ETS": "#1b9e77",
        "Loess": "#d95f02",
        "Log-Spline": "#7570b3",
        "Linear": "#e7298a",
    }               

    plot_columns = ["Actual", "Projected"]
    x = dict(shorthand="date:T", title="Date",
             axis=alt.Axis(format=(DATE_FORMAT)))
    y = dict(shorthand="fit:Q", title="Daily Cases", scale=y_scale)
    tooltip = [alt.Tooltip("utcmonthdate(date):O", title="Date", format=(
        DATE_FORMAT)), alt.Tooltip("fit:Q", format=".0f", title="New Cases")]
    
    color = alt.Color("Data Source:N",
                      sort=plot_columns,
                      scale=alt.Scale(domain=plot_columns,
                                      range=["black", line_color_type[fc_mth]]))
    strokeDash = alt.StrokeDash("Data Source:N",
                                scale=alt.Scale(
                                    domain=plot_columns,
                                    range=[[20, 0], [5,3]]))  # line_color_type[inf_spr]["chart"]]))
    fc = (
        alt.Chart(data=d, title=title)
        .transform_fold(fold=plot_columns, as_=["Data Source", "fit"])
        .encode(x=alt.X(**x), y=alt.Y(**y), color=color, tooltip=tooltip, size=alt.value(3), strokeDash=strokeDash)
        .mark_line()
        .properties(
            title={
                "text": title,
                "subtitle": subtitle
            }
        )
    )

    # Points
    tooltip = [alt.Tooltip("utcmonthdate(date):O", title="Date", format=(
        DATE_FORMAT)), alt.Tooltip("Daily Cases:Q", format=".0f", title="New Cases")]
    hist_points = (
        alt.Chart(data=d)
        .encode(x="date:T", y="Daily Cases:Q", tooltip=tooltip)
        .mark_point(color="black", fill="black")
    )

    bar = (
        alt.Chart(data=d)
        .encode(x=alt.X(**x))
        .transform_filter(alt.datum.day == 0)
        .mark_rule(color="black", opacity=0.35, size=2)
    )
 
    p = (
        alt.layer(fc, hist_points, bar)
        .configure_legend(symbolStrokeWidth=4, symbolSize=300, labelFontSize=12, titleFontSize=12)
    )
    return(p)
    # st.altair_chart(p, use_container_width=True)
