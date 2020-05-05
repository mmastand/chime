import streamlit as st
import numpy as np

def display_population_widgets(p, selected_states, selected_counties, nat_data) -> int:
    sub_nat = nat_data.loc[nat_data.state.isin(selected_states) & nat_data.county.isin(selected_counties)]
    population = int(np.sum(sub_nat.pop_est2019.unique()).item())
    st.subheader(f"""Calculated Regional Population: {population:,}""")
    override_population = st.checkbox(
        "Override Calculated Population",
        value = p.override_population
    )
    p.override_population = override_population
    if override_population:
        population_manual_override = st.number_input(
            "Population",
            min_value=0,
            max_value=8000000000,
            step=100000,
            value=population if p.population_manual_override is None else p.population_manual_override,
        )
        p.population_manual_override = population_manual_override
        population = population_manual_override
    p.population = population
    return population