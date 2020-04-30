import datetime

import altair as alt 
import numpy as np
import pandas as pd
import streamlit as st

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
from penn_chime.hc_actuals import census_mismatch_message
from penn_chime.utils import dataframe_to_base64


def display_body_charts(m, p: "Parameters", d: "Parameters", actuals: "pd.DataFrame", mode: "Mode"):

    st.subheader("New Hospital Admissions")
    admits_chart = build_admits_chart(alt=alt, admits_floor_df=m.admits_floor_df, p=p, actuals=actuals)
    st.altair_chart(admits_chart, use_container_width=True)
    st.markdown(build_descriptions(chart=admits_chart,
                                labels=p.admits_patient_chart_desc,))
    display_download_link(
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
    census_chart = build_census_chart(alt=alt, census_floor_df=m.census_floor_df, p=p, actuals=actuals)
    st.altair_chart(census_chart, use_container_width=True)
    # Display census mismatch message if appropriate
    census_mismatch_message(parameters=p, actuals=actuals, st=st)
    st.markdown(build_descriptions(chart=census_chart,
                                labels=p.census_patient_chart_desc,))
    display_download_link(
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
    beds_chart = build_beds_chart(alt=alt, beds_floor_df=m.beds_df, parameters=p)
    st.altair_chart(beds_chart, use_container_width=True)
    st.markdown(build_bed_descriptions(chart=beds_chart, labels=p.beds_chart_desc))
    display_download_link(
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
    sim_sir_w_date_chart = build_sim_sir_w_date_chart(alt=alt, sim_sir_w_date_floor_df=m.sim_sir_w_date_floor_df, actuals=actuals, p = p)
    st.altair_chart(sim_sir_w_date_chart, use_container_width=True)
    display_download_link(
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
    st.markdown("Quantity of PPE required per day")
    for pc in list(p.ppe_labels.keys())[3:]:
        ppe_chart = build_ppe_chart(
            alt=alt, ppe_floor_df=m.ppe_floor_df, p=p, plot_columns=pc)
        st.altair_chart(ppe_chart, use_container_width=True)
        st.markdown(build_ppe_descriptions(chart=ppe_chart, label = p.ppe_labels[pc]["label"]))
        st.markdown("  \n  \n")
    display_download_link(
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
    st.markdown("Number of staff required per day")
    for pc in list(p.staffing_labels.keys())[3:]:
        staffing_chart = build_staffing_chart(
            alt=alt, staffing_floor_df=m.staffing_floor_df, p=p, plot_columns=pc)
        st.altair_chart(staffing_chart, use_container_width=True)
        st.markdown(build_staffing_descriptions(
            chart=staffing_chart, label=p.staffing_labels[pc]["label"], shift_duration=p.shift_duration))
        st.markdown("  \n  \n")
    display_download_link(
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


def display_download_link(filename: str, df: pd.DataFrame):
    csv = dataframe_to_base64(df)
    st.markdown(
        """
        <a download="{filename}" href="data:file/csv;base64,{csv}">Download {filename}</a>
""".format(
            csv=csv, filename=filename
        ),
        unsafe_allow_html=True,
    )


def non_date_columns_to_int(df):
    for column in df.columns:
        if column != 'date':
            df[column] = df[column].astype(int)
    return df


def build_data_and_params(projection_admits, census_df, beds_df, ppe_df, staffing_df, model, parameters):
    # taken from admissions table function:
    admits_table = projection_admits[np.mod(projection_admits.index, 1) == 0].copy()
    admits_table["day"] = admits_table.index.astype(int)
    admits_table.index = range(admits_table.shape[0])
    admits_table = admits_table.fillna(0)
    admits_table = non_date_columns_to_int(admits_table)
    admits_table.rename(parameters.labels)

    # taken from census table function:
    census_table = census_df[np.mod(census_df.index, 1) == 0].copy()
    census_table.index = range(census_table.shape[0])
    census_table.loc[0, :] = 0
    census_table = census_table.dropna()
    census_table = non_date_columns_to_int(census_table)
    census_table.rename(parameters.labels)
    
    # taken from beds table function:
    bed_table = beds_df[np.mod(beds_df.index, 1) == 0].copy()
    bed_table.index = range(bed_table.shape[0])
    bed_table.total[0] = parameters.total_covid_beds - 1
    bed_table.non_icu[0] = parameters.total_covid_beds - parameters.icu_covid_beds - 1
    bed_table.icu[0] = parameters.icu_covid_beds - 1
    bed_table.ventilators[0] = parameters.covid_ventilators - 1
    bed_table = bed_table.dropna()
    bed_table = non_date_columns_to_int(bed_table)
    bed_table.rename(parameters.labels)

    # taken from raw sir table function:
    projection_area = pd.DataFrame({
        'susceptible': model.raw['susceptible'],
        'infected': model.raw['infected'],
        'recovered': model.raw['recovered'],
    })
    infect_table = (projection_area.iloc[::1, :]).apply(np.floor)
    infect_table.index = range(infect_table.shape[0])
    infect_table["day"] = infect_table.index
    infect_table = non_date_columns_to_int(infect_table)

    # Build full dataset
    df = pd.DataFrame(index=np.arange(admits_table.shape[0]))

    ########## Params ###########
    df["Author"] = parameters.author
    df["Scenario"] = parameters.scenario
    df["DateGenerated"] = (datetime.datetime.utcnow() - datetime.timedelta(hours=6)).isoformat()
    
    # Census and Severity
    df["CovidCensusValue"] = parameters.covid_census_value
    df["CovidCensusDate"] = parameters.covid_census_date
    df["DoublingTimeBeforeSocialDistancing"] = parameters.doubling_time
    df["SocialDistancingPercentReduction"] = parameters.relative_contact_rate
    df["SocialDistancingStartDate"] = parameters.mitigation_date
    df["DateFirstHospitalized"] = parameters.date_first_hospitalized
    df["InfectiousDays"] = parameters.infectious_days

    df["NonICUPercentage"] = parameters.non_icu.rate
    df["ICUPercentage"] = parameters.icu.rate
    df["VentilatorsPercentage"] = parameters.ventilators.rate

    df["NonICULengthOfStay"] = parameters.non_icu.days
    df["ICULengthOfStay"] = parameters.icu.days
    df["VentLengthOfStay"] = parameters.ventilators.days

    df["HospitalMarketShare"] = parameters.market_share
    df["RegionalPopulation"] = parameters.population

    # Bed Params
    df["BedBorrowing"] = parameters.beds_borrow
    df["TotalNumberOfBedsForCOVIDPatients"] = parameters.total_covid_beds
    df["TotalNumberOfICUBedsFoCOVIDPatients"] = parameters.icu_covid_beds
    df["TotalNumberOfVentsFoCOVIDPatients"] = parameters.covid_ventilators

    # PPE Params
    df["MasksN95Param"] = parameters.masks_n95
    df["MasksSurgicalParam"] = parameters.masks_surgical
    df["FaceShieldsParam"] = parameters.face_shield
    df["GlovesParam"] = parameters.gloves
    df["GownsParam"] = parameters.gowns
    df["OtherPPEParam"] = parameters.other_ppe
    df["MasksN95ICUParam"] = parameters.masks_n95_icu
    df["MasksSurgicalICUParam"] = parameters.masks_surgical_icu
    df["FaceShieldsICUParam"] = parameters.face_shield_icu
    df["GlovesICUParam"] = parameters.gloves_icu
    df["GownsICUParam"] = parameters.gowns_icu
    df["OtherPPEICUParam"] = parameters.other_ppe_icu

    # Staffing Params
    df["PatientsPerNurses"] = parameters.nurses
    df["PatientsPerPhysicians"] = parameters.physicians
    df["PatientsPerAdvancedPraticeProviders"] = parameters.advanced_practice_providers
    df["PatientsPerHealthcareAssistants"] = parameters.healthcare_assistants

    df["PatientsPerNursesICU"] = parameters.nurses_icu
    df["PatientsPerPhysiciansICU"] = parameters.physicians_icu
    df["PatientsPerAdvancedPraticeProvidersICU"] = parameters.advanced_practice_providers_icu
    df["PatientsPerHealthcareAssistantsICU"] = parameters.healthcare_assistants_icu

    df["ShiftDuration"] = parameters.shift_duration

    ########## Projected ###########
    df["Date"] = admits_table["date"]

    # Admits, Census, SIR, Beds
    df["TotalAdmissions"] = admits_table["total"]
    df["NonICUAdmissions"] = admits_table["non_icu"]
    df["ICUAdmissions"] = admits_table["icu"]
    df["VentilatorsAdmissions"] = admits_table["ventilators"]

    df["TotalCensus"] = census_table["total"]
    df["NonICUCensus"] = census_table["non_icu"]
    df["ICUCensus"] = census_table["icu"]
    df["VentilatorsCensus"] = census_table["ventilators"]

    df["Susceptible"] = infect_table["susceptible"]
    df["Infections"] = infect_table["infected"]
    df["Recovered"] = infect_table["recovered"]
    
    df["TotalBeds"] = bed_table["total"]
    df["NonICUBeds"] = bed_table["non_icu"]
    df["ICUBeds"] = bed_table["icu"]
    df["Ventilators"] = bed_table["ventilators"]

    # PPE
    ppe_df.loc[0, :] = 0
    df["MasksN95Total"] = ppe_df.masks_n95_total
    df["MasksN95NonICU"] = ppe_df.masks_n95_non_icu
    df["MasksN95ICU"] = ppe_df.masks_n95_icu

    df["MasksSurgicalTotal"] = ppe_df.masks_surgical_total
    df["MasksSurgicalNonICU"] = ppe_df.masks_surgical_non_icu
    df["MasksSurgicalICU"] = ppe_df.masks_surgical_icu
    
    df["FaceShieldsTotal"] = ppe_df.face_shield_total
    df["FaceShieldsNonICU"] = ppe_df.face_shield_non_icu
    df["FaceShieldsICU"] = ppe_df.face_shield_icu
    
    df["GlovesTotal"] = ppe_df.gloves_total
    df["GlovesNonICU"] = ppe_df.gloves_non_icu
    df["GlovesICU"] = ppe_df.gloves_icu
    
    df["GownsTotal"] = ppe_df.gowns_total
    df["GownsNonICU"] = ppe_df.gowns_non_icu
    df["GownsICU"] = ppe_df.gowns_icu
    
    df["OtherPPETotal"] = ppe_df.other_ppe_total
    df["OtherPPENonICU"] = ppe_df.other_ppe_non_icu
    df["OtherPPEICU"] = ppe_df.other_ppe_icu
    
    # Staffing
    staffing_df.loc[0, :] = 0
    df["NursesTotal"] = staffing_df.nurses_total
    df["NursesNonICU"] = staffing_df.nurses_non_icu
    df["NursesICU"] = staffing_df.nurses_icu

    df["PhysiciansTotal"] = staffing_df.physicians_total
    df["PhysiciansNonICU"] = staffing_df.physicians_non_icu
    df["PhysiciansICU"] = staffing_df.physicians_icu

    df["AdvancedPraticeProvidersTotal"] = staffing_df.advanced_practice_providers_total
    df["AdvancedPraticeProvidersNonICU"] = staffing_df.advanced_practice_providers_non_icu
    df["AdvancedPraticeProvidersICU"] = staffing_df.advanced_practice_providers_icu

    df["HealthcareAssistantsTotal"] = staffing_df.healthcare_assistants_total
    df["HealthcareAssistantsNonICU"] = staffing_df.healthcare_assistants_non_icu
    df["HealthcareAssistantsICU"] = staffing_df.healthcare_assistants_icu

    df["OtherStaffTotal"] = staffing_df.other_staff_total
    df["OtherStaffNonICU"] = staffing_df.other_staff_non_icu
    df["OtherStaffICU"] = staffing_df.other_staff_icu
    return(df)
