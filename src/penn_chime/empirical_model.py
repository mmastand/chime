import datetime
from typing import List
import json

import pandas as pd
import numpy as np
import requests
import streamlit as st

from .model_base import SimSirModelBase
from .parameters import Parameters, ForecastMethod, ForecastedMetric

EPOCH_START = datetime.datetime(1970, 1, 1)

class EmpiricalModel(SimSirModelBase):
    min_cases = 5

    @classmethod
    def can_use_actuals(cls, actuals: pd.DataFrame):
        if ("total_admissions_actual" in actuals.columns 
                and np.max(np.cumsum(actuals.total_admissions_actual)) >= cls.min_cases):
            return True
        return False

    @classmethod
    def get_actuals_invalid_message(cls):
        return """<p>In order to use actual data to predict COVID-19 demand please include the following columns: 'date', and 'total_admissions_actual'. 
        See the <a href="#working_with_actuals">Working with Actuals</a> section for details about supported columns and data types.</p>"""

    def __init__(self, p: Parameters, actuals: pd.DataFrame, states: List[str], counties: List[str]):
        super(EmpiricalModel, self).__init__(p)
        
        method = ForecastMethod.to_r_method(p.forecast_method)
        metric = ForecastedMetric.to_r_metric(p.forecasted_metric)
        py_in_df = self.r_input_from_actuals(actuals, states, counties)
        payload = json.loads(py_in_df.to_json(orient="records", date_format='iso'))
        response = requests.post(
            "http://localhost:8765/", 
            json=payload, 
            params={"method": method, "metric": metric}
        )
        response.raise_for_status()
        self.r_df = out_py_df = self.py_df_from_json_response(response.json())
        print(out_py_df.dtypes)

        self.raw = raw = self.raw_from_r_output(out_py_df)

        # self.calculate_dispositions(raw, self.rates, self.p.market_share)
        # self.calculate_admits(raw, self.rates)
        # self.calculate_census(raw, self.days)
        # self.add_counts()

    def py_df_from_json_response(self, response_dict):
        df = pd.read_json(response_dict)
        return (df)
        
    def dates_from_r_dates(self, elapsed_days):
        return EPOCH_START + datetime.timedelta(days=elapsed_days)

    def r_input_from_actuals(self, actuals, states, counties):
        
        states_str = "-".join(states)
        counties_str = "-".join(counties)
        region_str = ":".join([states_str, counties_str]).replace(' ', '')

        return (
            actuals
            .loc[actuals.state.isin(states) & actuals.county.isin(counties)]
            .groupby('date')
            .agg({
                "cases": "sum",
                "pop_est2019": "sum",
            })
            .reset_index()
            .rename(columns={"cases": "cumCases", "pop_est2019": "pop"})
            .assign(
                # Get daily cases from cumulative cases
                cases = lambda d: d.cumCases - d.cumCases.shift(1, fill_value=0),
                # Jason's code expects a 'rgn' column. He has it formatted as <state_abbr>:<county> but I don't 
                # think the column is really used.
                rgn = region_str, 
                # Take max population since regions may have different start days
                pop = lambda d: d['pop'].max() 
            )
        )

    def raw_from_r_output(self, r_output_df):
        raise NotImplementedError()
