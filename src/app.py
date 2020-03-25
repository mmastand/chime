"""App."""

import altair as alt  # type: ignore
import streamlit as st  # type: ignore

from penn_chime.presentation import (
    build_download_link,
    display_header,
    display_sidebar,
    draw_census_table,
    draw_projected_admissions_table,
    draw_raw_sir_simulation_table,
    hide_menu_style,
    show_additional_projections,
    show_more_info_about_this_tool,
    write_definitions,
    write_footer,
    build_data_and_params,
    display_how_to_use
)
from penn_chime.settings import DEFAULTS
from penn_chime.models import SimSirModel
from penn_chime.charts import (
    additional_projections_chart,
    admitted_patients_chart,
    new_admissions_chart,
    chart_descriptions,
)
from penn_chime.utils import dataframe_to_base64

# This is somewhat dangerous:
# Hide the main menu with "Rerun", "run on Save", "clear cache", and "record a screencast"
# This should not be hidden in prod, but removed
# In dev, this should be shown
st.markdown(hide_menu_style, unsafe_allow_html=True)

p = display_sidebar(st, DEFAULTS)
m = SimSirModel(p)

display_how_to_use(st)

display_header(st, m, p)


if st.checkbox("Show more info about this tool"):
    notes = "The total size of the susceptible population will be the entire catchment area"
    show_more_info_about_this_tool(st=st, model=m, parameters=p, defaults=DEFAULTS, notes=notes)

st.markdown("""The charts present the projected number of new admissions, census, and prevalence for COVID-19 patients
per day by patient category. **Each line describes a non-overlapping group.** For example, if we expect 25 new 
patients requiring hospitalization (blue line), 10 new patients requiring intensive care (orange line), and 
3 new patients requiring ventilation (red line), the total number of expected new admissions is 38 (25 + 10 + 3). 
This does not count patients who are presenting at the hospital unrelated to COVID-19.""")

st.subheader("New Admissions")
st.markdown("Projected number of **daily** COVID-19 admissions")
new_admit_chart = new_admissions_chart(alt, m.admits_df, parameters=p)
st.altair_chart(
    new_admissions_chart(alt, m.admits_df, parameters=p),
    use_container_width=True,
)

st.markdown(chart_descriptions(new_admit_chart, p.labels))

if st.checkbox("Show Projected Admissions in tabular form"):
    if st.checkbox("Show Daily Counts"):
        draw_projected_admissions_table(st, m.admits_df, p.labels, as_date=p.as_date, daily_count=True)
    else:
        draw_projected_admissions_table(st, m.admits_df, p.labels, as_date=p.as_date, daily_count=False)
    build_download_link(st,
        filename="projected_admissions.csv",
        df=m.admits_df,
        parameters=p
    )
st.subheader("Admitted Patients (Census)")
st.markdown(
    "Projected **census** of COVID-19 patients, accounting for arrivals and discharges"
)
census_chart = admitted_patients_chart(alt=alt, census=m.census_df, parameters=p)
st.altair_chart(
    admitted_patients_chart(alt=alt, census=m.census_df, parameters=p),
    use_container_width=True,
)
st.markdown(chart_descriptions(census_chart, p.labels, suffix=" Census"))
if st.checkbox("Show Projected Census in tabular form"):
    if st.checkbox("Show Daily Census Counts"):
        draw_census_table(st, m.census_df, p.labels, as_date=p.as_date, daily_count=True)
    else:
        draw_census_table(st, m.census_df, p.labels, as_date=p.as_date, daily_count=False)
    build_download_link(st,
        filename="projected_census.csv",
        df=m.census_df,
        parameters=p
    )

st.markdown(
    """**Click the checkbox below to view additional data generated by this simulation**"""
)
if st.checkbox("Show Additional Projections"):
    show_additional_projections(
        st, alt, additional_projections_chart, model=m, parameters=p
    )
    if st.checkbox("Show Raw SIR Simulation Data"):
        draw_raw_sir_simulation_table(st, model=m, parameters=p)


st.header("Export Full Data and Parameters")
df = build_data_and_params(projection_admits = m.admits_df, 
                           census_df = m.census_df, 
                           model = m, 
                           parameters = p)

if st.checkbox("Show full data and parameters to be exported"):
    st.dataframe(df)

if p.author == "Jane Doe" or p.scenario == "COVID Model":
    st.markdown("""
    **Enter a unique author name and scenario name to enable downloading.**""")
else:
    filename = "Data" + "_" + p.author + "_" + p.scenario + "_" + df.loc[0, "Date"] + ".csv"
    csv = dataframe_to_base64(df)
    st.markdown("""
            <a download="{filename}" href="data:text/plain;base64,{csv}">Download full table as CSV</a>
    """.format(csv=csv,filename=filename), unsafe_allow_html=True)

write_definitions(st)
write_footer(st)
