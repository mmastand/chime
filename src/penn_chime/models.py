"""Models.

Changes affecting results or their presentation should also update
constants.py `change_date`,
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from logging import INFO, basicConfig, getLogger
from sys import stdout
from typing import Dict, Generator, Tuple, Sequence, Optional

import numpy as np
import pandas as pd

from .constants import EPSILON, CHANGE_DATE
from .parameters import Parameters


basicConfig(
    level=INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=stdout,
)
logger = getLogger(__name__)


class SimSirModel:

    def __init__(self, p: Parameters):

        self.rates = {
            key: d.rate
            for key, d in p.dispositions.items()
        }

        self.days = {
            key: d.days
            for key, d in p.dispositions.items()
        }

        self.keys = ("susceptible", "infected", "recovered")

        # An estimate of the number of infected people on the day that
        # the first hospitalized case is seen
        #
        # Note: this should not be an integer.
        infected = (
            1.0 / p.market_share / p.non_icu.rate
        )

        susceptible = p.population - infected

        gamma = 1.0 / p.infectious_days
        self.gamma = gamma

        self.susceptible = susceptible
        self.infected = infected
        self.recovered = p.recovered

        if p.doubling_time is not None:
            # Back-projecting to when the first hospitalized case would have been admitted
            logger.info('Using doubling_time: %s', p.doubling_time)

            intrinsic_growth_rate = get_growth_rate(p.doubling_time)
            self.beta = get_beta(intrinsic_growth_rate,  gamma, self.susceptible, 0.0)
            self.beta_t = get_beta(intrinsic_growth_rate, self.gamma, self.susceptible, p.relative_contact_rate)

            if p.mitigation_date is None:
                self.i_day = 0 # seed to the full length
                temp_n_days = p.n_days
                p.n_days = 1000
                raw = self.run_projection(p, [(self.beta, p.n_days)])
                self.i_day = i_day = int(get_argmin_ds(raw["census_non_icu"], p.covid_census_value))
                p.n_days = temp_n_days

                self.raw = self.run_projection(p, self.gen_policy(p))

                logger.info('Set i_day = %s', i_day)
            else:
                projections = {}
                best_i_day = -1
                best_i_day_loss = float('inf')
                temp_n_days = p.n_days
                p.n_days = 1000
                for i_day in range(90):
                    self.i_day = i_day
                    raw = self.run_projection(p, self.gen_policy(p))


                    # Don't fit against results that put the peak before the present day
                    if raw["census_non_icu"].argmax() < i_day:
                        continue

                    loss = get_loss(raw["census_non_icu"][i_day], p.covid_census_value)
                    if loss < best_i_day_loss:
                        best_i_day_loss = loss
                        best_i_day = i_day
                p.n_days = temp_n_days
                self.i_day = best_i_day
                raw = self.run_projection(p, self.gen_policy(p))
                self.raw = raw

            logger.info(
                'Estimated date_first_hospitalized: %s; current_date: %s; i_day: %s',
                p.covid_census_date - timedelta(days=self.i_day),
                p.covid_census_date,
                self.i_day)

        elif p.date_first_hospitalized is not None:
            # Fitting spread parameter to observed hospital census (dates of 1 patient and today)
            self.i_day = (p.covid_census_date - p.date_first_hospitalized).days
            self.covid_census_value = p.covid_census_value
            logger.info(
                'Using date_first_hospitalized: %s; current_date: %s; i_day: %s, current_hospitalized: %s',
                p.date_first_hospitalized,
                p.covid_census_date,
                self.i_day,
                p.covid_census_value,
            )

            # Make an initial coarse estimate
            dts = np.linspace(1, 15, 15)
            min_loss = self.get_argmin_doubling_time(p, dts)

            # Refine the coarse estimate
            for iteration in range(4):
                dts = np.linspace(dts[min_loss-1], dts[min_loss+1], 15)
                min_loss = self.get_argmin_doubling_time(p, dts)

            p.doubling_time = dts[min_loss]

            logger.info('Estimated doubling_time: %s', p.doubling_time)
            intrinsic_growth_rate = get_growth_rate(p.doubling_time)
            self.beta = get_beta(intrinsic_growth_rate, self.gamma, self.susceptible, 0.0)
            self.beta_t = get_beta(intrinsic_growth_rate, self.gamma, self.susceptible, p.relative_contact_rate)
            self.raw = self.run_projection(p, self.gen_policy(p))

            self.population = p.population
        else:
            logger.info(
                'doubling_time: %s; date_first_hospitalized: %s',
                p.doubling_time,
                p.date_first_hospitalized,
            )
            raise AssertionError('doubling_time or date_first_hospitalized must be provided.')

        self.raw["date"] = self.raw["day"].astype("timedelta64[D]") + np.datetime64(p.covid_census_date)

        self.raw_df = pd.DataFrame(data=self.raw)
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
            'icu': self.raw['admits_icu'],
            'ventilators': self.raw['admits_ventilators'],
            'total': self.raw['admits_total']
        })
        self.census_df = pd.DataFrame(data={
            'day': self.raw['day'],
            'date': self.raw['date'],
            'non_icu': self.raw['census_non_icu'],
            'icu': self.raw['census_icu'],
            'ventilators': self.raw['census_ventilators'],
            'total': self.raw['census_total'],
        })
        self.beds_df = build_beds_df(self.census_df, p)
        self.ppe_df = build_ppe_df(self.census_df, p)
        self.staffing_df = build_staffing_df(self.census_df, p)

        logger.info('len(np.arange(-i_day, n_days+1)): %s', len(np.arange(-self.i_day, p.n_days+1)))
        logger.info('len(raw_df): %s', len(self.raw_df))

        self.infected = self.raw_df['infected'].values[self.i_day]
        self.susceptible = self.raw_df['susceptible'].values[self.i_day]
        self.recovered = self.raw_df['recovered'].values[self.i_day]

        self.intrinsic_growth_rate = intrinsic_growth_rate

        # r_t is r_0 after distancing
        self.r_t = self.beta_t / gamma * susceptible
        self.r_naught = self.beta / gamma * susceptible

        doubling_time_t = 1.0 / np.log2(
            self.beta_t * susceptible - gamma + 1)
        self.doubling_time_t = doubling_time_t

        self.sim_sir_w_date_df = build_sim_sir_w_date_df(self.raw_df, p.covid_census_date, self.keys)

        self.sim_sir_w_date_floor_df = build_floor_df(self.sim_sir_w_date_df, self.keys)
        self.admits_floor_df = build_floor_df(self.admits_df, p.dispositions.keys())
        self.census_floor_df = build_floor_df(self.census_df, p.dispositions.keys())
        self.beds_floor_df = build_floor_df(self.beds_df, p.dispositions.keys())
        self.ppe_floor_df = build_floor_df(self.ppe_df, self.ppe_df.columns[2:])
        self.staffing_floor_df = build_floor_df(self.staffing_df, self.staffing_df.columns[2:])

        self.daily_growth_rate = get_growth_rate(p.doubling_time)
        self.daily_growth_rate_t = get_growth_rate(self.doubling_time_t)

    def get_argmin_doubling_time(self, p: Parameters, dts):
        losses = np.full(dts.shape[0], np.inf)
        for i, i_dt in enumerate(dts):
            intrinsic_growth_rate = get_growth_rate(i_dt)
            self.beta = get_beta(intrinsic_growth_rate, self.gamma, self.susceptible, 0.0)
            self.beta_t = get_beta(intrinsic_growth_rate, self.gamma, self.susceptible, p.relative_contact_rate)

            raw = self.run_projection(p, self.gen_policy(p))

            # Skip values the would put the fit past peak
            peak_admits_day = raw["admits_non_icu"].argmax()
            if peak_admits_day < 0:
                continue

            predicted = raw["census_non_icu"][self.i_day]
            loss = get_loss(self.covid_census_value, predicted)
            losses[i] = loss

        min_loss = pd.Series(losses).argmin()
        return min_loss

    def gen_policy(self, p: Parameters) -> Sequence[Tuple[float, int]]:
        if p.mitigation_date is not None:
            mitigation_day = -(p.covid_census_date - p.mitigation_date).days
        else:
            mitigation_day = 0

        total_days = self.i_day + p.n_days

        if mitigation_day < -self.i_day:
            mitigation_day = -self.i_day

        pre_mitigation_days = self.i_day + mitigation_day
        post_mitigation_days = total_days - pre_mitigation_days

        return [
            (self.beta,   pre_mitigation_days),
            (self.beta_t, post_mitigation_days),
        ]

    def run_projection(self, p: Parameters, policy: Sequence[Tuple[float, int]]):
        raw = sim_sir(
            self.susceptible,
            self.infected,
            p.recovered,
            self.gamma,
            -self.i_day,
            policy
        )

        calculate_dispositions(raw, self.rates, p.market_share)
        calculate_admits(raw, self.rates)
        calculate_census(raw, self.days)

        return raw


def get_loss(current_hospitalized, predicted) -> float:
    """Squared error: predicted vs. actual current hospitalized."""
    return (current_hospitalized - predicted) ** 2.0


def get_argmin_ds(census, current_hospitalized: float) -> float:
    # By design, this forbids choosing a day after the peak
    # If that's a problem, see #381
    peak_day = census.argmax()
    losses = (census[:peak_day] - current_hospitalized) ** 2.0
    return losses.argmin()


def get_beta(
    intrinsic_growth_rate: float,
    gamma: float,
    susceptible: float,
    relative_contact_rate: float
) -> float:
    return (
        (intrinsic_growth_rate + gamma)
        / susceptible
        * (1.0 - relative_contact_rate)
    )


def get_growth_rate(doubling_time: Optional[float]) -> float:
    """Calculates average daily growth rate from doubling time."""
    if doubling_time is None or doubling_time == 0.0:
        return 0.0
    return (2.0 ** (1.0 / doubling_time) - 1.0)


def sir(
    s: float, i: float, r: float, beta: float, gamma: float, n: float
) -> Tuple[float, float, float]:
    """The SIR model, one time step."""
    s_n = (-beta * s * i) + s
    i_n = (beta * s * i - gamma * i) + i
    r_n = gamma * i + r
    scale = n / (s_n + i_n + r_n)
    return s_n * scale, i_n * scale, r_n * scale


def sim_sir(
    s: float, i: float, r: float, gamma: float, i_day: int, policies: Sequence[Tuple[float, int]]
):
    """Simulate SIR model forward in time, returning a dictionary of daily arrays
    Parameter order has changed to allow multiple (beta, n_days)
    to reflect multiple changing social distancing policies.
    """
    s, i, r = (float(v) for v in (s, i, r))
    n = s + i + r
    d = i_day

    total_days = 1
    for beta, days in policies:
        total_days += days

    d_a = np.empty(total_days, "int")
    s_a = np.empty(total_days, "float")
    i_a = np.empty(total_days, "float")
    r_a = np.empty(total_days, "float")

    index = 0
    for beta, n_days in policies:
        for _ in range(n_days):
            d_a[index] = d
            s_a[index] = s
            i_a[index] = i
            r_a[index] = r
            index += 1

            s, i, r = sir(s, i, r, beta, gamma, n)
            d += 1

    d_a[index] = d
    s_a[index] = s
    i_a[index] = i
    r_a[index] = r
    return {
        "day": d_a,
        "susceptible": s_a,
        "infected": i_a,
        "recovered": r_a,
        "ever_infected": i_a + r_a
    }


def build_sim_sir_w_date_df(
    raw_df: pd.DataFrame,
    current_date: datetime,
    keys: Sequence[str],
) -> pd.DataFrame:
    day = raw_df.day
    return pd.DataFrame({
        "day": day,
        "date": day.astype('timedelta64[D]') + np.datetime64(current_date),
        **{
            key: raw_df[key]
            for key in keys
        }
    })


def build_floor_df(df, keys):
    """Build floor sim sir w date."""
    return pd.DataFrame({
        "day": df.day,
        "date": df.date,
        **{
            key: np.floor(df[key])
            for key in keys
        }
    })


def calculate_dispositions(
    raw: Dict,
    rates: Dict[str, float],
    market_share: float,
):
    """Build dispositions dataframe of patients adjusted by rate and market_share."""
    for key, rate in rates.items():
        raw["ever_" + key] = raw["ever_infected"] * rate * market_share
        raw[key] = raw["ever_infected"] * rate * market_share


def calculate_admits(raw: Dict, rates):
    """Build admits dataframe from dispositions."""
    for key in rates.keys():
        ever = raw["ever_" + key]
        admit = np.empty_like(ever)
        admit[0] = np.nan
        admit[1:] = ever[1:] - ever[:-1]
        raw["admits_"+key] = admit
        raw[key] = admit
    raw['admits_total'] = np.floor(raw['admits_non_icu']) + np.floor(raw['admits_icu'])


def calculate_census(
    raw: Dict,
    lengths_of_stay: Dict[str, int],
):
    """Average Length of Stay for each disposition of COVID-19 case (total guesses)"""
    n_days = raw["day"].shape[0]
    for key, los in lengths_of_stay.items():
        cumsum = np.empty(n_days + los)
        cumsum[:los+1] = 0.0
        cumsum[los+1:] = raw["admits_" + key][1:].cumsum()

        census = cumsum[los:] - cumsum[:-los]
        raw["census_" + key] = census
    raw['census_total'] = np.floor(raw['census_non_icu']) + np.floor(raw['census_icu'])

def build_beds_df(
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
    new_hosp = []
    new_icu = []
    for row in beds_df.itertuples():
        if row.non_icu < 0 and row.icu > 0:
            needed = min(abs(row.non_icu), row.icu)
            new_hosp.append(row.non_icu + needed)
            new_icu.append(row.icu - needed)
        else: 
            new_hosp.append(row.non_icu)
            new_icu.append(row.icu)
    beds_df["non_icu"] = new_hosp
    beds_df["icu"] = new_icu
    return beds_df

def build_ppe_df(
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

    staffing_df["nurses_icu"] = np.ceil(np.ceil(
        fic / p.nurses_icu) * stf_mul) if p.nurses_icu !=0 else 0
    staffing_df["physicians_icu"] = np.ceil(np.ceil(
        fic / p.physicians_icu) * stf_mul) if p.physicians_icu !=0 else 0
    staffing_df["advanced_practice_providers_icu"] = np.ceil(np.ceil(
        fic / p.advanced_practice_providers_icu) * stf_mul) if p.advanced_practice_providers_icu !=0 else 0
    staffing_df["healthcare_assistants_icu"] = np.ceil(np.ceil(
        fic / p.healthcare_assistants_icu) * stf_mul) if p.healthcare_assistants_icu !=0 else 0

    staffing_df["nurses_total"] = np.ceil(staffing_df["nurses_non_icu"] + staffing_df["nurses_icu"])
    staffing_df["physicians_total"] = np.ceil(staffing_df["physicians_non_icu"] + staffing_df["physicians_icu"])
    staffing_df["advanced_practice_providers_total"] = np.ceil(staffing_df["advanced_practice_providers_non_icu"] + staffing_df["advanced_practice_providers_icu"])
    staffing_df["healthcare_assistants_total"] = np.ceil(staffing_df["healthcare_assistants_non_icu"] + staffing_df["healthcare_assistants_icu"])

    return staffing_df