import base64
import io
from typing import Tuple, Union

import numpy as np
import pandas as pd

ADMISSIONS_COLUMNS = [
    "total_admissions_actual",
    "non_icu_admissions_actual",
    "icu_admissions_actual",
    "intubated_actual",
]

CENSUS_COLUMNS = [
    "total_census_actual",
    "non_icu_census_actual",
    "icu_census_actual",
    "ventilators_in_use_actual",
]

INPUT_SIR_COLUMNS = [
    "cumulative_regional_infections",
]

def parse_actuals(uploaded_actuals) -> Tuple[Union[pd.DataFrame, None], Union[str, None]]:
    try:
        uploaded_actuals.seek(0)
        actuals_raw = pd.read_csv(uploaded_actuals, header=0)
    except:
        return None, "Could not parse the input CSV file into a dataframe. Please check the format."
    required_columns = set(['date'])
    one_or_more = set(ADMISSIONS_COLUMNS + CENSUS_COLUMNS + INPUT_SIR_COLUMNS)
    input_columns_set = set(actuals_raw.columns)
    column_error_message = f"Input CSV must contain a column called 'date' and one or more of the following columns: {one_or_more}"
    if required_columns.intersection(input_columns_set) != required_columns:
        return None, column_error_message
    if len(input_columns_set.intersection(one_or_more)) == 0:
        return None, column_error_message
    try:
        actuals = (
            actuals_raw
            .assign(
                date=lambda d: pd.to_datetime(d.date)
            )
        )
    except:
        return None, "Problem parsing date column. If possible please use an ISO-formatted date string."
    # Drop columns that are not used by the app so we don't overwrite other columns when we do joins.
    all_app_columns = required_columns.union(one_or_more)
    extra_input_columns = input_columns_set.difference(all_app_columns)
    if len(extra_input_columns) > 0:
        actuals = actuals.drop(columns=list(extra_input_columns))
    # If cumulative_regional_infections is present convert it from cumulative to delta
    if 'cumulative_regional_infections' in actuals.columns:
        actuals['daily_regional_infections'] = actuals.cumulative_regional_infections - actuals.cumulative_regional_infections.shift(1)
    return actuals, None
    

def actuals_download_widget(st):
    column_order = ["date", "total_admissions_actual", "icu_admissions_actual", "intubated_actual", "total_census_actual", "icu_census_actual", "ventilators_in_use_actual", "cumulative_regional_infections"]
    rows = 25
    t = np.arange(rows) # Time
    tau = 7 # Time required to increase by a factor of b.
    b = np.e 
    a = 267 # Initial count
    infections = a * b ** (t / tau)
    sample_df = pd.DataFrame({
        "date": pd.date_range("2020-03-10", periods=rows, freq='D'),
        "cumulative_regional_infections": np.floor(infections), 
    }).assign(
        total_admissions_actual=lambda d: np.floor(d.cumulative_regional_infections * .025 * .15),
        icu_admissions_actual=lambda d: np.floor(d.total_admissions_actual * .25),
        intubated_actual=lambda d: np.floor(d.icu_admissions_actual * .5),
        total_census_actual=lambda d: (d.total_admissions_actual.cumsum() - d.total_admissions_actual.cumsum().shift(7, fill_value=0)),
        icu_census_actual=lambda d: (d.icu_admissions_actual.cumsum() - d.icu_admissions_actual.cumsum().shift(9, fill_value=0)),
        ventilators_in_use_actual=lambda d: (d.intubated_actual.cumsum() - d.intubated_actual.cumsum().shift(10, fill_value=0)),
    )[column_order]
    buffer = io.StringIO()
    sample_df.to_csv(buffer, index=False)
    csv_string = buffer.getvalue()
    encoded_csv = base64.b64encode(csv_string.encode()).decode()
    filename = "ActualDataExample.csv"
    st.markdown("To download an example CSV file that contains dummy actuals please use the button below.")
    st.markdown(
        """<a download="{filename}" href="data:text/plain;base64,{encoded_csv}" style="padding:.75em;border-radius:10px;background-color:#00aeff;color:white;font-family:sans-serif;text-decoration:none;">Download Example Actuals</a>"""
        .format(encoded_csv=encoded_csv,filename=filename), 
        unsafe_allow_html=True,
    )

def census_mismatch_message(parameters: "Parameters", actuals: pd.DataFrame, st):
    if actuals is None or 'total_census_actual' not in actuals.columns:
        return
    else:
        sidebar_census_date = parameters.covid_census_date
        possible_actual = actuals.loc[actuals.date == pd.Timestamp(sidebar_census_date)]
        if len(possible_actual) > 0:
            # They have an actual census number for the date they selected on the sidebar
            sidebar_census_number = parameters.covid_census_value
            if (sidebar_census_number != possible_actual.total_census_actual).iloc[0]:
                # They don't match, display the message
                st.markdown(f"""
                        <span style="color:red;font-size:small;">Warning: The "Current COVID-19 Total Hospital Census" parameter in the sidebar does not match the actual census value for the selected date ({sidebar_census_date.isoformat()}). The census value from the uploaded actuals for that date is {int(possible_actual.total_census_actual.iloc[0])}.</span> 
                    """, 
                    unsafe_allow_html=True
                )
        else:
            # They do not have an actual census for their selected census date, display nothing
            pass
