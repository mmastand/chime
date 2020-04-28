import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime, date, timedelta

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
        "dbT_prd_spln": "Log-Spline",
        "dbT_prd_ets": "Exponential Smoothing",
        "dbT_prd_loess": "Loess",
        "b": "Beta",
        "s": "Susceptible",
        "i": "Infected",
        "r": "Recovered",
        "n": "Newly Infected",
        "rst": "rst",
    }
    return(pcn)

def plot_dynamic_doubling_fit(d):
    DATE_FORMAT = "%b %d"
    y_scale = alt.Scale(
    #    domain=(0, 70),
    #    clamp=True,
    )
    
    # Drop Rt columns
    d = d.drop(columns=["Rt_prd_spln", "Rt_prd_ets", "Rt_prd_loess"])

    # Only show 60 days into future
    d = d.loc[d.date <= (datetime.today() + timedelta(days=60))]

    # Add fcst column
    d["fcst"] = np.where(d.cases.isnull(), 1, 0)
    
    # Zero cases where we have forecast
    d.dbT.loc[d.fcst == 1] = np.nan
    # Zero infected where we have actuals
    d.dbT_prd_ets.loc[d.fcst == 0] = np.nan
    d.dbT_prd_loess.loc[d.fcst == 0] = np.nan
    d.dbT_prd_spln.loc[d.fcst == 0] = np.nan
    
    # Names for display
    pcn = get_names_for_display()
    d = d.rename(columns=pcn)
    plot_columns = ["Log-Spline", "Exponential Smoothing", "Loess"]

    # Chart title
    title = str(d.rgn.iloc[0] + " Doubling Time")

    # Forecast Chart
    x = dict(shorthand="date:T", title="Date", axis=alt.Axis(format=(DATE_FORMAT)))
    y = dict(shorthand="Fit:Q", title="Doubling Time", scale=y_scale)
    color = alt.Color("Forecast Method:N",
                    scale=alt.Scale(scheme="dark2"))
    fc = (alt.Chart(data=d, title=title)
        .transform_fold(fold=plot_columns, as_=["Forecast Method", "Fit"],)
        .encode(x=alt.X(**x), y=alt.Y(**y), color=color,)
        .mark_line()
        )

    # Points
    db_points = (
        alt.Chart(data=d)
        .encode(x="date:T", y="Doubling Time:Q")
        .mark_point(filled=True, color="black")
    )  
    # Points
    db_line = (
        alt.Chart(data=d)
        .encode(x="date:T", y="Doubling Time:Q")
        .mark_line(color="black")
    )



    chart = [db_points, db_line, fc]
    chart = alt.layer(*chart, data=d)
    return(chart)

def plot_Rt_fit(d):
    DATE_FORMAT = "%b %d"
    y_scale = alt.Scale(
           domain = (0, 20),
           clamp = True,
    )

    # Drop dbT columns
    d = d.drop(columns=["dbT_prd_spln", "dbT_prd_ets", "dbT_prd_loess"])

    # Only show 60 days into future
    d = d.loc[d.date <= (datetime.today() + timedelta(days=14))]

    # Add fcst column
    d["fcst"] = np.where(d.Rt.isnull(), 1, 0)

    # Zero cases where we have forecast
    d.Rt.loc[d.fcst == 1] = np.nan
    # Zero infected where we have actuals
    d.Rt_prd_ets.loc[d.fcst == 0] = np.nan
    d.Rt_prd_loess.loc[d.fcst == 0] = np.nan
    d.Rt_prd_spln.loc[d.fcst == 0] = np.nan

    # Names for display
    pcn = get_names_for_display()
    d = d.rename(columns=pcn)

    # Chart title
    title = str(d.rgn.iloc[0] + " Reproduction Rate")

    d["one"] = 1

    # Lines
    x = dict(shorthand="date:T", title="Date", axis=alt.Axis(format=(DATE_FORMAT)))
    y = dict(shorthand="Fit:Q", title="Reproduction Rate", scale=y_scale)
    plot_columns = ["Log-Spline", "Exponential Smoothing", "Loess"]
    color = alt.Color("Forecast Method:N",
                      scale=alt.Scale(scheme="dark2"))

    fc = (
        alt.Chart(data=d, title=title)
        .transform_fold(fold=plot_columns, as_=["Forecast Method", "Fit"])
        .encode(x=alt.X(**x), y=alt.Y(**y), color=color)
        .mark_line()
    )
    
    # Points
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

    p = (
        alt.layer(fc, rt_line, rt_points, conf, dash)
    )
    return(p)

def plot_daily_cases(d):
    DATE_FORMAT = "%b %d"
    y_scale = alt.Scale(
        #    domain = (0, 40),
        #    clamp = True,
    )
    #  Drop dbT columns
    d = d.drop(columns=["dbT_prd_spln", "dbT_prd_ets", "dbT_prd_loess"])
    
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
    
    # Chart title
    title = str(d.rgn.iloc[0] + " Daily Cases")

    x = dict(shorthand="date:T", title="Date",
             axis=alt.Axis(format=(DATE_FORMAT)))
    y = dict(shorthand="Newly Infected:Q", title="Reproduction Rate", scale=y_scale)
    color = alt.Color("Forecast Method:N",
                      scale=alt.Scale(scheme="dark2"))
    fc = (
        alt.Chart(data=d, title=title)
        .transform_fold(fold=["Newly Infected"], as_=["Forecast Method", "Fit"])
        .encode(x=alt.X(**x), y=alt.Y(**y), color=color)
        .mark_line()
    )

    # Points
    hist_points = (
        alt.Chart(data=d)
        .encode(x="date:T", y="Daily Cases:Q")
        .mark_point(color="black", fill="black")
    )
    # Points
    hist_line = (
        alt.Chart(data=d)
        .encode(x="date:T", y="Daily Cases:Q")
        .mark_line(color="black")
    )
    p = (
        alt.layer(fc, hist_line, hist_points)
    )
    return(p)
