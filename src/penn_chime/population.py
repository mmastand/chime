import streamlit as st

def display_population_widgets(p, selected_states, selected_counties, nat_data) -> int:
    sub_nat = nat_data.loc[nat_data.state.isin(selected_states) & nat_data.county.isin(selected_counties)]
    population = int(sub_nat.pop_est2019.iloc[0])
    st.subheader(f"""Calculated Regional Population: {population:,}""")
    p.population
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
            value=p.population_manual_override,
        )
        p.population_manual_override = population_manual_override
        population = population_manual_override
    return population