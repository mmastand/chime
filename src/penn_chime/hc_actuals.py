from typing import Tuple, Union

import pandas as pd

ADMISSIONS_COLUMNS = [
    "total_admissions_actual",
    "icu_admissions_actual",
    "intubated_actual",
]

CENSUS_COLUMNS = [
    "total_census_actual",
    "icu_census_actual",
    "ventilators_in_use_actual",
]

SIR_COLUMNS = [
    "cumulative_regional_infections",
]

def parse_actuals(uploaded_actuals) -> Tuple[Union[pd.DataFrame, None], Union[str, None]]:
    try:
        uploaded_actuals.seek(0)
        actuals_raw = pd.read_csv(uploaded_actuals, header=0)
    except:
        return None, "Could not parse the input CSV file into a dataframe. Please check the format."
    required_columns = set(['date'])
    one_or_more = set(ADMISSIONS_COLUMNS + CENSUS_COLUMNS + SIR_COLUMNS)
    column_error_message = f"Input CSV must contain a column called 'date' and one or more of the following columns: {one_or_more}"
    if required_columns.intersection(set(actuals_raw.columns)) != required_columns:
        return None, column_error_message
    if len(set(actuals_raw.columns).intersection(one_or_more)) == 0:
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
    # TODO: drop columns that aren't listed above
    return actuals, None
