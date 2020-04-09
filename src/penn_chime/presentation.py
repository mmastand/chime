"""effectful functions for streamlit io"""

import os
from typing import Optional
import datetime

import altair as alt
import numpy as np
import pandas as pd

from .constants import (
    CHANGE_DATE,
    DATE_FORMAT,
    DOCS_URL,
    FLOAT_INPUT_MIN,
    FLOAT_INPUT_STEP,
)

from .utils import dataframe_to_base64
from .parameters import Parameters, Disposition
from .models import SimSirModel as Model
from .hc_param_import_export import (
    constants_from_uploaded_file, 
    param_download_widget
)
from .hc_actuals import parse_actuals, actuals_download_widget

hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        </style>
        """


########
# Text #
########


def display_header(st, m, p):

    infected_population_warning_str = (
        """(Warning: The number of estimated infections is greater than the total regional population. Please verify the values entered in the sidebar.)"""
        if m.infected > p.population
        else ""
    )

    st.subheader("Information About This Tool")

    st.markdown(
        f"""
        This tool was developed by Health Catalyst to assist healthcare systems with their modeling and forecasting of COVID-19 infection 
        rates in their local catchment region, and the subsequent impact of those rates on care delivery capacity. We extend our deep 
        thanks to the [Predictive Healthcare team at Penn Medicine] (http://predictivehealthcare.pennmedicine.org/)  for their [COVID-19 
        Hospital Impact Model for Epidemics] (https://penn-chime.phl.io/), and making the code for their tool available to the opensource community. We leveraged the Penn 
        epidemiology models, and added new features in our tool such as the ability to run multiple scenarios, store those scenarios on 
        users' local desktops, then upload those scenarios again for later use. We also added additional features that reflect hospital 
        operations, such as the ability to understand capacity.
        We've done our best to test and validate this tool, balancing time-to-value with thorough test and validation. 
        * If you find a bug, please report it [here] (mailto:covidcapacitybugs@healthcatalyst.com).
        * If you have an enhancement request, please provide it [here] (mailto:covidcapacityenhancements@healthcatalyst.com).
        
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """<p>See <strong><a href="#application_guidance">Application Guidance</a></strong> section below for more information.</p>""",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <link rel="stylesheet" href="https://www1.pennmedicine.org/styles/shared/penn-medicine-header.css">
        <div class="penn-medicine-header__content">
            <a id="title" class="penn-medicine-header__title" style="font-size:24pt;color:#00aeff">COVID-19 Hospital Impact Model for Epidemics</a>
        </div> 
        <br>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """The estimated number of currently infected individuals is **{total_infections:.0f}**. This is based on current inputs for
    Hospitalizations (**{current_hosp}**), Hospitalization rate (**{hosp_rate:.0%}**), Region size (**{S}**),
    and Hospital market share (**{market_share:.0%}**).

{infected_population_warning_str}

An initial doubling time of **{doubling_time}** days and a recovery time of **{recovery_days}** days imply an $R_0$ of
 **{r_naught:.2f}** and daily growth rate of **{daily_growth:.2f}%**.

**Mitigation**: A **{relative_contact_rate:.0%}** reduction in social contact after the onset of the
outbreak **{impact_statement:s} {doubling_time_t:.1f}** days, implying an effective $R_t$ of **${r_t:.2f}$**
and daily growth rate of **{daily_growth_t:.2f}%**.
""".format(
            total_infections=m.infected,
            current_hosp=p.covid_census_value,
            hosp_rate=p.hospitalized.rate,
            S=p.population,
            market_share=p.market_share,
            recovery_days=p.infectious_days,
            r_naught=m.r_naught,
            doubling_time=p.doubling_time,
            relative_contact_rate=p.relative_contact_rate,
            r_t=m.r_t,
            doubling_time_t=abs(m.doubling_time_t),
            impact_statement=(
                "halves the infections every"
                if m.r_t < 1
                else "reduces the doubling time to"
            ),
            daily_growth=m.daily_growth_rate * 100.0,
            daily_growth_t=m.daily_growth_rate_t * 100.0,
            infected_population_warning_str=infected_population_warning_str,
        )
    )

    return None


# class Input:
#     """Helper to separate Streamlit input definition from creation/rendering"""

#     def __init__(self, st_obj, label, value, kwargs):
#         self.st_obj = st_obj
#         self.label = label
#         self.value = value
#         self.kwargs = kwargs

#     def __call__(self):
#         return self.st_obj(self.label, value=self.value, **self.kwargs)


# class NumberInput(Input):
#     def __init__(
#         self,
#         st_obj,
#         label,
#         min_value=None,
#         max_value=None,
#         value=None,
#         step=None,
#         format=None,
#         key=None,
#     ):
#         kwargs = dict(
#             min_value=min_value, max_value=max_value, step=step, format=format, key=key
#         )
#         super().__init__(st_obj.number_input, label, value, kwargs)


# class DateInput(Input):
#     def __init__(self, st_obj, label, value=None, key=None):
#         kwargs = dict(key=key)
#         super().__init__(st_obj.date_input, label, value, kwargs)


# class PercentInput(NumberInput):
#     def __init__(
#         self,
#         st_obj,
#         label,
#         min_value=0.0,
#         max_value=100.0,
#         value=None,
#         step=FLOAT_INPUT_STEP,
#         format="%f",
#         key=None,
#     ):
#         super().__init__(
#             st_obj, label, min_value, max_value, value * 100.0, step, format, key
#         )

#     def __call__(self):
#         return super().__call__() / 100.0


# class CheckboxInput(Input):
#     def __init__(self, st_obj, label, value=None, key=None):
#         kwargs = dict(key=key)
#         super().__init__(st_obj.checkbox, label, value, kwargs)

# class TextInput(Input):
#     def __init__(self, st_obj, label, value=None, key=None):
#         kwargs = dict(key=key)
#         super().__init__(st_obj.text_input, label, value, kwargs)


def display_sidebar(st, d: Parameters) -> Parameters:
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

    st_obj = st.sidebar
    st.sidebar.markdown(
        "### Scenario"
    )
    uploaded_file = st.sidebar.file_uploader("Load Scenario", type=['json'])
    if uploaded_file is not None:
        d = constants_from_uploaded_file(uploaded_file)

    # st.sidebar.markdown("""
    #     <span style="color:red;font-size:small;">Known Limitation: You must refresh your browser window before loading scenario, otherwise the projections will not be updated.</span> 
    # """, unsafe_allow_html=True)
    st.sidebar.markdown("""
        <span style="color:red;font-size:small;">Please refresh your browser window before loading a scenario.</span> 
    """, unsafe_allow_html=True)

    
    
    # social_distancing_start_date_input = DateInput(
    #     st_obj, "Date when Social Distancing Protocols Started (Default is today)", value=d.social_distancing_start_date,
    # )
    
    
    # max_y_axis_set_input = CheckboxInput(
    #     st_obj, 
    #     "Set the Y-axis on graphs to a static value",
    # )
    # max_y_axis_input = NumberInput(
    #     st_obj, 
    #     "Y-axis static value", 
    #     value=500, 
    #     format="%i", 
    #     step=25,
    # )

    # Build in desired order

    author = st.sidebar.text_input(
        "Author Name", 
        value="Jane Doe" if uploaded_file is None else d.author
    )
    scenario = st.sidebar.text_input(
        "Scenario Name", 
        value="Scenario Name" if uploaded_file is None else d.scenario
    )

    st.sidebar.markdown(
        "### Hospital Parameters"
    )
    population = st.sidebar.number_input(
        "Regional Population",
        min_value=1,
        value=(d.population),
        step=1,
        format="%i",
    )
    market_share = st.sidebar.number_input(
        "Hospital Market Share (%)",
        min_value=0.5,
        value=d.market_share * 100.,
    ) / 100.
    covid_census_value = st.sidebar.number_input(
        "Current COVID-19 Total Hospital Census",
        min_value=0,
        value=d.covid_census_value,
        step=1,
        format="%i",
    )
    covid_census_date = st.sidebar.date_input(
        "Current Date (default is today)",
        value = d.covid_census_date,
    )

    st.sidebar.markdown(
        "### Spread and Contact Parameters"
    )

    
    # parameter.first_hospitalized_date_known = st.sidebar.checkbox("Set the Y-axis on graphs to a static value", value=max_y_axis_set_default)
    
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
            "Doubling time in days (up to today)",
            min_value=0.5,
            value=d.doubling_time,
            step=0.25,
            format="%f",
        )
        first_hospitalized_date_known = False
        date_first_hospitalized = None

    relative_contact_rate = st.sidebar.number_input(
        "Social distancing (% reduction in social contact going forward)",
        min_value=0.0,
        max_value=100.0,
        value=d.relative_contact_rate * 100.,
        step=1.0,
    ) / 100.

    # social_distancing_start_date = social_distancing_start_date_input()
    social_distancing_start_date = (datetime.datetime.utcnow() - datetime.timedelta(hours=6)).date()

    st.sidebar.markdown(
        "### Severity Parameters"
    )
    
    hospitalized_rate = st.sidebar.number_input(
        "Hospitalization %(total infections)", 
        value=d.hospitalized.rate * 100.,
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
    hospitalized_days = st.sidebar.number_input(
        "Average Hospital Length of Stay (days)",
        min_value=0,
        value=d.hospitalized.days,
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
        hospitalized=Disposition(hospitalized_rate, hospitalized_days),
        total_covid_beds=total_covid_beds,
        icu_covid_beds=icu_covid_beds,
        covid_ventilators=covid_ventilators,
        icu=Disposition(icu_rate, icu_days),
        relative_contact_rate=relative_contact_rate,
        ventilators=Disposition(ventilators_rate, ventilators_days),
        social_distancing_start_date=social_distancing_start_date,
        date_first_hospitalized=date_first_hospitalized,
        doubling_time=doubling_time,
        infectious_days=infectious_days,
        market_share=market_share,
        population=population,
        author=author,
        scenario=scenario,
        first_hospitalized_date_known=first_hospitalized_date_known,
        current_date=covid_census_date,
    )

    parameters = display_ppe_section(st, d, parameters)
    parameters = display_staffing_section(st, d, parameters)
    parameters = display_displayParameters_section(st, d, uploaded_file, parameters)

    actuals = display_actuals_section(st)
    param_download_widget(
        st,
        parameters,
    )
    return parameters, actuals


def display_actuals_section(st):
    actuals = None
    # If you put this in a checkbox then 
    st.sidebar.markdown("### Actuals")
    st.sidebar.markdown(
        """<p>For instructions on how to format actual data please see the <a href="#working_with_actuals">Working with Actuals</a> section.</p>""",
        unsafe_allow_html=True,
    )
    uploaded_actuals = st.sidebar.file_uploader("Load Actuals", type=['csv'])
    if uploaded_actuals:
        # st.sidebar.markdown(uploaded_actuals.read())
        actuals, error_message = parse_actuals(uploaded_actuals)
        if error_message:
            st.sidebar.markdown(error_message)
    return actuals


def display_ppe_section(st, d: Parameters, p: Parameters) -> Parameters:
    st.sidebar.markdown("### Personal Protection Equipment")
    st.sidebar.markdown("**Non-Critical Care**")
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
    st.sidebar.markdown("**Critical Care**")
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

def display_staffing_section(st, d: Parameters, p: Parameters) -> Parameters:
    st.sidebar.markdown("### Staffing")
    
    # Shift Duration - Shared param between ICU and Non-ICU staff
    shift_duration = st.sidebar.number_input(
        "Shift Duration",
        min_value=8,
        max_value=12,
        value=d.shift_duration,
        step=2,
        format="%i",
    )
    p.shift_duration = shift_duration

    st.sidebar.markdown("**Non-Critical Care**")
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


    # Critical Care
    st.sidebar.markdown("**Critical Care**")
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

    return p

def display_displayParameters_section(st, d: Parameters, uploaded_file, p: Parameters) -> Parameters:
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

def display_more_info(
    st, model: Model, parameters: Parameters, defaults: Parameters, notes: str = "",
):
    """a lot of streamlit writing to screen."""
    st.subheader(
        "[Discrete-time SIR modeling](https://mathworld.wolfram.com/SIRModel.html) of infections/recovery"
    )
    st.markdown(
        """The model consists of individuals who are either _Susceptible_ ($S$), _Infected_ ($I$), or _Recovered_ ($R$).

The epidemic proceeds via a growth and decline process. This is the core model of infectious disease spread and has been in use in epidemiology for many years."""
    )
    st.markdown("""The dynamics are given by the following 3 equations.""")

    st.latex("S_{t+1} = (-\\beta S_t I_t) + S_t")
    st.latex("I_{t+1} = (\\beta S_t I_t - \\gamma I_t) + I_t")
    st.latex("R_{t+1} = (\\gamma I_t) + R_t")

    st.markdown(
        """To project the expected impact to Penn Medicine, we estimate the terms of the model.

To do this, we use a combination of estimates from other locations, informed estimates based on logical reasoning, and best guesses from the American Hospital Association.


### Parameters

The model's parameters, $\\beta$ and $\\gamma$, determine the virulence of the epidemic.

$$\\beta$$ can be interpreted as the _effective contact rate_:
"""
    )
    st.latex("\\beta = \\tau \\times c")

    st.markdown(
        """which is the transmissibility ($\\tau$) multiplied by the average number of people exposed ($$c$$).  The transmissibility is the basic virulence of the pathogen.  The number of people exposed $c$ is the parameter that can be changed through social distancing.


$\\gamma$ is the inverse of the mean recovery time, in days.  I.e.: if $\\gamma = 1/{recovery_days}$, then the average infection will clear in {recovery_days} days.

An important descriptive parameter is the _basic reproduction number_, or $R_0$.  This represents the average number of people who will be infected by any given infected person.  When $R_0$ is greater than 1, it means that a disease will grow.  Higher $R_0$'s imply more rapid growth.  It is defined as """.format(
            recovery_days=int(parameters.infectious_days)
        )
    )
    st.latex("R_0 = \\beta /\\gamma")

    st.markdown(
        """

$R_0$ gets bigger when

- there are more contacts between people
- when the pathogen is more virulent
- when people have the pathogen for longer periods of time

A doubling time of {doubling_time} days and a recovery time of {recovery_days} days imply an $R_0$ of {r_naught:.2f}.

#### Effect of social distancing

After the beginning of the outbreak, actions to reduce social contact will lower the parameter $c$.  If this happens at
time $t$, then the number of people infected by any given infected person is $R_t$, which will be lower than $R_0$.

A {relative_contact_rate:.0%} reduction in social contact would increase the time it takes for the outbreak to double,
to {doubling_time_t:.2f} days from {doubling_time:.2f} days, with a $R_t$ of {r_t:.2f}.

#### Using the model

We need to express the two parameters $\\beta$ and $\\gamma$ in terms of quantities we can estimate.

- $\\gamma$:  the CDC is recommending 14 days of self-quarantine, we'll use $\\gamma = 1/{recovery_days}$.
- To estimate $$\\beta$$ directly, we'd need to know transmissibility and social contact rates.  since we don't know these things, we can extract it from known _doubling times_.  The AHA says to expect a doubling time $T_d$ of 7-10 days. That means an early-phase rate of growth can be computed by using the doubling time formula:
""".format(
            doubling_time=parameters.doubling_time,
            recovery_days=parameters.infectious_days,
            r_naught=model.r_naught,
            relative_contact_rate=parameters.relative_contact_rate,
            doubling_time_t=model.doubling_time_t,
            r_t=model.r_t,
        )
    )
    st.latex("g = 2^{1/T_d} - 1")

    st.markdown(
        """
- Since the rate of new infections in the SIR model is $g = \\beta S - \\gamma$, and we've already computed $\\gamma$, $\\beta$ becomes a function of the initial population size of susceptible individuals.
$$\\beta = (g + \\gamma)$$.


### Initial Conditions

- {notes} \n
""".format(
            notes=notes
        )
    )
    return None


def write_definitions(st):
    st.markdown("""<a name="application_guidance"></a>""", unsafe_allow_html=True)
    st.header("Application Guidance")
    st.subheader("Working with Projected Data")
    st.markdown("""
    This tool has the ability to load and save parameters, as well as save parameters and calculations. Enable
    these features by changing the *Author Name* and *Scenario Name* to values of your choosing. Rather than create the parameter file
    from scratch we highly recommend using the "Save Parameters" button to create a parameter file which can then be edited by hand
    if desired. Please note however that it is easy to inadvertently produce an invalid JSON file when editing by hand. If you wish
    to update a set of existing parameters we recommend loading in the parameters, editing them in the UI, and re-exporting a new
    version of the parameters.
    
    **Saving Parameters:** At the bottom of the left sidebar, a download link will appear to save your 
    parameters as a file. Click to save the file. This file is .json and can be opened in a text editor.
    
    **Loading Parameters:** At the top of the left sidebar, browse for a parameter file (in the same 
    format as the exported parameters) or drag and drop. Parameter values will update.
    
    **Saving Calculations**: At the bottom of the main page, a link will appear to save all model 
    parameters and calculations as a .csv file. Click the link to save the file.
    """)

    st.markdown(
        """**For more details on input selection, please refer here: [User Documentation](https://code-for-philly.gitbook.io/chime/what-is-chime/parameters#guidance-on-selecting-inputs)**"""
    )
    st.markdown("""<a name="working_with_actuals"></a>""", unsafe_allow_html=True)
    st.subheader("Working with Actuals")
    st.markdown("""
    Using the parameters in the sidebar it is possible to configure theoretical projections that are driven by the 
    SIR model. However you may also upload actual data which will be displayed along with the projections in the 
    appropriate chart above. To upload actual data please use the file upload widget at the bottom of the sidebar.
    Uploaded files must be in the comma-separated-value (CSV) format. Below is a list of columns that you may include 
    in the uploaded CSV file along with a description of each column. Please note that column names are **case sensitive**.

    #### Required Columns
    `date`: The date corresponding to the measurements below.

    #### Optional Columns
    One or more of the following columns must also be present:

    `total_admissions_actual`: The total number of COVID-19 patients admitted on `date`. 

    `icu_admissions_actual`: The number of COVID-19 patients who entered the ICU on `date`.

    `intubated_actual`: The number of COVID-19 patients who were intubated on `date`. 

    `total_census_actual`: The total hospital COVID-19 census on `date`.

    `icu_census_actual`: The ICU COVID-19 census on `date`.

    `ventilators_in_use_actual`: The number of ventilators in use for COVID-19 patients on `date`.

    `cumulative_regional_infections`: The total number of infections in your region or catchment area on `date`. 
    **This number must be cumulative** rather than a count of currently infected people. A non-cumulative version
    of this column is generated before it is displayed in the SIR chart above, named `daily_regional_infections`.

    """)
    # st.markdown("""
    # Using the parameters in the sidebar it is possible to configure theoretical projections that are driven by the 
    # SIR model. However it is also important to be able compare those theoretical projections to actual data gathered 
    # from your hospital or region. Using the file upload widget at the bottom of the sidebar you may upload actual data 
    # which will be displayed along with the projections in the appropriate chart above. Uploaded files must be in the 
    # comma-separated-value (CSV) format. The supported columns and data types are as follows. Please note that column 
    # names are **case sensitive**.

    # #### Required Columns
    # | Column       | Data Type        | Description |
    # |--------------|------------------|-------------|
    # | `date`       | Date or Datetime | The date corresponding to the measurements below. |
    # `date`: The date corresponding to the measurements below.

    # #### Optional Columns
    # One or more of the following columns must be present.

    # | Column                            | Data Type         | Description  |
    # | --------------------------------- |:-----------------:| -----:|
    # | `total_admissions_actual`         | integer or float  | The total number of COVID-19 patients admitted on `date`.      |
    # | `icu_admissions_actual`           | integer or float  | The number of COVID-19 patients who entered the ICU on `date`. |
    # | `intubated_actual`                | integer or float  | The number of COVID-19 patients who were intubated on `date`.  |
    # | `total_census_actual`             | integer or float  | The total hospital COVID-19 census on `date`. |
    # | `icu_census_actual`               | integer or float  | The ICU COVID-19 census on `date`. |
    # | `ventilators_in_use_actual`       | integer or float  | The number of ventilators in use for COVID-19 patients on `date`.|
    # | `cumulative_regional_infections`  | integer or float  | The total number of infections in your region or catchment area on `date`. **This number must be cumulative** rather than a count of currently infected people. |

    # | Column                            | Description  |
    # | --------------------------------- | -----|
    # | `total_admissions_actual`         | The total number of COVID-19 patients admitted on `date`.      |
    # | `icu_admissions_actual`           | The number of COVID-19 patients who entered the ICU on `date`. |
    # | `intubated_actual`                | The number of COVID-19 patients who were intubated on `date`.  |
    # | `total_census_actual`             | The total hospital COVID-19 census on `date`. |
    # | `icu_census_actual`               | The ICU COVID-19 census on `date`. |
    # | `ventilators_in_use_actual`       | The number of ventilators in use for COVID-19 patients on `date`.|
    # | `cumulative_regional_infections`  | The cumulative number of infections in your region or catchment area on `date`. **This number must be cumulative** (rather than a count of currently infected people) so that it may be used to calculate doubling time. |

    
    # `total_admissions_actual`: The total number of COVID-19 patients admitted on `date`. 

    # `icu_admissions_actual`: The number of COVID-19 patients who entered the ICU on `date`.

    # `intubated_actual`: The number of COVID-19 patients who were intubated on `date`. 

    # `total_census_actual`: The total hospital COVID-19 census on `date`.

    # `icu_census_actual`: The ICU COVID-19 census on `date`.

    # `ventilators_in_use_actual`: The number of ventilators in use for COVID-19 patients on `date`.

    # `cumulative_regional_infections`: The total number of infections in your region or catchment area on `date`. **This number must be cumulative** rather than a count of currently infected people.

    # """)
    actuals_download_widget(st)

    


def write_footer(st):
    st.header("References & Acknowledgements")
    st.markdown(
        """* This application is based on the work that is developed and made freely available (under MIT license) by Penn Medicine (https://github.com/CodeForPhilly/chime). 
        """
    )
    
    st.markdown("""<a name="release_notes"></a>""", unsafe_allow_html=True)
    st.subheader("Features and Enhancements History")
    if st.checkbox("Show Features and Enhancements History"):
        st.markdown("""  
            **V: 1.5.0 (Thursday, April 09, 2020)** 
            * Added staffing functionality
            * Changed exported column name to "VentilatorsAdmissions"
            * Moved capacity parameters to lower on sidebar
            * Fixed a bug where first row contained NaNs in full downloaded data
            
            **V: 1.4.0 (Wednesday, April 08, 2020)** 
            * Added PPE/patient/day functionality
            * Changed minimum days to project to 7

            **V: 1.3.7 (Tuesday, April 07, 2020)** 
            * Fixed estimated start day bug when "Number of Days to Project" was low
            * Fixed total census to be a sum of ICU and non-ICU

            **V: 1.3.5 (Monday, April 06, 2020)** 

            * Added **support for providing historical data** and incorporating it in the hospital admission/census/COVID-19 capacity charts/projections
    
            **V: 1.2.11 (Thursday, April 02, 2020):** 
            
            * Incorporated changes made by **Penn Med to ensure replicability**
            * Created parameter categories in the left menu for better organization
            * Added support for specifying the date of the first hospitalized case            

            **V: 1.1.1 (Friday, March 27, 2020):** 
            
            * Added support for **loading and saving capacity planning scenarios** 
            * Added support for **understanding capacity** as well as demand by specifying Numbers of Total Beds, ICU Beds, and Ventilators for COVID-19 Patients
            * Added support for exporting full dataset and capacity scenario as a csv file
    
        """)
    st.markdown("© 2020, Health Catalyst Inc.")


def display_download_link(st, filename: str, df: pd.DataFrame):
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
    bed_table.hospitalized[0] = parameters.total_covid_beds - parameters.icu_covid_beds - 1
    bed_table.icu[0] = parameters.icu_covid_beds - 1
    bed_table.ventilators[0] = parameters.covid_ventilators - 1
    bed_table = bed_table.dropna()
    bed_table = non_date_columns_to_int(bed_table)
    bed_table.rename(parameters.labels)

    # taken from raw sir table function:
    projection_area = model.raw_df
    infect_table = (projection_area.iloc[::1, :]).apply(np.floor)
    infect_table.index = range(infect_table.shape[0])
    infect_table["day"] = infect_table.index
    infect_table = non_date_columns_to_int(infect_table)

    # Build full dataset
    df = admits_table.copy()
    df = df.rename(columns = {
        "date": "Date",
        "total": "TotalAdmissions", 
        "icu": "ICUAdmissions", 
        "ventilators": "VentilatorsAdmissions"}, )
    
    df["TotalCensus"] = census_table["total"]
    df["ICUCensus"] = census_table["icu"]
    df["VentilatorsCensus"] = census_table["ventilators"]

    df["TotalBeds"] = bed_table["total"]
    df["ICUBeds"] = bed_table["icu"]
    df["Ventilators"] = bed_table["ventilators"]

    ppe_df.loc[0, :] = 0
    df["MasksN95Total"] = ppe_df.masks_n95_total
    df["MasksSurgicalTotal"] = ppe_df.masks_surgical_total
    df["FaceShieldsTotal"] = ppe_df.face_shield_total
    df["GlovesTotal"] = ppe_df.gloves_total
    df["GownsTotal"] = ppe_df.gowns_total
    df["OtherPPETotal"] = ppe_df.other_ppe_total
    df["MasksN95ICU"] = ppe_df.masks_n95_icu
    df["MasksSurgicalICU"] = ppe_df.masks_surgical_icu
    df["FaceShieldsICU"] = ppe_df.face_shield_icu
    df["GlovesICU"] = ppe_df.gloves_icu
    df["GownsICU"] = ppe_df.gowns_icu
    df["OtherPPEICU"] = ppe_df.other_ppe_icu
    df["MasksN95Hosp"] = ppe_df.masks_n95_hosp
    df["MasksSurgicalHosp"] = ppe_df.masks_surgical_hosp
    df["FaceShieldsHosp"] = ppe_df.face_shield_hosp
    df["GlovesHosp"] = ppe_df.gloves_hosp
    df["GownsHosp"] = ppe_df.gowns_hosp
    df["OtherPPEHosp"] = ppe_df.other_ppe_hosp
    
    # Staffing
    staffing_df.loc[0, :] = 0
    df["NursesHosp"] = staffing_df.nurses_hosp
    df["PhysiciansHosp"] = staffing_df.physicians_hosp
    df["AdvancedPraticeProvidersHosp"] = staffing_df.advanced_practice_providers_hosp
    df["HealthcareAssistantsHosp"] = staffing_df.healthcare_assistants_hosp

    df["NursesICU"] = staffing_df.nurses_icu
    df["PhysiciansICU"] = staffing_df.physicians_icu
    df["AdvancedPraticeProvidersICU"] = staffing_df.advanced_practice_providers_icu
    df["HealthcareAssistantsICU"] = staffing_df.healthcare_assistants_icu
    
    df["NursesTotal"] = staffing_df.nurses_total
    df["PhysiciansTotal"] = staffing_df.physicians_total
    df["AdvancedPraticeProvidersTotal"] = staffing_df.advanced_practice_providers_total
    df["HealthcareAssistantsTotal"] = staffing_df.healthcare_assistants_total

    df["Susceptible"] = infect_table["susceptible"]
    df["Infections"] = infect_table["infected"]
    df["Recovered"] = infect_table["recovered"]

    df["Author"] = parameters.author
    df["Scenario"] = parameters.scenario
    df["DateGenerated"] = (datetime.datetime.utcnow() - datetime.timedelta(hours=6)).isoformat()

    df["CovidCensusValue"] = parameters.covid_census_value
    df["CovidCensusDate"] = parameters.covid_census_date
    df["DoublingTimeBeforeSocialDistancing"] = parameters.doubling_time
    df["SocialDistancingPercentReduction"] = parameters.relative_contact_rate
    df["SocialDistancingStartDate"] = parameters.social_distancing_start_date
    df["DateFirstHospitalized"] = parameters.date_first_hospitalized
    df["InfectiousDays"] = parameters.infectious_days

    df["HospitalizationPercentage"] = parameters.hospitalized.rate
    df["ICUPercentage"] = parameters.icu.rate
    df["VentilatorsPercentage"] = parameters.ventilators.rate

    df["HospitalLengthOfStay"] = parameters.hospitalized.days
    df["ICULengthOfStay"] = parameters.icu.days
    df["VentLengthOfStay"] = parameters.ventilators.days

    df["HospitalMarketShare"] = parameters.market_share
    df["RegionalPopulation"] = parameters.population
    
    df["TotalNumberOfBedsForCOVIDPatients"] = parameters.total_covid_beds
    df["TotalNumberOfICUBedsFoCOVIDPatients"] = parameters.icu_covid_beds
    df["TotalNumberOfVentsFoCOVIDPatients"] = parameters.covid_ventilators
    
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
    
    # Reorder columns
    df = df[[
        "Author", 
        "Scenario", 
        "DateGenerated",

        "CovidCensusValue",
        "CovidCensusDate",
        "DoublingTimeBeforeSocialDistancing",
        "SocialDistancingPercentReduction",
        "SocialDistancingStartDate",
        "DateFirstHospitalized",
        "InfectiousDays",
        "HospitalizationPercentage",
        "ICUPercentage",
        "VentilatorsPercentage",

        "HospitalLengthOfStay",
        "ICULengthOfStay",
        "VentLengthOfStay",

        "HospitalMarketShare",
        "RegionalPopulation",
        # "CurrentlyKnownRegionalInfections",
        
        "TotalNumberOfBedsForCOVIDPatients",
        "TotalNumberOfICUBedsFoCOVIDPatients",
        "TotalNumberOfVentsFoCOVIDPatients",
        # "TotalNumberOfBeds",
        # "TotalNumberOfICUBeds",
        # "TotalNumberOfVents",

        "MasksN95Param",
        "MasksSurgicalParam",
        "FaceShieldsParam",
        "GlovesParam",
        "GownsParam",
        "OtherPPEParam",
        "MasksN95ICUParam",
        "MasksSurgicalICUParam",
        "FaceShieldsICUParam",
        "GlovesICUParam",
        "GownsICUParam",
        "OtherPPEICUParam",

        "PatientsPerNurses",
        "PatientsPerPhysicians",
        "PatientsPerAdvancedPraticeProviders",
        "PatientsPerHealthcareAssistants",
        "PatientsPerNursesICU",
        "PatientsPerPhysiciansICU",
        "PatientsPerAdvancedPraticeProvidersICU",
        "PatientsPerHealthcareAssistantsICU",
        "ShiftDuration",

        "Date",
        "TotalAdmissions", 
        "ICUAdmissions", 
        "VentilatorsAdmissions",

        "TotalCensus",
        "ICUCensus",
        "VentilatorsCensus",
        
        "TotalBeds",
        "ICUBeds",
        "Ventilators", 

        "Susceptible",
        "Infections",
        "Recovered",

        "MasksN95Total",
        "MasksN95Hosp",
        "MasksN95ICU",
        "MasksSurgicalTotal",
        "MasksSurgicalHosp",
        "MasksSurgicalICU",
        "FaceShieldsTotal",
        "FaceShieldsHosp",
        "FaceShieldsICU",
        "GlovesTotal",
        "GlovesHosp",
        "GlovesICU",
        "GownsTotal",
        "GownsHosp",
        "GownsICU",
        "OtherPPETotal",
        "OtherPPEHosp",
        "OtherPPEICU",

        "NursesTotal",
        "NursesHosp",
        "NursesICU",
        "PhysiciansTotal",
        "PhysiciansHosp",
        "PhysiciansICU",
        "AdvancedPraticeProvidersTotal",
        "AdvancedPraticeProvidersHosp",
        "AdvancedPraticeProvidersICU",
        "HealthcareAssistantsTotal",
        "HealthcareAssistantsHosp",
        "HealthcareAssistantsICU",
    ]]
    return(df)
