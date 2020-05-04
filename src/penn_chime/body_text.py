import streamlit as st
import datetime

from .parameters import Parameters, Mode
from .model_base import SimSirModelBase as Model
from .hc_actuals import actuals_download_widget


def display_app_title():
    st.subheader("Health Catalyst® COVID-19 Capacity Planning Tool")
    

def display_app_description():
    st.markdown(
        f"""
        Forecast local COVID-19 demand in the context of local system capacity to set 
        expectations and inform mitigation strategy:
        * Built on the outstanding [Penn Med](http://predictivehealthcare.pennmedicine.org/) [epidemic model] (https://penn-chime.phl.io/) - with additional features
        * **New: Forecast infections based upon actual county level data and dynamic infection spread rates (Empirical Model)**
        * Manage, use, and save scenarios, bed and ventilator capacity, and actual data
        * Estimate demand for personal protective equipment (PPE) and staff

        Important note on definitions (<span style="color:red;"><i>different from Penn Med model</i></span>):
        * Total: Sum of beds/patients in "non-ICU" plus "ICU" 
        * Ventilators: Devices used to assist with patient breathing, counted independently of beds (not a subset of ICU or Total patients/beds)
        * Length of Stay: ICU Admissions is divided into an ICU portion followed by a non-ICU portion

        Questions, comments, support, or requests: [covidcapacity@healthcatalyst.com](mailto:covidcapacity@healthcatalyst.com)  
        <p>See <strong><a href="#application_guidance">Application Guidance</a></strong> section below for more information.</p>
        """,
        unsafe_allow_html=True,
    )

def display_disclaimer():
    st.markdown(
        """
        **Notice**: _There is a high degree of uncertainty about the details of COVID-19 infection, transmission, 
        and the effectiveness of social distancing measures. Long-term projections made using this simplified 
        model of outbreak progression should be treated with extreme caution._ 
        """
    )

def display_parameter_text(m: "Model", p: Parameters):
    infected_population_warning_str = (
        """(Warning: The number of estimated infections is greater than the total regional population. Please verify the values entered in the sidebar.)"""
        if m.infected > p.population
        else ""
    )
    
    st.markdown(
        """The estimated number of currently infected individuals is **{total_infections:.0f}**. This is based on current inputs for
    Hospitalizations (**{current_hosp}**), Hospitalization rate (**{hosp_rate:.2%}**), Region size (**{S}**),
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
            hosp_rate=p.non_icu.rate,
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

def display_user_must_upload_actuals():
    st.markdown("""
    **Please use the file upload dialogue at the bottom of the sidebar to upload actual data which can be used to predict COVID-19 demand.**
    """)


def display_more_info(
    model: Model, parameters: Parameters, defaults: Parameters, notes: str = "",
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


def display_actuals_definitions():
    st.markdown("""<a name="application_guidance"></a>""", unsafe_allow_html=True)
    st.header("Application Guidance")
    st.subheader("Working with Scenarios")
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
    st.markdown(
    """
    Actuals are for comparison purposes only and may help you adjust parameters in the projection model such as 
    hospital market share and illness severity (e.g., hospitalization rates and length of stay).
    To upload actual data please use the file upload widget at the bottom of the sidebar.
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

    """
    )
    actuals_download_widget()


def display_footer():
    st.header("References & Acknowledgements")
    st.markdown(
        """* This application is based on the work that is developed and made freely available (under MIT license) by Penn Medicine (https://github.com/CodeForPhilly/chime). 
        """
    )
    
    st.markdown("""<a name="release_notes"></a>""", unsafe_allow_html=True)
    st.subheader("Features and Enhancements History")
    st.markdown("""  
        **V: 2.1.0 (Monday, May 4, 2020)**
        * Added "emprical forecasts".  Leverages county infection and population data to forecast future infections.
        * Changed how ICU length of stay is represented.

        **V: 1.7.1 (Tuesday, April 14, 2020)**
        * Added Non-ICU to all charts. This corresponds to Hospitalized in Penn Med.
        * Changed Total color to black, other colors match Penn Med.

        **V: 1.6.0 (Monday, April 13, 2020)**
        * Added ability to select a social distancing start date that is independent of the current date. This is to maintain **consistency with Penn Med's functionality**.

        **V: 1.5.3 (Thursday, April 09, 2020)** 
        * Added **staffing functionality**
        * Changed exported column name to "VentilatorsAdmissions"
        * Moved capacity parameters to lower on sidebar
        * Fixed a bug where first row contained NaNs in full downloaded data
        
        **V: 1.4.0 (Wednesday, April 08, 2020)** 
        * Added **PPE/patient/day functionality**
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


def display_empirical_long():
    st.markdown(
        """
        Rather than using a fixed infection spread rate modified by a single
        social distancing effective impact adjustment, "Empirical Model Mode"
        estimates future COVID-19 cases based upon case history to date.

        There is not a single best approach to estimating infection spread and
        forecasting methods across all regions.  Typically, it is possible to
        arrive at a reasonable approach through visual inspection and selecting
        the combination of "Infection Spread Measure" and "Forecast Method"
        accordingly.
        * Infection spread: Use either "Doubling Time" using the approach of [Hall, 2014] (https://doi.org/10.1093/molbev/mst187) or "Reproduction Rate" using the approach of [Cori, 2013] (https://doi.org/10.1093/aje/kwt133).
        * Forecast: Select from exponential smoothing or local (LOESS), spline, or linear regression.
        These calcualtions are done using [R] (https://www.r-project.org/)

        New hospital admissions, census, and other demand estimates are still
        derived from the SIR model.  What is different is how the SIR (specifically
        the "I" (Infected)) calculation is done:
        * Where actual new cases are available, this determines "I" directly.
        * For future days, the $\\beta$ term is derived dynamically based upon your selection of the Infection Spread and Forecast Method.
        By allowing dynamic infection spread, it is possible to capture the
        dynamic nature of epidemic spread and counter measures.

        Note that the forecast model will adjust for changes in contributors
        such as social distancing effectiveness and testing rates.  However, it
        will take some time for the model to adjust and extra caution should be
        applied in interpretation during times of rapid change.

        In addition, please note that the hospital admission and ventilator use
        percentage defaults should be inspected carefully when using actual
        infection data.  In many regions, testing was done disproportionately in
        patients presenting to the hospital--not the general population.  You may
        need to increase your hospital admission and ventilator use rates to gets
        appropriate volume in your region of interest.
        """
    )

    # Takes r_df
def display_empirical_short(d):
    a_start = d.date.min().strftime("%b %d")
    a_end = d.date.loc[d.rst==1].max().strftime("%b %d")
    f_end = d.date.max().strftime("%b %d")
    mm = d.mSIR.iloc[0].split(",")
    st.markdown(
        f"""
        Empirical Model Mode uses county data reported by the [New York Times](https://github.com/nytimes/covid-19-data)
        and 2019 census data from the [U.S. Census] (https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/counties/totals/)
        * Actuals presented from {a_start} to {a_end}
        * Daily cases through {f_end} estimated by applying {mm[1].strip()} forecasting to the {mm[0].strip()} growth metric.
        """
    )

def zero_admits_warning(p):
    params = []
    if p.non_icu.rate <= 0.1:
        params.append("Non-ICU")
    if p.icu.rate <= 0.05:
        params.append("ICU")
    if p.ventilators.rate <= 0.05:
        params.append("Ventilators")

    if (len(params) > 0) and (p.app_mode == Mode.EMPIRICAL):
        st.markdown(
            f"""
            *Please check "Severity Parameters" {", ".join(params)} 
            to ensure demand is appropriate given the subset of patients tested for COVID-19.*
            """
        )
