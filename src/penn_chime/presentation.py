"""effectful functions for streamlit io"""

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
        
        See **Application Guidance** section below for more information 
        """,
        unsafe_allow_html=True,)

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


class Input:
    """Helper to separate Streamlit input definition from creation/rendering"""

    def __init__(self, st_obj, label, value, kwargs):
        self.st_obj = st_obj
        self.label = label
        self.value = value
        self.kwargs = kwargs

    def __call__(self):
        return self.st_obj(self.label, value=self.value, **self.kwargs)


class NumberInput(Input):
    def __init__(
        self,
        st_obj,
        label,
        min_value=None,
        max_value=None,
        value=None,
        step=None,
        format=None,
        key=None,
    ):
        kwargs = dict(
            min_value=min_value, max_value=max_value, step=step, format=format, key=key
        )
        super().__init__(st_obj.number_input, label, value, kwargs)


class DateInput(Input):
    def __init__(self, st_obj, label, value=None, key=None):
        kwargs = dict(key=key)
        super().__init__(st_obj.date_input, label, value, kwargs)


class PercentInput(NumberInput):
    def __init__(
        self,
        st_obj,
        label,
        min_value=0.0,
        max_value=100.0,
        value=None,
        step=FLOAT_INPUT_STEP,
        format="%f",
        key=None,
    ):
        super().__init__(
            st_obj, label, min_value, max_value, value * 100.0, step, format, key
        )

    def __call__(self):
        return super().__call__() / 100.0


class CheckboxInput(Input):
    def __init__(self, st_obj, label, value=None, key=None):
        kwargs = dict(key=key)
        super().__init__(st_obj.checkbox, label, value, kwargs)

class TextInput(Input):
    def __init__(self, st_obj, label, value=None, key=None):
        kwargs = dict(key=key)
        super().__init__(st_obj.text_input, label, value, kwargs)


def display_sidebar(st, d: Parameters) -> Parameters:
    # Initialize variables
    # these functions create input elements and bind the values they are set to
    # to the variables they are set equal to
    # it's kindof like ember or angular if you are familiar with those
    st_obj = st.sidebar
    st.sidebar.markdown(
        "### Scenario"
    )
    uploaded_file = st.sidebar.file_uploader("Load Scenario", type=['json'])
    if uploaded_file is not None:
        d = constants_from_uploaded_file(uploaded_file)

    st.sidebar.markdown("""
        <span style="color:red;font-size:small;">Known Limitation: You must refresh your browser window before loading scenario, otherwise the projections will not be updated.</span> 
    """, unsafe_allow_html=True)

    author_input = TextInput(
        st_obj,
        "Author Name", 
        value="Jane Doe" if uploaded_file is None else d.author
    )
    
    scenario_input = TextInput(
        st_obj,
        "Scenario Name", 
        value="COVID Model" if uploaded_file is None else d.scenario
    )

    n_days_input = NumberInput(
        st_obj,
        "Number of days to project",
        min_value=30,
        value=d.n_days,
        step=1,
        format="%i",
    )
    doubling_time_input = NumberInput(
        st_obj,
        "Doubling time in days (up to today)",
        min_value=0.5,
        value=d.doubling_time,
        step=0.25,
        format="%f",
    )
    social_distancing_start_date_input = DateInput(
        st_obj, "Date when Social Distancing Protocols Started (Default is today)", value=d.social_distancing_start_date,
    )
    date_first_hospitalized_input = DateInput(
        st_obj, "Date of first hospitalized case - Enter this date to have chime estimate the initial doubling time",
        value=d.date_first_hospitalized,
    )
    relative_contact_pct_input = PercentInput(
        st_obj,
        "Social distancing (% reduction in social contact going forward)",
        min_value=0.0,
        max_value=100.0,
        value=d.relative_contact_rate,
        step=1.0,
    )
    hospitalized_pct_input = PercentInput(
        st_obj, "Hospitalization %(total infections)", value=d.hospitalized.rate,
    )
    icu_pct_input = PercentInput(
        st_obj,
        "ICU %(total infections)",
        min_value=0.0,
        value=d.icu.rate,
        step=0.05
    )
    ventilators_pct_input = PercentInput(
        st_obj, "Ventilators %(total infections)", value=d.ventilators.rate,
    )
    hospitalized_days_input = NumberInput(
        st_obj,
        "Average Hospital Length of Stay (days)",
        min_value=0,
        value=d.hospitalized.days,
        step=1,
        format="%i",
    )
    icu_days_input = NumberInput(
        st_obj,
        "Average Days in ICU",
        min_value=0,
        value=d.icu.days,
        step=1,
        format="%i",
    )
    ventilators_days_input = NumberInput(
        st_obj,
        "Average Days on Ventilator",
        min_value=0,
        value=d.ventilators.days,
        step=1,
        format="%i",
    )
    market_share_pct_input = PercentInput(
        st_obj,
        "Hospital Market Share (%)",
        min_value=0.5,
        value=d.market_share,
    )
    population_input = NumberInput(
        st_obj,
        "Regional Population",
        min_value=1,
        value=(d.population),
        step=1,
        format="%i",
    )
    covid_census_value_input = NumberInput(
        st_obj,
        "COVID-19 Total Hospital Census",
        min_value=0,
        value=d.covid_census_value,
        step=1,
        format="%i",
    )
    covid_census_date_input = DateInput(
        st_obj,
        "COVID-19 Total Hospital Census Date",
        value = d.covid_census_date,
    )
    total_covid_beds_input = NumberInput(
        st_obj,
        "Total # of Beds for COVID-19 Patients",
        min_value=0,
        value=d.total_covid_beds,
        step=10,
        format="%i",
    )
    icu_covid_beds_input = NumberInput(
        st_obj,
        "Total # of ICU Beds for COVID-19 Patients",
        min_value=0,
        value=d.icu_covid_beds,
        step=5,
        format="%i",
    )
    covid_ventilators_input = NumberInput(
        st_obj,
        "Total # of Ventilators for COVID-19 Patients",
        min_value=0,
        value=d.covid_ventilators,
        step=5,
        format="%i",
    )
    infectious_days_input = NumberInput(
        st_obj,
        "Infectious Days",
        min_value=0,
        value=d.infectious_days,
        step=1,
        format="%i",
    )
    max_y_axis_set_input = CheckboxInput(
        st_obj, "Set the Y-axis on graphs to a static value"
    )
    max_y_axis_input = NumberInput(
        st_obj, "Y-axis static value", value=500, format="%i", step=25
    )

    # Build in desired order

    author = author_input()
    scenario = scenario_input()

    st.sidebar.markdown(
        "### Hospital Parameters"
    )
    population = population_input()
    market_share = market_share_pct_input()
    covid_census_value = covid_census_value_input()
    covid_census_date = covid_census_date_input()

    st.sidebar.markdown(
        "### Hospital Capacity"
    )
    total_covid_beds = total_covid_beds_input()
    icu_covid_beds = icu_covid_beds_input()
    covid_ventilators = covid_ventilators_input()

    st.sidebar.markdown(
        "### Spread and Contact Parameters"
    )

    
    # parameter.first_hospitalized_date_known = st.sidebar.checkbox("Set the Y-axis on graphs to a static value", value=max_y_axis_set_default)
    
    first_hospitalized_date_known_default = False if uploaded_file is None else d.first_hospitalized_date_known

    if st.sidebar.checkbox(
        "I know the date of the first hospitalized case.", value=first_hospitalized_date_known_default
    ):
        date_first_hospitalized = date_first_hospitalized_input()
        first_hospitalized_date_known = True
        doubling_time = None
    else:
        doubling_time = doubling_time_input()
        first_hospitalized_date_known = False
        date_first_hospitalized = None

    relative_contact_rate = relative_contact_pct_input()

    social_distancing_start_date = social_distancing_start_date_input()

    st.sidebar.markdown(
        "### Severity Parameters"
    )
    hospitalized_rate = hospitalized_pct_input()
    icu_rate = icu_pct_input()
    ventilators_rate = ventilators_pct_input()
    infectious_days = infectious_days_input()
    hospitalized_days = hospitalized_days_input()
    icu_days = icu_days_input()
    ventilators_days = ventilators_days_input()

    st.sidebar.markdown(
        "### Display Parameters"
    )
    n_days = n_days_input()
    
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
        max_y_axis=max_y_axis,
        n_days=n_days,
        population=population,
        author=author,
        scenario=scenario,
        first_hospitalized_date_known=first_hospitalized_date_known,
    )

    param_download_widget(
        st,
        parameters, 
        max_y_axis_set=max_y_axis_set, 
        max_y_axis=max_y_axis
    )

    return parameters

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

def build_data_and_params(projection_admits, census_df, beds_df, model, parameters):
    # taken from admissions table function:
    admits_table = projection_admits[np.mod(projection_admits.index, 1) == 0].copy()
    admits_table["day"] = admits_table.index.astype(int)
    admits_table.index = range(admits_table.shape[0])
    admits_table = admits_table.fillna(0).astype(int)
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
    df["DateGenerated"] = datetime.datetime.utcnow().isoformat()

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
        # "CurrentlyKnownRegionalInfections",
        
        # "TotalNumberOfBeds",
        "TotalNumberOfBedsForNCPatients",
        # "TotalNumberOfICUBeds",
        "TotalNumberOfICUBedsForNCPatients",
        # "TotalNumberOfVents",
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