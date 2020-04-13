"""Models.

Changes affecting results or their presentation should also update
constants.py `change_date`,
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from logging import INFO, basicConfig, getLogger
from sys import stdout
from typing import Dict, Generator, Tuple, Sequence,Optional

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

        # Note: this should not be an integer.
        # We're appoximating infected from what we do know.
        # TODO market_share > 0, hosp_rate > 0
        infected = (
            1.0 / p.market_share / p.hospitalized.rate
        )

        susceptible = p.population - infected

        intrinsic_growth_rate = get_growth_rate(p.doubling_time)

        gamma = 1.0 / p.infectious_days

        # Contact rate, beta
        beta = (
            (intrinsic_growth_rate + gamma)
            / susceptible
            * (1.0 - p.relative_contact_rate)
        )  # {rate based on doubling time} / {initial susceptible}

        # r_t is r_0 after distancing
        r_t = beta / gamma * susceptible

        # Simplify equation to avoid division by zero:
        # self.r_naught = r_t / (1.0 - relative_contact_rate)
        r_naught = (intrinsic_growth_rate + gamma) / gamma

        self.susceptible = susceptible
        self.infected = infected
        self.recovered = p.recovered

        self.beta = beta
        self.gamma = gamma
        self.beta_t = get_beta(intrinsic_growth_rate, self.gamma, self.susceptible, p.relative_contact_rate)
        self.intrinsic_growth_rate = intrinsic_growth_rate

        # if p.date_first_hospitalized is None and p.doubling_time is not None:
        if p.doubling_time is not None:
            logger.info('Using doubling_time: %s', p.doubling_time)
            self.i_day = 0
            self.beta = (
                (intrinsic_growth_rate + gamma)
                / susceptible
            )

            self.i_day = 0 # seed to the full length
            self.beta_t = self.beta
            n_day_tmp = p.n_days
            p.n_days = 1000
            self.run_projection(p)
            self.i_day = i_day = int(get_argmin_ds(self.census_df, p.covid_census_value))
            p.n_days = n_day_tmp

            self.beta_t = get_beta(intrinsic_growth_rate, self.gamma, self.susceptible, p.relative_contact_rate)
            self.run_projection(p)

            self.r_t = self.beta_t / gamma * susceptible
            self.r_naught = self.beta / gamma * susceptible
            logger.info('Set i_day = %s', i_day)
            p.date_first_hospitalized = p.current_date - timedelta(days=i_day)
            logger.info(
                'Estimated date_first_hospitalized: %s; current_date: %s; i_day: %s',
                p.date_first_hospitalized,
                p.current_date,
                self.i_day)
        
        # elif p.date_first_hospitalized is not None and p.doubling_time is None:
        elif p.date_first_hospitalized is not None:
            self.i_day = (p.current_date - p.date_first_hospitalized).days
            logger.info(
                'Using date_first_hospitalized: %s; current_date: %s; i_day: %s',
                p.date_first_hospitalized,
                p.current_date,
                self.i_day)
            min_loss = 2.0**99
            dts = np.linspace(1, 15, 29)
            losses = np.zeros(dts.shape[0])
            self.covid_census_value = p.covid_census_value
            for i, i_dt in enumerate(dts):
                intrinsic_growth_rate = get_growth_rate(i_dt)
                self.beta = get_beta(intrinsic_growth_rate, self.gamma, self.susceptible, 0.0)
                self.beta_t = get_beta(intrinsic_growth_rate, self.gamma, self.susceptible, p.relative_contact_rate)

                self.run_projection(p)
                # Only use projection if i_day is to the left of the census maximum
                if self.i_day > self.census_df.total.idxmax():
                    losses[i] = np.inf
                loss = self.get_loss()
                losses[i] = loss

            p.doubling_time = dts[pd.Series(losses).argmin()]
            logger.info('Estimated doubling_time: %s', p.doubling_time)
            intrinsic_growth_rate = get_growth_rate(p.doubling_time)
            self.beta = get_beta(intrinsic_growth_rate, self.gamma, self.susceptible, 0.0)
            self.beta_t = get_beta(intrinsic_growth_rate, self.gamma, self.susceptible, p.relative_contact_rate)
            self.run_projection(p)

            self.intrinsic_growth_rate = intrinsic_growth_rate
            self.population = p.population
        else:
            logger.info(
                'doubling_time: %s; date_first_hospitalized: %s',
                p.doubling_time,
                p.date_first_hospitalized,
            )
            raise AssertionError('doubling_time or date_first_hospitalized must be provided.')

        logger.info('len(np.arange(-i_day, n_days+1)): %s', len(np.arange(-self.i_day, p.n_days+1)))
        logger.info('len(raw_df): %s', len(self.raw_df))

        self.infected = self.raw_df['infected'].values[self.i_day]
        self.susceptible = self.raw_df['susceptible'].values[self.i_day]
        self.recovered = self.raw_df['recovered'].values[self.i_day]

        self.r_t = self.beta_t / gamma * susceptible
        self.r_naught = self.beta / gamma * susceptible

        doubling_time_t = 1.0 / np.log2(
            self.beta_t * susceptible - gamma + 1)
        self.doubling_time_t = doubling_time_t

        self.sim_sir_w_date_df = build_sim_sir_w_date_df(self.raw_df, p.current_date, self.keys)

        self.sim_sir_w_date_floor_df = build_floor_df(self.sim_sir_w_date_df, self.keys)
        self.admits_floor_df = build_floor_df(self.admits_df, p.dispositions.keys())
        self.census_floor_df = build_floor_df(self.census_df, p.dispositions.keys())
        self.beds_floor_df = build_floor_df(self.beds_df, p.dispositions.keys())
        self.ppe_floor_df = build_floor_df(self.ppe_df, self.ppe_df.columns[2:])
        self.staffing_floor_df = build_floor_df(self.staffing_df, self.staffing_df.columns[2:])

        self.daily_growth_rate = get_growth_rate(p.doubling_time)
        self.daily_growth_rate_t = get_growth_rate(self.doubling_time_t)

    def run_projection(self, p):
        self.raw_df = sim_sir_df(
            self.susceptible,
            self.infected,
            p.recovered,
            self.gamma,
            -self.i_day,
            self.beta,
            self.i_day,
            self.beta_t,
            p.n_days
        )
        self.dispositions_df = build_dispositions_df(self.raw_df, self.rates, p.market_share, p.current_date)
        self.admits_df = build_admits_df(self.dispositions_df)
        self.census_df = build_census_df(self.admits_df, self.days)
        self.beds_df = build_beds_df(self.census_df, p)
        self.ppe_df = build_ppe_df(self.census_df, p)
        self.staffing_df = build_staffing_df(self.census_df, p)
        self.current_infected = self.raw_df.infected.loc[self.i_day]

    def get_loss(self) -> float:
        """Squared error: predicted vs. actual current hospitalized."""
        predicted = self.census_df.hospitalized.loc[self.i_day]
        return (self.covid_census_value - predicted) ** 2.0


def get_argmin_ds(census_df: pd.DataFrame, covid_census_value: float) -> float:
    # By design, this forbids choosing a day after the peak
    # If that's a problem, see #381
    peak_day = census_df.hospitalized.argmax()
    losses_df = (census_df.hospitalized[:peak_day] - covid_census_value) ** 2.0
    return losses_df.argmin()


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

    # TODO:
    #   Post check dfs for negative values and
    #   warn the user that their input data is bad.
    #   JL: I suspect that these adjustments covered bugs.

    #if s_n < 0.0:
    #    s_n = 0.0
    #if i_n < 0.0:
    #    i_n = 0.0
    #if r_n < 0.0:
    #    r_n = 0.0
    scale = n / (s_n + i_n + r_n)
    return s_n * scale, i_n * scale, r_n * scale


def gen_sir(
    s: float, i: float, r: float, gamma: float, i_day: int, *args
) -> Generator[Tuple[int, float, float, float], None, None]:
    """Simulate SIR model forward in time yielding tuples.
    Parameter order has changed to allow multiple (beta, n_days)
    to reflect multiple changing social distancing policies.
    """
    s, i, r = (float(v) for v in (s, i, r))
    n = s + i + r
    d = i_day
    while args:
        beta, n_days, *args = args
        for _ in range(n_days):
            yield d, s, i, r
            s, i, r = sir(s, i, r, beta, gamma, n)
            d += 1
    yield d, s, i, r


def sim_sir_df(
    s: float, i: float, r: float,
    gamma: float, i_day: int, *args
) -> pd.DataFrame:
    """Simulate the SIR model forward in time."""
    return pd.DataFrame(
        data=gen_sir(s, i, r, gamma, i_day, *args),
        columns=("day", "susceptible", "infected", "recovered"),
    )


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


def build_dispositions_df(
    raw_df: pd.DataFrame,
    rates: Dict[str, float],
    market_share: float,
    current_date: datetime,
) -> pd.DataFrame:
    """Build dispositions dataframe of patients adjusted by rate and market_share."""
    patients = raw_df.infected + raw_df.recovered
    day = raw_df.day
    return pd.DataFrame({
        "day": day,
        "date": day.astype('timedelta64[D]') + np.datetime64(current_date),
        **{
            key: patients * rate * market_share
            for key, rate in rates.items()
        }
    })


def build_admits_df(dispositions_df: pd.DataFrame) -> pd.DataFrame:
    """Build admits dataframe from dispositions."""
    admits_df = dispositions_df.iloc[:, :] - dispositions_df.shift(1)
    admits_df.day = dispositions_df.day
    admits_df.date = dispositions_df.date
    admits_df["total"] = np.floor(admits_df.hospitalized) + np.floor(admits_df.icu)
    return admits_df


def build_census_df(
    admits_df: pd.DataFrame,
    lengths_of_stay: Dict[str, int],
) -> pd.DataFrame:
    """Average Length of Stay for each disposition of COVID-19 case (total guesses)"""
    census_df = pd.DataFrame({
        'day': admits_df.day,
        'date': admits_df.date,
        **{
            key: (
                admits_df[key].cumsum()
                - admits_df[key].cumsum().shift(los).fillna(0)
            )
            for key, los in lengths_of_stay.items()
        }
    })
    census_df["total"] = np.floor(census_df["hospitalized"]) + np.floor(census_df["icu"])
    return(census_df)

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
    beds_df["hospitalized"] = p.total_covid_beds - p.icu_covid_beds - census_df["hospitalized"]
    beds_df["icu"] = p.icu_covid_beds - census_df["icu"]
    beds_df["ventilators"] = p.covid_ventilators - census_df["ventilators"]
    beds_df["total"] = p.total_covid_beds - census_df["hospitalized"] - census_df["icu"]
    # beds_df = beds_df.head(n_days)

    # Shift people to ICU if main hospital is full and ICU is not.
    new_hosp = []
    new_icu = []
    for row in beds_df.itertuples():
        if row.hospitalized < 0 and row.icu > 0:
            needed = min(abs(row.hospitalized), row.icu)
            new_hosp.append(row.hospitalized + needed)
            new_icu.append(row.icu - needed)
        else: 
            new_hosp.append(row.hospitalized)
            new_icu.append(row.icu)
    beds_df["hospitalized"] = new_hosp
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

    floored_hospitalized_census = np.floor(census_df.hospitalized)
    ppe_df["masks_n95_hosp"] = p.masks_n95 * floored_hospitalized_census
    ppe_df["masks_surgical_hosp"] = p.masks_surgical * floored_hospitalized_census
    ppe_df["face_shield_hosp"] = p.face_shield * floored_hospitalized_census
    ppe_df["gloves_hosp"] = p.gloves * floored_hospitalized_census
    ppe_df["gowns_hosp"] = p.gowns * floored_hospitalized_census
    ppe_df["other_ppe_hosp"] = p.other_ppe * floored_hospitalized_census

    floored_icu_census = np.floor(census_df.icu)
    ppe_df["masks_n95_icu"] = p.masks_n95_icu * floored_icu_census
    ppe_df["masks_surgical_icu"] = p.masks_surgical_icu * floored_icu_census
    ppe_df["face_shield_icu"] = p.face_shield_icu * floored_icu_census
    ppe_df["gloves_icu"] = p.gloves_icu * floored_icu_census
    ppe_df["gowns_icu"] = p.gowns_icu * floored_icu_census
    ppe_df["other_ppe_icu"] = p.other_ppe_icu * floored_icu_census
    
    ppe_df["masks_n95_total"] = ppe_df["masks_n95_hosp"] + ppe_df["masks_n95_icu"]
    ppe_df["masks_surgical_total"] = ppe_df["masks_surgical_hosp"] + ppe_df["masks_surgical_icu"]
    ppe_df["face_shield_total"] = ppe_df["face_shield_hosp"] + ppe_df["face_shield_icu"]
    ppe_df["gloves_total"] = ppe_df["gloves_hosp"] + ppe_df["gloves_icu"]
    ppe_df["gowns_total"] = ppe_df["gowns_hosp"] + ppe_df["gowns_icu"]
    ppe_df["other_ppe_total"] = ppe_df["other_ppe_hosp"] + ppe_df["other_ppe_icu"]

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
    fhc = np.floor(census_df.hospitalized) # floored hospitalized census
    fic = np.floor(census_df.icu) # floored icu census

    staffing_df["nurses_hosp"] = np.ceil(np.ceil(
        fhc / p.nurses) * stf_mul) if p.nurses !=0 else 0
    staffing_df["physicians_hosp"] = np.ceil(np.ceil(
        fhc / p.physicians) * stf_mul) if p.physicians != 0 else 0
    staffing_df["advanced_practice_providers_hosp"] = np.ceil(np.ceil(
        fhc / p.advanced_practice_providers) * stf_mul) if p.advanced_practice_providers != 0 else 0
    staffing_df["healthcare_assistants_hosp"] = np.ceil(np.ceil(
        fhc / p.healthcare_assistants) * stf_mul) if p.healthcare_assistants != 0 else 0

    staffing_df["nurses_icu"] = np.ceil(np.ceil(
        fic / p.nurses_icu) * stf_mul) if p.nurses_icu !=0 else 0
    staffing_df["physicians_icu"] = np.ceil(np.ceil(
        fic / p.physicians_icu) * stf_mul) if p.physicians_icu !=0 else 0
    staffing_df["advanced_practice_providers_icu"] = np.ceil(np.ceil(
        fic / p.advanced_practice_providers_icu) * stf_mul) if p.advanced_practice_providers_icu !=0 else 0
    staffing_df["healthcare_assistants_icu"] = np.ceil(np.ceil(
        fic / p.healthcare_assistants_icu) * stf_mul) if p.healthcare_assistants_icu !=0 else 0

    staffing_df["nurses_total"] = np.ceil(staffing_df["nurses_hosp"] + staffing_df["nurses_icu"])
    staffing_df["physicians_total"] = np.ceil(staffing_df["physicians_hosp"] + staffing_df["physicians_icu"])
    staffing_df["advanced_practice_providers_total"] = np.ceil(staffing_df["advanced_practice_providers_hosp"] + staffing_df["advanced_practice_providers_icu"])
    staffing_df["healthcare_assistants_total"] = np.ceil(staffing_df["healthcare_assistants_hosp"] + staffing_df["healthcare_assistants_icu"])

    return staffing_df
