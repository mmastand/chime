from sys import stdout
from logging import INFO, basicConfig

basicConfig(
    level=INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=stdout,
)

import datetime

import streamlit as st  # type: ignore

from penn_chime.sidebar import display_sidebar
from penn_chime.body_text import (
    display_app_title,
    display_app_description,
    display_disclaimer,
    display_parameter_text,
    display_user_must_upload_actuals,
    display_more_info,
    display_actuals_definitions,
    display_footer,
)
from penn_chime.body_charts import display_body_charts
from penn_chime.settings import get_defaults
from penn_chime.penn_model import PennModel
from penn_chime.empirical_model import EmpiricalModel
from penn_chime.parameters import Mode
from penn_chime.national_data import get_national_data
from penn_chime.dummy_data import prep_dummy_data
from penn_chime.hc_param_import_export import param_download_widget


# This is somewhat dangerous:
# Hide the main menu with "Rerun", "run on Save", "clear cache", and "record a screencast"
# This should not be hidden in prod, but removed
# In dev, this should be shown
hide_menu_style = """
<style>
#MainMenu {visibility: hidden;}
</style>
"""
st.markdown(hide_menu_style, unsafe_allow_html=True)


d = get_defaults()
p, actuals, mode = display_sidebar(d)
display_app_title()
display_app_description()
display_disclaimer()

if mode == Mode.EMPIRICAL:
    ## Logic to control whether we use county data or actuals. For now we are only using county data.
    # if actuals == None:
    #     # Display a placeholder instructing the user to upload actuals
    #     # so we can run the model and display the projections
    #     display_user_must_upload_actuals()
    # else:
    #     if EmpiricalModel.can_use_actuals(actuals):
    #         # Use Actuals
    #     else:
    #         # Display a warning message that the actuals do not contain the needed information to run the model
    #         text = EmpiricalModel.get_actuals_invalid_message()
    #         st.markdown(text, unsafe_allow_html=True)

    # Pick county to use for actuals
    nat_data = get_national_data()

    states = sorted(list(nat_data.state.unique()))
    selected_states = st.multiselect("Please choose one or more states.", states, default=p.selected_states)
    if len(selected_states) > 0:
        p.selected_states = selected_states
        counties = nat_data.loc[nat_data.state.isin(selected_states)].county.unique()
        counties = sorted(list(counties))
        selected_counties = st.multiselect("Please choose one or more counties.", counties, default=p.selected_counties)

        if len(selected_counties) > 0:
            p.selected_counties = selected_counties
            m = EmpiricalModel(p, nat_data, selected_states, selected_counties)
            # Display population
            population = m.r_df['pop'].iloc[0]
            st.subheader(f"""Regional Population: {population}""")
            display_body_charts(m, p, d, actuals, mode)
    else:
        st.markdown("""
            <h4 style="color:#00aeff">Please selected your geographic region above to generate COVID-19 projections.</h4>
        """, unsafe_allow_html=True)
    

        
else:
    # Mode is classic Penn
    m = PennModel(p)
    display_parameter_text(m, p)
    if st.checkbox("Show more info about this tool"):
        notes = "The total size of the susceptible population will be the entire catchment area for our hospitals."
        display_more_info(model=m, parameters=p, defaults=d, notes=notes)
    display_body_charts(m, p, d, actuals, mode)

display_actuals_definitions()
display_footer()
param_download_widget(p)
