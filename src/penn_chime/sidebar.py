import os

import streamlit as st

from .hc_param_import_export import (
    constants_from_uploaded_file
)
from .hc_actuals import parse_actuals
from .parameters import ForecastMethod, ForecastedMetric, Mode, Parameters, Disposition
from .constants import EPSILON


def display_sidebar(d: Parameters) -> Parameters:
    # Initialize variables
    # these functions create input elements and bind the values they are set to
    # to the variables they are set equal to
    # it's kindof like ember or angular if you are familiar with those
    BUILD_TIME = os.environ['BUILD_TIME']
    VERSION_NUMBER = os.environ['VERSION_NUMBER']
    st.sidebar.markdown(
        f"""V: **{VERSION_NUMBER}** (**{BUILD_TIME}**)""",
        unsafe_allow_html=True,)
    st.sidebar.markdown("""
        <span style="font-size:medium;"><a href="#release_notes">Features and Enhancements History</a></span> 
    """, unsafe_allow_html=True)

    mode = st.sidebar.radio("App Mode", [Mode.PENN_MODEL, Mode.EMPIRICAL], index=1)

    st.sidebar.markdown(
        "### Scenario"
    )
    uploaded_file = st.sidebar.file_uploader("Load Scenario", type=['json'])
    if uploaded_file is not None:
        d = constants_from_uploaded_file(uploaded_file)

    st.sidebar.markdown("""
        <span style="color:red;font-size:small;">Please refresh your browser window before loading a scenario.</span> 
    """, unsafe_allow_html=True)

    author = st.sidebar.text_input(
        "Author Name", 
        value="Jane Doe" if uploaded_file is None else d.author
    )
    scenario = st.sidebar.text_input(
        "Scenario Name", 
        value="Scenario Name" if uploaded_file is None else d.scenario
    )

    if mode == Mode.EMPIRICAL:
        st.sidebar.markdown(
            "### Model Settings"
        )
        metric_options = [ForecastedMetric.DOUBLING_TIME, ForecastedMetric.RT]
        forecasted_metric = st.sidebar.radio(
            "Forecasted Metric",
            metric_options,
            index=metric_options.index(d.forecasted_metric),
        )
        method_options = [ForecastMethod.ETS, ForecastMethod.LOESS, ForecastMethod.SPLINE, ForecastMethod.LINEAR]
        forecast_method = st.sidebar.radio(
            "Forecast Method",
            method_options,
            index=method_options.index(d.forecast_method)
        )
    else:
        forecasted_metric = d.forecasted_metric
        forecast_method = d.forecast_method

    st.sidebar.markdown(
        "### Hospital Parameters"
    )
    if mode == Mode.PENN_MODEL:
        population = st.sidebar.number_input(
            "Regional Population",
            min_value=1,
            value=(d.population),
            step=1,
            format="%i",
        )
    else:
        population = d.population
    market_share = st.sidebar.number_input(
        "Hospital Market Share (%)",
        min_value=0.5,
        value=d.market_share * 100.,
    ) / 100.

    if mode == Mode.PENN_MODEL:
        # Take values from the inputs
        covid_census_value = st.sidebar.number_input(
            "Current COVID-19 Total Hospital Census",
            min_value=0,
            value=d.covid_census_value,
            step=1,
            format="%i",
        )
        covid_census_date = st.sidebar.date_input(
            "Current date (default is today)",
            value = d.covid_census_date,
        )

        st.sidebar.markdown(
            "### Spread and Contact Parameters"
        )
    
        first_hospitalized_date_known_default = False if uploaded_file is None else d.first_hospitalized_date_known
        if st.sidebar.checkbox(
            "I know the date of the first hospitalized case.", value=first_hospitalized_date_known_default
        ):
            st.sidebar.markdown("""First Hospitalized Date Must Be Before Current Date""")
            date_first_hospitalized = st.sidebar.date_input(
                "Date of first hospitalized case - Enter this date to have chime estimate the initial doubling time",
                value=d.date_first_hospitalized,
            )
            first_hospitalized_date_known = True
            doubling_time = None
        else:
            doubling_time = st.sidebar.number_input(
                "Doubling time in days (before social distancing)",
                min_value=0.5,
                value=d.doubling_time,
                step=0.25,
                format="%f",
            )
            first_hospitalized_date_known = False
            date_first_hospitalized = None

        mitigation_date = None
        relative_contact_rate = EPSILON
        social_distancing_is_implemented = st.sidebar.checkbox("Social distancing measures have been implemented.", value=d.social_distancing_is_implemented)
        if social_distancing_is_implemented:
            mitigation_date = st.sidebar.date_input(
                "Date of social distancing measures effect (may be delayed from implementation)",
                value=d.mitigation_date
            )
            relative_contact_rate = st.sidebar.number_input(
                "Social distancing (% reduction in social contact going forward)",
                min_value=0.0,
                max_value=100.0,
                value=d.relative_contact_rate * 100.,
                step=1.0,
            ) / 100.
    else:
        covid_census_value = d.covid_census_value
        covid_census_date = d.covid_census_date
        first_hospitalized_date_known = d.first_hospitalized_date_known
        date_first_hospitalized = d.date_first_hospitalized
        doubling_time = d.doubling_time
        social_distancing_is_implemented = d.social_distancing_is_implemented
        mitigation_date = d.mitigation_date
        relative_contact_rate = d.relative_contact_rate


    st.sidebar.markdown(
        "### Severity Parameters"
    )
    
    non_icu_rate = st.sidebar.number_input(
        "Non-ICU %(total infections)", 
        value=d.non_icu.rate * 100.,
        min_value=0.0000000001,
    ) / 100.
    icu_rate = st.sidebar.number_input(
        "ICU %(total infections)",
        min_value=0.0,
        value=d.icu.rate * 100.,
        step=0.05
    ) / 100.
    ventilators_rate = st.sidebar.number_input(
        "Ventilators %(total infections)", 
        value=d.ventilators.rate * 100.,
    ) / 100.
    infectious_days = st.sidebar.number_input(
        "Infectious Days",
        min_value=0,
        value=d.infectious_days,
        step=1,
        format="%i",
    )
    non_icu_days = st.sidebar.number_input(
        "Average Non-ICU Length of Stay (days)",
        min_value=0,
        value=d.non_icu.days,
        step=1,
        format="%i",
    )
    icu_days = st.sidebar.number_input(
        "Average Days in ICU",
        min_value=0,
        value=d.icu.days,
        step=1,
        format="%i",
    )
    ventilators_days = st.sidebar.number_input(
        "Average Days on Ventilator",
        min_value=0,
        value=d.ventilators.days,
        step=1,
        format="%i",
    )

    st.sidebar.markdown(
        "### COVID-19 Hospital Capacity"
    )
    beds_borrow_default = True if uploaded_file is None else d.beds_borrow
    beds_borrow_input = st.sidebar.checkbox("Allow borrowing beds between departments", value=beds_borrow_default)
    
    total_covid_beds = st.sidebar.number_input(
        "Total # of Beds for COVID-19 Patients",
        min_value=0,
        value=d.total_covid_beds,
        step=10,
        format="%i",
    )
    icu_covid_beds = st.sidebar.number_input(
        "Total # of ICU Beds for COVID-19 Patients",
        min_value=0,
        value=d.icu_covid_beds,
        step=5,
        format="%i",
    )
    covid_ventilators = st.sidebar.number_input(
        "Total # of Ventilators for COVID-19 Patients",
        min_value=0,
        value=d.covid_ventilators,
        step=5,
        format="%i",
    )

    parameters = Parameters(
        covid_census_value=covid_census_value,
        covid_census_date=covid_census_date,
        non_icu=Disposition(non_icu_rate, non_icu_days),
        total_covid_beds=total_covid_beds,
        icu_covid_beds=icu_covid_beds,
        covid_ventilators=covid_ventilators,
        icu=Disposition(icu_rate, icu_days),
        relative_contact_rate=relative_contact_rate,
        mitigation_date=mitigation_date,
        social_distancing_is_implemented=social_distancing_is_implemented,
        ventilators=Disposition(ventilators_rate, ventilators_days),
        date_first_hospitalized=date_first_hospitalized,
        doubling_time=doubling_time,
        infectious_days=infectious_days,
        market_share=market_share,
        population=population,
        author=author,
        scenario=scenario,
        first_hospitalized_date_known=first_hospitalized_date_known,
        current_date=covid_census_date,
        beds_borrow=beds_borrow_input,
        app_mode=mode,
        forecast_method=forecast_method,
        forecasted_metric=forecasted_metric,
    )
    if uploaded_file is not None:
        parameters.selected_states = d.selected_states
        parameters.selected_counties = d.selected_counties

    parameters = display_ppe_section(d, parameters)
    parameters = display_staffing_section(d, parameters)
    parameters = display_displayParameters_section(d, uploaded_file, parameters)

    actuals = display_actuals_section()
    return parameters, actuals, mode


def display_actuals_section():
    actuals = None
    # If you put this in a checkbox then 
    st.sidebar.markdown("### Actuals")
    st.sidebar.markdown(
        """<p>For instructions on how to format actual data please see the <a href="#working_with_actuals">Working with Actuals</a> section.
        Uploaded <b>actuals are for visualizations purposes only</b> and do not affect calculations.</p> """,
        unsafe_allow_html=True,
    )
    uploaded_actuals = st.sidebar.file_uploader("Load Actuals", type=['csv'])
    if uploaded_actuals:
        # st.sidebar.markdown(uploaded_actuals.read())
        actuals, error_message = parse_actuals(uploaded_actuals)
        if error_message:
            st.sidebar.markdown(error_message)
    return actuals


def display_ppe_section(d: Parameters, p: Parameters) -> Parameters:
    st.sidebar.markdown("### Personal Protection Equipment")
    st.sidebar.markdown("**Non-ICU**")
    # Non-critical care
    masks_n95 = st.sidebar.number_input(
        "Masks - N95/Patient/Day",
        min_value=0,
        value=d.masks_n95,
        step=1,
        format="%i",
    )
    p.masks_n95 = masks_n95

    masks_surgical = st.sidebar.number_input(
        "Masks - Surgical/Patient/Day",
        min_value=0,
        value=d.masks_surgical,
        step=1,
        format="%i",
    )
    p.masks_surgical = masks_surgical

    face_shield = st.sidebar.number_input(
        "Face Shields/Patient/Day",
        min_value=0,
        value=d.face_shield,
        step=1,
        format="%i",
    )
    p.face_shield = face_shield

    gloves = st.sidebar.number_input(
        "Gloves/Pair/Patient/Day",
        min_value=0,
        value=d.gloves,
        step=1,
        format="%i",
    )
    p.gloves = gloves

    gowns = st.sidebar.number_input(
        "Gowns/Patient/Day",
        min_value=0,
        value=d.gowns,
        step=1,
        format="%i",
    )
    p.gowns = gowns

    other_ppe = st.sidebar.number_input(
        "Other/Patient/Day",
        min_value=0,
        value=d.other_ppe,
        step=1,
        format="%i",
    )
    p.other_ppe = other_ppe

    # Critical Care
    st.sidebar.markdown("**ICU**")
    masks_n95_icu = st.sidebar.number_input(
        "Masks - N95/Patient/Day (ICU)",
        min_value=0,
        value=d.masks_n95_icu,
        step=1,
        format="%i",
    )
    p.masks_n95_icu = masks_n95_icu

    masks_surgical_icu = st.sidebar.number_input(
        "Masks - Surgical/Patient/Day (ICU)",
        min_value=0,
        value=d.masks_surgical_icu,
        step=1,
        format="%i",
    )
    p.masks_surgical_icu = masks_surgical_icu

    face_shield_icu = st.sidebar.number_input(
        "Face Shields/Patient/Day (ICU)",
        min_value=0,
        value=d.face_shield_icu,
        step=1,
        format="%i",
    )
    p.face_shield_icu = face_shield_icu

    gloves_icu = st.sidebar.number_input(
        "Gloves/Pair/Patient/Day (ICU)",
        min_value=0,
        value=d.gloves_icu,
        step=1,
        format="%i",
    )
    p.gloves_icu = gloves_icu

    gowns_icu = st.sidebar.number_input(
        "Gowns/Patient/Day (ICU)",
        min_value=0,
        value=d.gowns_icu,
        step=1,
        format="%i",
    )
    p.gowns_icu = gowns_icu

    other_ppe_icu = st.sidebar.number_input(
        "Other/Patient/Day (ICU)",
        min_value=0,
        value=d.other_ppe_icu,
        step=1,
        format="%i",
    )
    p.other_ppe_icu = other_ppe_icu
    return p

def display_staffing_section(d: Parameters, p: Parameters) -> Parameters:
    st.sidebar.markdown("### Staffing")
    
    # Shift Duration - Shared param between ICU and Non-ICU staff
    shift_duration = st.sidebar.number_input(
        "Shift Duration (hours)",
        min_value=8,
        max_value=24,
        value=d.shift_duration,
        step=2,
        format="%i",
    )
    p.shift_duration = shift_duration

    st.sidebar.markdown("**Non-ICU**")
    # Non-critical care
    nurses = st.sidebar.number_input(
        "Patients/Nurse",
        min_value=0,
        value=d.nurses,
        step=1,
        format="%i",
    )
    p.nurses = nurses

    physicians = st.sidebar.number_input(
        "Patients/Physician",
        min_value=0,
        value=d.physicians,
        step=1,
        format="%i",
    )
    p.physicians = physicians

    advanced_practice_providers = st.sidebar.number_input(
        "Patients/Advanced Practice Provider (APP)",
        min_value=0,
        value=d.advanced_practice_providers,
        step=1,
        format="%i",
    )
    p.advanced_practice_providers = advanced_practice_providers

    healthcare_assistants = st.sidebar.number_input(
        "Patients/Healthcare Assistant (PCT, CNA, etc)",
        min_value=0,
        value=d.healthcare_assistants,
        step=1,
        format="%i",
    )
    p.healthcare_assistants = healthcare_assistants

    other_staff = st.sidebar.number_input(
        "Patients/Other Staff",
        min_value=0,
        value=d.other_staff,
        step=1,
        format="%i",
    )
    p.other_staff = other_staff

    # Critical Care
    st.sidebar.markdown("**ICU**")
    nurses_icu = st.sidebar.number_input(
        "Patients/Nurse (ICU)",
        min_value=0,
        value=d.nurses_icu,
        step=1,
        format="%i",
    )
    p.nurses_icu = nurses_icu

    physicians_icu = st.sidebar.number_input(
        "Patients/Physician (ICU)",
        min_value=0,
        value=d.physicians_icu,
        step=1,
        format="%i",
    )
    p.physicians_icu = physicians_icu

    advanced_practice_providers_icu = st.sidebar.number_input(
        "Patients/Advanced Practice Provider (APP) (ICU)",
        min_value=0,
        value=d.advanced_practice_providers_icu,
        step=1,
        format="%i",
    )
    p.advanced_practice_providers_icu = advanced_practice_providers_icu

    healthcare_assistants_icu = st.sidebar.number_input(
        "Patients/Healthcare Assistant (PCT, CNA, etc) (ICU)",
        min_value=0,
        value=d.healthcare_assistants_icu,
        step=1,
        format="%i",
    )
    p.healthcare_assistants_icu = healthcare_assistants_icu

    other_staff_icu = st.sidebar.number_input(
        "Patients/Other Staff (ICU)",
        min_value=0,
        value=d.other_staff_icu,
        step=1,
        format="%i",
    )
    p.other_staff_icu = other_staff_icu
    return p

def display_displayParameters_section(d: Parameters, uploaded_file, p: Parameters) -> Parameters:
    st.sidebar.markdown(
        "### Display Parameters"
    )
    n_days = st.sidebar.number_input(
        "Number of days to project",
        min_value=7,
        value=d.n_days,
        step=1,
        format="%i",
    )
    p.n_days = n_days
    
    max_y_axis_set_default = False if uploaded_file is None else d.max_y_axis_set
    max_y_axis_set = st.sidebar.checkbox("Set the Y-axis on graphs to a static value", value=max_y_axis_set_default)
    max_y_axis = 500 if uploaded_file is None else d.max_y_axis
    if max_y_axis_set:
        max_y_axis = st.sidebar.number_input(
            "Y-axis static value", 
            value=max_y_axis, 
            format="%i", 
            step=25,
        )

    p.max_y_axis = max_y_axis
    p.max_y_axis_set = max_y_axis_set

    return p