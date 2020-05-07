from __future__ import annotations

import logging
import datetime
from typing import Dict, Sequence, Tuple

import numpy as np
import pandas as pd 

from .parameters import Parameters


class SimSirModelBase:

    def __init__(self, p: Parameters):

        self.rates = {
            key: d.rate
            for key, d in p.dispositions.items()
        }

        self.days = {
            key: d.days
            for key, d in p.dispositions.items()
        }
        self.p = p
        self.gamma = 1.0 / p.infectious_days
        self.keys = ("susceptible", "infected", "recovered")
        self.raw = pd.DataFrame() # Placeholder to satisfy the linter, subclasses overwrite this

    def sir(
        self, s: float, i: float, r: float, beta: float, gamma: float, n: float
    ) -> Tuple[float, float, float]:
        """The SIR model, one time step."""
        s_n = (-beta * s * i) + s
        i_n = (beta * s * i - gamma * i) + i
        r_n = gamma * i + r
        scale = n / (s_n + i_n + r_n)
        return s_n * scale, i_n * scale, r_n * scale

    def add_counts(self):
        """
        Adds the admits, census, beds, ppe, and staffing dataframes
        to the model object, `model`.
        """
        self.dispositions_df = pd.DataFrame(data={
            'day': self.raw['day'],
            'date': self.raw['date'],
            'ever_non_icu': self.raw['ever_non_icu'],
            'ever_icu': self.raw['ever_icu'],
            'ever_ventilators': self.raw['ever_ventilators'],
        })
        self.admits_df = pd.DataFrame(data={
            'day': self.raw['day'],
            'date': self.raw['date'],
            'non_icu': self.raw['admits_non_icu'],
            'non_icu_after_icu': self.raw['admits_non_icu_after_icu'],
            'icu': self.raw['admits_icu'],
            'ventilators': self.raw['admits_ventilators'],
            'total': self.raw['admits_total']
        })
        self.census_df = pd.DataFrame(data={
            'day': self.raw['day'],
            'date': self.raw['date'],
            'non_icu': self.raw['census_non_icu'],
            'non_icu_after_icu': self.raw['census_non_icu_after_icu'],
            'icu': self.raw['census_icu'],
            'ventilators': self.raw['census_ventilators'],
            'total': self.raw['census_total'],
        })
        self.beds_df = self.build_beds_df(self.census_df, self.p)
        self.ppe_df = self.build_ppe_df(self.census_df, self.p)
        self.staffing_df = self.build_staffing_df(self.census_df, self.p)

        self.sim_sir_w_date_df = self.build_sim_sir_w_date_df(self.raw, self.p.covid_census_date, self.keys)

        self.sim_sir_w_date_floor_df = self.build_floor_df(self.sim_sir_w_date_df, self.keys)
        self.admits_floor_df = self.build_floor_df(self.admits_df, self.p.dispositions.keys())
        self.census_floor_df = self.build_floor_df(self.census_df, self.p.dispositions.keys())
        self.beds_floor_df = self.build_floor_df(self.beds_df, self.beds_df.columns[2:])
        self.ppe_floor_df = self.build_floor_df(self.ppe_df, self.ppe_df.columns[2:])
        self.staffing_floor_df = self.build_floor_df(self.staffing_df, self.staffing_df.columns[2:])


    def build_sim_sir_w_date_df(
        self,
        raw: Dict,
        current_date: datetime.datetime,
        keys: Sequence[str],
    ) -> pd.DataFrame:
        day = pd.Series(raw['day'])
        return pd.DataFrame({
            "day": day,
            "date": day.astype('timedelta64[D]') + np.datetime64(current_date),
            **{
                key: raw[key]
                for key in keys
            }
        })


    def build_floor_df(self, df, keys):
        """Build floor sim sir w date."""
        return pd.DataFrame({
            "day": df.day,
            "date": df.date,
            **{
                key: np.floor(df[key])
                for key in keys
            }
        })


    def build_beds_df(
        self,
        census_df: pd.DataFrames,
        p,
    ) -> pd.DataFrame:
        """ALOS for each category of COVID-19 case (total guesses)"""
        beds_df = pd.DataFrame()
        beds_df["day"] = census_df["day"]
        beds_df["date"] = census_df["date"]

        # If hospitalized < 0 and there's space in icu, start borrowing if possible
        # If ICU < 0, raise alarms. No changes.
        beds_df["non_icu"] = p.total_covid_beds - p.icu_covid_beds - census_df["non_icu"]
        beds_df["icu"] = p.icu_covid_beds - census_df["icu"]
        beds_df["ventilators"] = p.covid_ventilators - census_df["ventilators"]
        beds_df["total"] = p.total_covid_beds - census_df["non_icu"] - census_df["icu"]
        # beds_df = beds_df.head(n_days)

        # Shift people to ICU if main hospital is full and ICU is not.
        # And vice versa
        if p.beds_borrow:
            new_hosp = []
            new_icu = []
            for row in beds_df.itertuples():
                if row.non_icu < 0 and row.icu > 0: # ICU to Non-ICU
                    needed = min(abs(row.non_icu), row.icu)
                    new_hosp.append(row.non_icu + needed)
                    new_icu.append(row.icu - needed)
                elif row.non_icu > 0 and row.icu < 0: # Non-ICU to ICU
                    needed = min(abs(row.icu), row.non_icu)
                    new_hosp.append(row.non_icu - needed)
                    new_icu.append(row.icu + needed)
                else: 
                    new_hosp.append(row.non_icu)
                    new_icu.append(row.icu)
            beds_df["non_icu"] = new_hosp
            beds_df["icu"] = new_icu
            beds_df = beds_df[["day", "date", "total", "non_icu", "icu", "ventilators"]]
        return beds_df


    def build_ppe_df(
        self,
        census_df: pd.DataFrames,
        p,
    ) -> pd.DataFrame:
        """ALOS for each category of COVID-19 case (total guesses)"""
        ppe_df = pd.DataFrame()
        ppe_df["day"] = census_df["day"]
        ppe_df["date"] = census_df["date"]

        fnic = np.floor(census_df.non_icu) # floored non-icu census
        ppe_df["masks_n95_non_icu"] = p.masks_n95 * fnic
        ppe_df["masks_surgical_non_icu"] = p.masks_surgical * fnic
        ppe_df["face_shield_non_icu"] = p.face_shield * fnic
        ppe_df["gloves_non_icu"] = p.gloves * fnic
        ppe_df["gowns_non_icu"] = p.gowns * fnic
        ppe_df["other_ppe_non_icu"] = p.other_ppe * fnic

        fic = np.floor(census_df.icu) # floored icu census
        ppe_df["masks_n95_icu"] = p.masks_n95_icu * fic
        ppe_df["masks_surgical_icu"] = p.masks_surgical_icu * fic
        ppe_df["face_shield_icu"] = p.face_shield_icu * fic
        ppe_df["gloves_icu"] = p.gloves_icu * fic
        ppe_df["gowns_icu"] = p.gowns_icu * fic
        ppe_df["other_ppe_icu"] = p.other_ppe_icu * fic
        
        ppe_df["masks_n95_total"] = ppe_df["masks_n95_non_icu"] + ppe_df["masks_n95_icu"]
        ppe_df["masks_surgical_total"] = ppe_df["masks_surgical_non_icu"] + ppe_df["masks_surgical_icu"]
        ppe_df["face_shield_total"] = ppe_df["face_shield_non_icu"] + ppe_df["face_shield_icu"]
        ppe_df["gloves_total"] = ppe_df["gloves_non_icu"] + ppe_df["gloves_icu"]
        ppe_df["gowns_total"] = ppe_df["gowns_non_icu"] + ppe_df["gowns_icu"]
        ppe_df["other_ppe_total"] = ppe_df["other_ppe_non_icu"] + ppe_df["other_ppe_icu"]

        return ppe_df


    def build_staffing_df(
        self,
        census_df: pd.DataFrames,
        p,
    ) -> pd.DataFrame:
        """ALOS for each category of COVID-19 case (total guesses)"""
        staffing_df = pd.DataFrame()
        staffing_df["day"] = census_df["day"]
        staffing_df["date"] = census_df["date"]

        stf_mul = 24.0 / p.shift_duration # Staffing Multiplier
        fnic = np.floor(census_df.non_icu) # floored non-icu census
        fic = np.floor(census_df.icu) # floored icu census

        staffing_df["nurses_non_icu"] = np.ceil(np.ceil(
            fnic / p.nurses) * stf_mul) if p.nurses !=0 else 0
        staffing_df["physicians_non_icu"] = np.ceil(np.ceil(
            fnic / p.physicians) * stf_mul) if p.physicians != 0 else 0
        staffing_df["advanced_practice_providers_non_icu"] = np.ceil(np.ceil(
            fnic / p.advanced_practice_providers) * stf_mul) if p.advanced_practice_providers != 0 else 0
        staffing_df["healthcare_assistants_non_icu"] = np.ceil(np.ceil(
            fnic / p.healthcare_assistants) * stf_mul) if p.healthcare_assistants != 0 else 0
        staffing_df["other_staff_non_icu"] = np.ceil(np.ceil(
        fnic / p.other_staff) * stf_mul) if p.other_staff != 0 else 0

        staffing_df["nurses_icu"] = np.ceil(np.ceil(
            fic / p.nurses_icu) * stf_mul) if p.nurses_icu !=0 else 0
        staffing_df["physicians_icu"] = np.ceil(np.ceil(
            fic / p.physicians_icu) * stf_mul) if p.physicians_icu !=0 else 0
        staffing_df["advanced_practice_providers_icu"] = np.ceil(np.ceil(
            fic / p.advanced_practice_providers_icu) * stf_mul) if p.advanced_practice_providers_icu !=0 else 0
        staffing_df["healthcare_assistants_icu"] = np.ceil(np.ceil(
            fic / p.healthcare_assistants_icu) * stf_mul) if p.healthcare_assistants_icu !=0 else 0
        staffing_df["other_staff_icu"] = np.ceil(np.ceil(
            fic / p.other_staff_icu) * stf_mul) if p.other_staff_icu != 0 else 0

        staffing_df["nurses_total"] = np.ceil(staffing_df["nurses_non_icu"] + staffing_df["nurses_icu"])
        staffing_df["physicians_total"] = np.ceil(staffing_df["physicians_non_icu"] + staffing_df["physicians_icu"])
        staffing_df["advanced_practice_providers_total"] = np.ceil(staffing_df["advanced_practice_providers_non_icu"] + staffing_df["advanced_practice_providers_icu"])
        staffing_df["healthcare_assistants_total"] = np.ceil(staffing_df["healthcare_assistants_non_icu"] + staffing_df["healthcare_assistants_icu"])
        staffing_df["other_staff_total"] = np.ceil(staffing_df["other_staff_non_icu"] + staffing_df["other_staff_icu"])
        return staffing_df


    def calculate_dispositions(
        self,
        raw: Dict,
        rates: Dict[str, float],
        market_share: float,
    ):
        """Build dispositions dataframe of patients adjusted by rate and market_share."""
        for key, rate in rates.items():
            raw["ever_" + key] = raw["ever_infected"] * rate * market_share
            raw[key] = raw["ever_infected"] * rate * market_share


    def calculate_admits(self, raw: Dict, rates, p,):
        """Build admits dataframe from dispositions."""
        for key in rates.keys():
            ever = raw["ever_" + key]
            admit = np.empty_like(ever)
            admit[0] = np.nan
            admit[1:] = ever[1:] - ever[:-1]
            raw["admits_"+key] = admit
            raw[key] = admit
        
        # Pad with icu LOS 0's then cut off icu LOS from end.
        if p.non_icu_after_icu.days > 0:  # If non-ICU LOS > 0, shift by icu LOS
            raw["admits_non_icu_after_icu"] = np.pad(
                raw["admits_icu"], [p.icu.days, 0], mode="constant")[:-p.icu.days]
        else:
            raw["admits_non_icu_after_icu"] = np.zeros(len(raw["admits_non_icu"]))
        # Uncomment to count transfers as admissions to non-icu, though this double counts census.
        # Have to copy admits_non_icu before the addition to avoid double counting. When commented, census is correct. 
        # raw["admits_non_icu"] = raw["admits_non_icu"] + raw["admits_non_icu_after_icu"]
        raw['admits_total'] = np.floor(raw['admits_non_icu']) + np.floor(raw['admits_icu'])

        # Replace NaNs with 0
        for key in raw.keys():
            raw[key] = np.nan_to_num(raw[key])

    def calculate_census(
        self,
        raw: Dict,
        lengths_of_stay: Dict[str, int],
    ):
        """Average Length of Stay for each disposition of COVID-19 case (total guesses)"""
        n_days = raw["day"].shape[0]
        for key, los in lengths_of_stay.items():
            if (key == "non_icu_after_icu") and (los == 0):
                raw['census_non_icu_after_icu'] = np.zeros(len(raw["census_icu"]))
            else:
                cumsum = np.empty(n_days + los)
                cumsum[:los+1] = 0.0
                cumsum[los+1:] = raw["admits_" + key][1:].cumsum()

                census = cumsum[los:] - cumsum[:-los]
                raw["census_" + key] = census
        raw['census_non_icu'] = raw['census_non_icu'] + raw['census_non_icu_after_icu']
        raw['census_total'] = np.floor(raw['census_non_icu']) + np.floor(raw['census_icu'])
