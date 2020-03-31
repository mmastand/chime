"""effectful functions for streamlit io"""

import os
from typing import Optional
from datetime import datetime

import altair as alt  # type: ignore
import numpy as np  # type: ignore
import pandas as pd  # type: ignore

from .defaults import Constants, RateLos
from .utils import add_date_column, dataframe_to_base64
from .parameters import Parameters
from .hc_param_import_export import (
    constants_from_uploaded_file,
    param_download_widget,
)
from streamlit.ScriptRunner import RerunException

DATE_FORMAT = "%b, %d"  # see https://strftime.org


hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        </style>
        """


########
# Text #
########


def display_header(st, m, p):

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
        """
        The estimated number of currently infected individuals is **{total_infections:.0f}**. This is based on current inputs for
    Hospitalizations (**{current_hosp}**), Hospitalization rate (**{hosp_rate:.1%}**), Region size (**{S}**),
    and Hospital market share (**{market_share:.0%}**).

An initial doubling time of **{doubling_time}** days and a recovery time of **{recovery_days}** days imply an $R_0$ of
**{r_naught:.2f}**.

**Mitigation**: A **{relative_contact_rate:.0%}** reduction in social contact after the onset of the
outbreak **{impact_statement:s} {doubling_time_t:.1f}** days, implying an effective $R_t$ of **${r_t:.2f}$**.
""".format(
            total_infections=m.infected,
            current_hosp=p.current_hospitalized,
            hosp_rate=p.hospitalized.rate,
            S=p.susceptible,
            market_share=p.market_share,
            recovery_days=p.recovery_days,
            r_naught=m.r_naught,
            doubling_time=p.doubling_time,
            relative_contact_rate=p.relative_contact_rate,
            r_t=m.r_t,
            doubling_time_t=abs(m.doubling_time_t),
            impact_statement=("halves the infections every" if m.r_t < 1 else "reduces the doubling time to")
        )
    )

    return None

def display_how_to_use(st):
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
        
        See **Application Guidance** section below for more information 
        """,
        unsafe_allow_html=True,)

def display_sidebar(st, d: Constants) -> Parameters:
    # Initialize variables
    # these functions create input elements and bind the values they are set to
    # to the variables they are set equal to
    # it's kindof like ember or angular if you are familiar with those
    
    BUILD_TIME = os.environ['BUILD_TIME'] # == "`date`"
    VERSION_NUMBER = os.environ['VERSION_NUMBER']
    st.sidebar.markdown(
        f"""V: **{VERSION_NUMBER}** (**{BUILD_TIME}**)""",
        unsafe_allow_html=True,)
    
    st.sidebar.subheader("Scenario")
    uploaded_file = st.sidebar.file_uploader("Load Parameters", type=['json'])
    if uploaded_file is not None:
        d, raw_imported = constants_from_uploaded_file(uploaded_file)

    st.sidebar.markdown("""
        <span style="color:red;font-size:small;">Known Limitation: You must refresh your browser window before loading parameters, otherwise the projections will not be updated.</span> 
    """, unsafe_allow_html=True)

    author = st.sidebar.text_input("Author Name", 
        value="Jane Doe" if uploaded_file is None else raw_imported["Author"])
    
    scenario = st.sidebar.text_input("Scenario Name", 
        value="COVID Model" if uploaded_file is None else raw_imported["Scenario"])
    
    st.sidebar.subheader("Hospital Parameters")
    susceptible = st.sidebar.number_input(
        "Regional Population",
        min_value=1,
        value=d.region.susceptible,
        step=100000,
        format="%i",
    )

    market_share = (
        st.sidebar.number_input(
            "Hospital Market Share (%)",
            min_value=0.001,
            max_value=100.0,
            value=d.market_share * 100,
            step=1.0,
            format="%f",
        )
        / 100.0
    )

    current_hospitalized = st.sidebar.number_input(
        "COVID-19 Total Hospital Census",
        min_value=0,
        value=d.current_hospitalized,
        step=1,
        format="%i",
    )

    census_date = st.sidebar.date_input(
        "COVID-19 Total Hospital Census Date",
        value = d.census_date,
    )
    
    st.sidebar.subheader("Hospital Capacity")
    total_non_covid_beds = st.sidebar.number_input(
        "Total # of Beds for COVID Patients",
    #    min_value=0,
       value=d.total_non_covid_beds,
    #    step=10,
       format="%i",
    )


    total_non_covid_icu_beds = st.sidebar.number_input(
        "Total # of ICU Beds for COVID Patients",
    #    min_value=0,
       value=d.total_non_covid_icu_beds,
    #    step=10,
       format="%i",
    )
    
    total_non_covid_vents = st.sidebar.number_input(
        "Total # of Ventilators for COVID Patients",
    #    min_value=0,
       value=d.total_non_covid_vents,
    #    step=10,
       format="%i",
    )

    st.sidebar.subheader("Spread and Contact Parameters")
    doubling_time = st.sidebar.number_input(
        "Doubling time before social distancing (days)",
        min_value=0.0,
        value=d.doubling_time,
        step=0.1,
        format="%.2f",
    )

    relative_contact_rate = (
        st.sidebar.number_input(
            "Social distancing (% reduction in social contact)",
            min_value=0,
            max_value=100,
            value=int(d.relative_contact_rate * 100),
            step=5,
            format="%i",
        )
        / 100.0
    )
    
    st.sidebar.subheader("Severity Parameters")

    hospitalized_rate = (
        st.sidebar.number_input(
            "Hospitalization %(total infections)",
            min_value=0.001,
            max_value=100.0,
            value=d.hospitalized.rate * 100,
            step=1.0,
            format="%f",
        )
        / 100.0
    )
    icu_rate = (
        st.sidebar.number_input(
            "ICU %(total infections)",
            min_value=0.0,
            max_value=100.0,
            value=d.icu.rate * 100,
            step=1.0,
            format="%f",
        )
        / 100.0
    )
    ventilators_rate = (
        st.sidebar.number_input(
            "Ventilators %(total infections)",
            min_value=0.0,
            max_value=100.0,
            value=d.ventilators.rate * 100,
            step=1.0,
            format="%f",
        )
        / 100.0
    )

    hospitalized_los = st.sidebar.number_input(
        "Hospital Length of Stay",
        min_value=0,
        value=d.hospitalized.length_of_stay,
        step=1,
        format="%i",
    )
    icu_los = st.sidebar.number_input(
        "ICU Length of Stay",
        min_value=0,
        value=d.icu.length_of_stay,
        step=1,
        format="%i",
    )
    ventilators_los = st.sidebar.number_input(
        "Vent Length of Stay",
        min_value=0,
        value=d.ventilators.length_of_stay,
        step=1,
        format="%i",
    )
    
    st.sidebar.subheader("Display Parameters")
    
    n_days = st.sidebar.number_input(
        "Number of days to project",
        min_value=30,
        max_value=1000,
        value=d.n_days,
        step=10,
        format="%i",
    )

    as_date_default = False if uploaded_file is None else raw_imported["PresentResultAsDates"]
    as_date = st.sidebar.checkbox(label="Present result as dates instead of days", value=as_date_default)
    
    max_y_axis_set_default = False if uploaded_file is None else raw_imported["MaxYAxisSet"]
    max_y_axis_set = st.sidebar.checkbox("Set the Y-axis on graphs to a static value", value=max_y_axis_set_default)
    max_y_axis = 500 if uploaded_file is None else raw_imported["MaxYAxis"]
    if max_y_axis_set:
        max_y_axis = st.sidebar.number_input(
            "Y-axis static value", 
            value=max_y_axis, 
            format="%i", 
            step=25,
        )

    parameters = Parameters(
        as_date=as_date,
        current_hospitalized=current_hospitalized,
        doubling_time=doubling_time,
        market_share=market_share,
        max_y_axis=max_y_axis,
        max_y_axis_set=max_y_axis_set,
        n_days=n_days,
        relative_contact_rate=relative_contact_rate,
        susceptible=susceptible,

        hospitalized=RateLos(hospitalized_rate, hospitalized_los),
        icu=RateLos(icu_rate, icu_los),
        ventilators=RateLos(ventilators_rate, ventilators_los),

        total_non_covid_beds= total_non_covid_beds,
        total_non_covid_icu_beds=total_non_covid_icu_beds,
        total_non_covid_vents=total_non_covid_vents,

        author = author,
        scenario = scenario,

        census_date = census_date,
        selected_offset = d.selected_offset,
    )
    return parameters


def show_more_info_about_this_tool(st, model, parameters, defaults, notes: str = ""):
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
            recovery_days=int(parameters.recovery_days)
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
            recovery_days=parameters.recovery_days,
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
        + "- "
        + "| \n".join(
            f"{key} = {value} "
            for key, value in defaults.region.__dict__.items()
            if key != "_s"
        )
    )
    return None


def write_definitions(st):
    st.subheader("Application Guidance")
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


def write_footer(st):
    st.subheader("References & Acknowledgements")
    st.markdown(
        """* This application is based on the work that is developed and made freely available (under MIT license) by Penn Medicine (https://github.com/CodeForPhilly/chime). 
        """
    )
    st.markdown("© 2020, Health Catalyst Inc.")


def show_additional_projections(
    st, alt, charting_func, model, parameters
):
    st.subheader(
        "The number of infected and recovered individuals in the hospital catchment region at any given moment"
    )

    st.altair_chart(
        charting_func(
            alt,
            model=model,
            parameters=parameters
        ),
        use_container_width=True,
    )


##########
# Tables #
##########


def draw_projected_admissions_table(
    st, parameters, projection_admits: pd.DataFrame, labels, as_date: bool = False, daily_count: bool = False,
    ):
    if daily_count == True:
        admits_table = projection_admits
    else:
        admits_table = projection_admits.iloc[::7]
    admits_table["day"] = admits_table.index
    admits_table.index = range(admits_table.shape[0])
    admits_table = np.ceil(admits_table.fillna(0)).astype(int)

    if as_date:
        admits_table = add_date_column(
            admits_table, parameters, drop_day_column=True, date_format=DATE_FORMAT, daily_count=daily_count
        )
    admits_table.rename(labels)
    st.table(admits_table)
    return None


def draw_census_table(st, parameters, census_df: pd.DataFrame, labels, as_date: bool = False, daily_count: bool = False):
    if daily_count == True:
        census_table = census_df
    else:
        census_table = census_df.iloc[::7]
    census_table.index = range(census_table.shape[0])
    census_table.loc[0, :] = 0
    census_table = census_table.dropna().astype(int)

    if as_date:
        census_table = add_date_column(
            census_table, parameters, drop_day_column=True, date_format=DATE_FORMAT, daily_count=daily_count
        )

    census_table.rename(labels)
    st.table(census_table)
    return None

def draw_beds_table(st, parameters, bed_df: pd.DataFrame, labels, as_date: bool = False, daily_count: bool = False):
    if daily_count == True:
        bed_table = bed_df
    else:
        bed_table = bed_df.iloc[::7]
    bed_table.index = range(bed_table.shape[0])
    bed_table.loc[0, :] = 0
    bed_table = bed_table.dropna().astype(int)

    if as_date:
        bed_table = add_date_column(
            bed_table, parameters, drop_day_column=True, date_format=DATE_FORMAT, daily_count=daily_count
        )

    bed_table.rename(labels)
    st.table(bed_table)
    return None

def draw_raw_sir_simulation_table(st, parameters, model):
    as_date = parameters.as_date
    projection_area = model.raw_df
    projection_area["day"] = projection_area.index.astype(int)
    infect_table = (projection_area.iloc[::7, :]).apply(np.floor)
    infect_table.index = range(infect_table.shape[0])
   
    if as_date:
        infect_table = add_date_column(
            infect_table, parameters, drop_day_column=True, date_format=DATE_FORMAT, daily_count=False
        )

    st.table(infect_table)
    build_download_link(st,
        filename="raw_sir_simulation_data.csv",
        df=projection_area,
        parameters=parameters
    )

def build_download_link(st, filename: str, df: pd.DataFrame, parameters: Parameters):
    if parameters.as_date:
        df = add_date_column(df, parameters, drop_day_column=True, date_format="%Y-%m-%d")

    csv = dataframe_to_base64(df)
    st.markdown("""
        <a download="{filename}" href="data:file/csv;base64,{csv}">Download full table as CSV</a>
""".format(csv=csv,filename=filename), unsafe_allow_html=True)

def build_data_and_params(projection_admits, census_df, beds_df, model, parameters):
    # taken from admissions table function:
    admits_table = projection_admits[np.mod(projection_admits.index, 1) == 0].copy()
    admits_table["day"] = admits_table.index.astype(int)
    admits_table.index = range(admits_table.shape[0])
    admits_table = admits_table.fillna(0).astype(int)
    # Add date info
    admits_table = add_date_column(
        admits_table, parameters, drop_day_column=True, date_format="%Y-%m-%d"
    )
    admits_table.rename(parameters.labels)

    # taken from census table function:
    census_table = census_df[np.mod(census_df.index, 1) == 0].copy()
    census_table.index = range(census_table.shape[0])
    census_table.loc[0, :] = 0
    census_table = census_table.dropna().astype(int)
    census_table.rename(parameters.labels)
    
    # taken from beds table function:

    bed_table = beds_df[np.mod(beds_df.index, 1) == 0].copy()
    bed_table.index = range(bed_table.shape[0])
    bed_table.loc[0, :] = 0
    bed_table = bed_table.dropna().astype(int)
    bed_table.rename(parameters.labels)

    # taken from raw sir table function:
    projection_area = model.raw_df
    infect_table = (projection_area.iloc[::1, :]).apply(np.floor)
    infect_table.index = range(infect_table.shape[0])
    infect_table["day"] = infect_table.index.astype(int)

    # Build full dataset
    df = admits_table.copy()
    df = df.rename(columns = {
        "date": "Date",
        "total": "TotalAdmissions", 
        "icu": "ICUAdmissions", 
        "ventilators": "ventilatorsAdmissions"}, )
    
    df["TotalCensus"] = census_table["total"]
    df["ICUCensus"] = census_table["icu"]
    df["ventilatorsCensus"] = census_table["ventilators"]

    df["TotalBeds"] = bed_table["total"]
    df["ICUBeds"] = bed_table["icu"]
    df["Ventilators"] = bed_table["ventilators"]

    df["Susceptible"] = infect_table["susceptible"]
    df["Infections"] = infect_table["infected"]
    df["Recovered"] = infect_table["recovered"]

    df["Author"] = parameters.author
    df["Scenario"] = parameters.scenario
    df["DateGenerated"] = datetime.utcnow().isoformat()

    df["CurrentlyHospitalizedCovidPatients"] = parameters.current_hospitalized
    df["CurrentlyHospitalizedCovidPatientsDate"] = parameters.census_date
    df["SelectedOffsetDays"] = parameters.selected_offset
    df["DoublingTimeBeforeSocialDistancing"] = parameters.doubling_time
    df["SocialDistancingPercentReduction"] = parameters.relative_contact_rate
    
    df["HospitalizationPercentage"] = parameters.hospitalized.rate
    df["ICUPercentage"] = parameters.icu.rate
    df["ventilatorsPercentage"] = parameters.ventilators.rate

    df["HospitalLengthOfStay"] = parameters.hospitalized.length_of_stay
    df["ICULengthOfStay"] = parameters.icu.length_of_stay
    df["VentLengthOfStay"] = parameters.ventilators.length_of_stay

    df["HospitalMarketShare"] = parameters.market_share
    df["RegionalPopulation"] = parameters.susceptible
    
    df["TotalNumberOfBedsForNCPatients"] = parameters.total_non_covid_beds
    df["TotalNumberOfICUBedsForNCPatients"] = parameters.total_non_covid_icu_beds
    df["TotalNumberOfVentsForNCPatients"] = parameters.total_non_covid_vents

    
    # Reorder columns
    df = df[[
        "Author", 
        "Scenario", 
        "DateGenerated",

        "CurrentlyHospitalizedCovidPatients",
        "CurrentlyHospitalizedCovidPatientsDate",
        "SelectedOffsetDays",
        "DoublingTimeBeforeSocialDistancing",
        "SocialDistancingPercentReduction",

        "HospitalizationPercentage",
        "ICUPercentage",
        "ventilatorsPercentage",

        "HospitalLengthOfStay",
        "ICULengthOfStay",
        "VentLengthOfStay",

        "HospitalMarketShare",
        "RegionalPopulation",
        "CurrentlyKnownRegionalInfections",
        
        "TotalNumberOfBeds",
        "TotalNumberOfBedsForNCPatients",
        "TotalNumberOfICUBeds",
        "TotalNumberOfICUBedsForNCPatients",
        "TotalNumberOfVents",
        "TotalNumberOfVentsForNCPatients",

        "Date",
        "TotalAdmissions", 
        "ICUAdmissions", 
        "ventilatorsAdmissions",

        "TotalCensus",
        "ICUCensus",
        "ventilatorsCensus",
        
        "TotalBeds",
        "ICUBeds",
        "Ventilators", 

        "Susceptible",
        "Infections",
        "Recovered"
        ]]
    return(df)