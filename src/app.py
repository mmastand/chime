from sys import stdout
from logging import INFO, basicConfig

basicConfig(
    level=INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=stdout,
)

import datetime

import altair as alt  # type: ignore
import streamlit as st  # type: ignore

from penn_chime.presentation import (
    display_download_link,
    display_header,
    display_more_info,
    display_sidebar,
    hide_menu_style,
    write_definitions,
    write_footer,
    build_data_and_params,
)
from penn_chime.settings import get_defaults
from penn_chime.penn_model import PennModel
from penn_chime.empirical_model import EmpiricalModel
from penn_chime.charts import (
    build_admits_chart,
    build_census_chart,
    build_beds_chart,
    build_ppe_chart,
    build_staffing_chart,
    build_descriptions,
    build_bed_descriptions,
    build_ppe_descriptions,
    build_staffing_descriptions,
    build_sim_sir_w_date_chart,
    build_table,
)
from penn_chime.utils import dataframe_to_base64
from penn_chime.hc_actuals import census_mismatch_message
from penn_chime.r_stuff import do_r_stuff, get_county_data
from penn_chime.parameters import Mode



# This is somewhat dangerous:
# Hide the main menu with "Rerun", "run on Save", "clear cache", and "record a screencast"
# This should not be hidden in prod, but removed
# In dev, this should be shown
st.markdown(hide_menu_style, unsafe_allow_html=True)

d = get_defaults()
mode = st.sidebar.radio("App Mode", [Mode.PENN_MODEL, Mode.EMPIRICAL])

p, actuals = display_sidebar(st, d, mode)
m = PennModel(p)

display_header(st, m, p)

result = do_r_stuff()
st.markdown(f"""R Stuff: {result}""")

# nyt_data = get_county_data()
# st.dataframe(nyt_data)

# states = list(nyt_data.state.unique()).sort()
# selected_states = st.multiselect("Please choose a state.", states)
# if len(selected_states) > 0:
#     counties = nyt_data.loc[nyt_data.state.isin(selected_states)].county.unique()
#     counties = list(counties).sort()
#     st.multiselect("Please choose a county.", counties)

if st.checkbox("Show more info about this tool"):
    notes = "The total size of the susceptible population will be the entire catchment area for our hospitals."
    display_more_info(st=st, model=m, parameters=p, defaults=d, notes=notes)

st.subheader("New Hospital Admissions")
st.markdown("Projected number of **daily** COVID-19 admissions.")
admits_chart = build_admits_chart(alt=alt, admits_floor_df=m.admits_floor_df, p=p, actuals=actuals)
st.altair_chart(admits_chart, use_container_width=True)
st.markdown(build_descriptions(chart=admits_chart,
                               labels=p.admits_patient_chart_desc,))
display_download_link(
    st,
    filename=f"{p.current_date}_projected_admits.csv",
    df=m.admits_df,
)

if st.checkbox("Show Projected Admissions in tabular form"):
    admits_modulo = 1
    if not st.checkbox("Show Daily Counts"):
        admits_modulo = 7
    table_df = build_table(
        df=m.admits_floor_df,
        labels=p.labels,
        modulo=admits_modulo)
    st.table(table_df)


st.subheader("Hospital Census")
st.markdown("Projected **census** of COVID-19 patients, accounting for arrivals and discharges.")
census_chart = build_census_chart(alt=alt, census_floor_df=m.census_floor_df, p=p, actuals=actuals)
st.altair_chart(census_chart, use_container_width=True)
# Display census mismatch message if appropriate
census_mismatch_message(parameters=p, actuals=actuals, st=st)
st.markdown(build_descriptions(chart=census_chart,
                               labels=p.census_patient_chart_desc,))
display_download_link(
    st,
    filename=f"{p.current_date}_projected_census.csv",
    df=m.census_df,
)
if st.checkbox("Show Projected Census in tabular form"):
    census_modulo = 1
    if not st.checkbox("Show Daily Census Counts"):
        census_modulo = 7
    table_df = build_table(
        df=m.census_floor_df,
        labels=p.labels,
        modulo=census_modulo)
    st.table(table_df)


st.subheader("COVID-19 Capacity")
st.markdown(
    "Projected **number** of available COVID-19 beds, accounting for admits and discharges"
)  
beds_chart = build_beds_chart(alt=alt, beds_floor_df=m.beds_df, parameters=p)
st.altair_chart(beds_chart, use_container_width=True)
st.markdown(build_bed_descriptions(chart=beds_chart, labels=p.beds_chart_desc))
display_download_link(
    st,
    filename=f"{p.current_date}_projected_capacity.csv",
    df=m.beds_df,
)

if st.checkbox("Show Projected Capacity in tabular form"):
    beds_modulo = 1
    if not st.checkbox("Show Daily Capacity Counts"):
        beds_modulo = 7
    table_df = build_table(
        df=m.beds_floor_df,
        labels=p.labels,
        modulo=beds_modulo)
    st.table(table_df)

st.subheader("Susceptible, Infected, and Recovered")
st.markdown("The number of susceptible, infected, and recovered individuals in the hospital catchment region at any given moment")
sim_sir_w_date_chart = build_sim_sir_w_date_chart(alt=alt, sim_sir_w_date_floor_df=m.sim_sir_w_date_floor_df, actuals=actuals, p = p)
st.altair_chart(sim_sir_w_date_chart, use_container_width=True)
display_download_link(
    st,
    filename=f"{p.current_date}_sim_sir_w_date.csv",
    df=m.sim_sir_w_date_df,
)

if st.checkbox("Show SIR Simulation in tabular form"):
    table_df = build_table(
        df=m.sim_sir_w_date_floor_df,
        labels=p.labels)
    st.table(table_df)

### PPE Section
st.subheader("Personal Protection Equipment")
st.markdown("The quantity of PPE needed per day")
for pc in list(p.ppe_labels.keys())[3:]:
    ppe_chart = build_ppe_chart(
        alt=alt, ppe_floor_df=m.ppe_floor_df, p=p, plot_columns=pc)
    st.altair_chart(ppe_chart, use_container_width=True)
    st.markdown(build_ppe_descriptions(chart=ppe_chart, label = p.ppe_labels[pc]["label"]))
    st.markdown("  \n  \n")
display_download_link(
    st,
    filename=f"{p.current_date}_projected_ppe_required.csv",
    df=m.ppe_df,
)
if st.checkbox("Show Projected PPE Required in tabular form"):
    ppe_modulo = 1
    if not st.checkbox("Show Daily PPE Required"):
        ppe_modulo = 7
    table_df = build_table(
        df=m.ppe_floor_df,
        labels=p.labels,
        modulo=ppe_modulo)
    st.dataframe(table_df)

### Staffing Section
st.subheader("Staffing")
st.markdown("The number of staff required per day")
for pc in list(p.staffing_labels.keys())[3:]:
    staffing_chart = build_staffing_chart(
        alt=alt, staffing_floor_df=m.staffing_floor_df, p=p, plot_columns=pc)
    st.altair_chart(staffing_chart, use_container_width=True)
    st.markdown(build_staffing_descriptions(
        chart=staffing_chart, label=p.staffing_labels[pc]["label"], shift_duration=p.shift_duration))
    st.markdown("  \n  \n")
display_download_link(
    st,
    filename=f"{p.current_date}_projected_staffing_required.csv",
    df=m.staffing_df,
)
if st.checkbox("Show Projected Staffing Required in tabular form"):
    staffing_modulo = 1
    if not st.checkbox("Show Daily Staffing Required"):
        staffing_modulo = 7
    table_df = build_table(
        df=m.staffing_floor_df,
        labels=p.labels,
        modulo=staffing_modulo)
    st.dataframe(table_df)

### Export Full Data and Parameters
st.header("Export Full Data and Parameters")
df = build_data_and_params(projection_admits = m.admits_df, 
                           census_df = m.census_df,
                           beds_df = m.beds_df, 
                           ppe_df = m.ppe_df,
                           staffing_df = m.staffing_df,
                           model = m, 
                           parameters = p)

if st.checkbox("Show full data and parameters to be exported"):
    st.dataframe(df)

filename = "Data" + "_" + p.author + "_" + p.scenario + "_" + (datetime.datetime.utcnow() - datetime.timedelta(hours=6)).isoformat() + ".csv"
csv = dataframe_to_base64(df)
st.markdown("""
        <a download="{filename}" href="data:text/plain;base64,{csv}">Download full table as CSV</a>
""".format(csv=csv,filename=filename), unsafe_allow_html=True)

if actuals is not None:
    if st.checkbox("Display Uploaded Actuals"):
        st.dataframe(actuals)

write_definitions(st)
write_footer(st)


