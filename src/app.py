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
from penn_chime.r_stuff import do_r_stuff, get_county_data
from penn_chime.parameters import Mode


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
    if actuals == None:
        # Display a placeholder instructing the user to upload actuals
        # so we can run the model and display the projections
        display_user_must_upload_actuals()
    else:
        if EmpiricalModel.can_use_actuals(actuals):
            # Pick county to use for actuals
            # nyt_data = get_county_data()
            # st.dataframe(nyt_data)

            # states = list(nyt_data.state.unique()).sort()
            # selected_states = st.multiselect("Please choose a state.", states)
            # if len(selected_states) > 0:
            #     counties = nyt_data.loc[nyt_data.state.isin(selected_states)].county.unique()
            #     counties = list(counties).sort()
            #     st.multiselect("Please choose a county.", counties)

            # m = EmpiricalModel(p, actuals)
            # display_body_charts(m, p, d, actuals, mode)
            pass
        else:
            # Display a warning message that the actuals do not contain the needed information to run the model
            text = EmpiricalModel.get_actuals_invalid_message()
            st.markdown(text, unsafe_allow_html=True)
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
