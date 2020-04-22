"""Models.

Changes affecting results or their presentation should also update
constants.py `change_date`,
"""
from __future__ import annotations

import datetime
from logging import getLogger
from typing import Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .parameters import Parameters
from .model_base import SimSirModelBase


logger = getLogger(__name__)


class PennModel(SimSirModelBase):
    def __init__(self, p: Parameters):
        super(PennModel, self).__init__(p)

        # An estimate of the number of infected people on the day that
        # the first hospitalized case is seen
        #
        # Note: this should not be an integer.
        infected = (
            1.0 / p.market_share / p.non_icu.rate
        )

        susceptible = p.population - infected

        self.susceptible = susceptible
        self.infected = infected
        self.recovered = p.recovered

        if p.doubling_time is not None:
            # Back-projecting to when the first hospitalized case would have been admitted
            logger.info('Using doubling_time: %s', p.doubling_time)

            intrinsic_growth_rate = self.get_growth_rate(p.doubling_time)
            self.beta = self.get_beta(intrinsic_growth_rate, self.gamma, self.susceptible, 0.0)
            self.beta_t = self.get_beta(intrinsic_growth_rate, self.gamma, self.susceptible, p.relative_contact_rate)

            if p.mitigation_date is None:
                self.i_day = 0 # seed to the full length
                temp_n_days = p.n_days
                p.n_days = 1000
                raw = self.run_projection(p, [(self.beta, p.n_days)])
                self.i_day = i_day = int(self.get_argmin_ds(raw["census_non_icu"], p.covid_census_value))
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

                    loss = self.get_loss(raw["census_non_icu"][i_day], p.covid_census_value)
                    if loss < best_i_day_loss:
                        best_i_day_loss = loss
                        best_i_day = i_day
                p.n_days = temp_n_days
                self.i_day = best_i_day
                raw = self.run_projection(p, self.gen_policy(p))
                self.raw = raw

            logger.info(
                'Estimated date_first_hospitalized: %s; current_date: %s; i_day: %s',
                p.covid_census_date - datetime.timedelta(days=self.i_day),
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
            intrinsic_growth_rate = self.get_growth_rate(p.doubling_time)
            self.beta = self.get_beta(intrinsic_growth_rate, self.gamma, self.susceptible, 0.0)
            self.beta_t = self.get_beta(intrinsic_growth_rate, self.gamma, self.susceptible, p.relative_contact_rate)
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

        self.add_counts() # Adds admits, census, beds, ppe, and staffing dataframes.

        logger.info('len(np.arange(-i_day, n_days+1)): %s', len(np.arange(-self.i_day, p.n_days+1)))
        logger.info('len(raw): %s', len(self.raw))

        # These properties end up in the dynamic description text
        self.infected = self.raw['infected'][self.i_day]
        self.susceptible = self.raw['susceptible'][self.i_day]
        self.recovered = self.raw['recovered'][self.i_day]

        self.intrinsic_growth_rate = intrinsic_growth_rate

        # r_t is r_0 after distancing
        self.r_t = self.beta_t / self.gamma * susceptible
        self.r_naught = self.beta / self.gamma * susceptible

        doubling_time_t = 1.0 / np.log2(
            self.beta_t * susceptible - self.gamma + 1)
        self.doubling_time_t = doubling_time_t

        self.daily_growth_rate = self.get_growth_rate(p.doubling_time)
        self.daily_growth_rate_t = self.get_growth_rate(self.doubling_time_t)

    def get_argmin_doubling_time(self, p: Parameters, dts):
        losses = np.full(dts.shape[0], np.inf)
        for i, i_dt in enumerate(dts):
            intrinsic_growth_rate = self.get_growth_rate(i_dt)
            self.beta = self.get_beta(intrinsic_growth_rate, self.gamma, self.susceptible, 0.0)
            self.beta_t = self.get_beta(intrinsic_growth_rate, self.gamma, self.susceptible, p.relative_contact_rate)

            raw = self.run_projection(p, self.gen_policy(p))

            # Skip values the would put the fit past peak
            peak_admits_day = raw["admits_non_icu"].argmax()
            if peak_admits_day < 0:
                continue

            predicted = raw["census_non_icu"][self.i_day]
            loss = self.get_loss(self.covid_census_value, predicted)
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
        raw = self.sim_sir(
            self.susceptible,
            self.infected,
            p.recovered,
            self.gamma,
            -self.i_day,
            policy
        )

        self.calculate_dispositions(raw, self.rates, p.market_share)
        self.calculate_admits(raw, self.rates)
        self.calculate_census(raw, self.days)

        return raw


    def get_loss(self, current_hospitalized, predicted) -> float:
        """Squared error: predicted vs. actual current hospitalized."""
        return (current_hospitalized - predicted) ** 2.0


    def get_argmin_ds(self, census, current_hospitalized: float) -> float:
        # By design, this forbids choosing a day after the peak
        # If that's a problem, see #381
        peak_day = census.argmax()
        losses = (census[:peak_day] - current_hospitalized) ** 2.0
        return losses.argmin()


    def get_beta(
        self,
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


    def get_growth_rate(self, doubling_time: Optional[float]) -> float:
        """Calculates average daily growth rate from doubling time."""
        if doubling_time is None or doubling_time == 0.0:
            return 0.0
        return (2.0 ** (1.0 / doubling_time) - 1.0)


    def sim_sir(
        self, s: float, i: float, r: float, gamma: float, i_day: int, policies: Sequence[Tuple[float, int]]
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

                s, i, r = self.sir(s, i, r, beta, gamma, n)
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

