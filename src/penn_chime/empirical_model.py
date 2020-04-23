import pandas as pd
import numpy as np
import scipy.stats as sps

from .model_base import SimSirModelBase
from .parameters import Parameters


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

    def __init__(self, p: Parameters, actuals: pd.DataFrame):
        super(EmpiricalModel, self).__init__(p)

        self.actuals = actuals
        self.GAMMA = 1 / 7
        self.R_T_MAX = 12
        self.r_t_range = np.linspace(0, self.R_T_MAX, self.R_T_MAX*100+1)

        rt_df = self.get_rt_values(self.actuals)
        rt_df_forecasted = self.forecast_rt(rt_df, p)
        # Fit model to actuals
        s_0, i_0, r_0 = None, None, None # Get current s, i, r values
        betas = None # Get betas
        self.raw = self.run_projection(self.p.n_days, s_0, i_0, r_0, betas, self.gamma)
        self.add_counts()

    def get_rt_values(self, actuals: pd.DataFrame):
        # Assuming actuals is the actuals file that the user uploads, transform it in to the shape that
        # the R_t code expects. (Series of cumulative cases with a DateTime index)
        cases = (
            actuals[['date', 'total_admissions_actual']]
            .assign(total_admissions_actual = lambda d: np.cumsum(d.total_admissions_actual))
            .set_index('date')
            .squeeze()
        )
        cases_prepped, smoothed = self.prepare_cases(cases, min_cases=self.min_cases)
        posteriors, log_likelihood = self.get_posteriors(smoothed, sigma=.25)
        hdis = self.highest_density_interval(posteriors, p=.9)
        most_likely = posteriors.idxmax().rename('ML')
        result = pd.concat([most_likely, hdis], axis=1)
        return result

    def forecast_rt(self, rt_df, p):
        raise NotImplementedError()

    def prepare_cases(self, cases, min_cases, win_size=7):
        new_cases = cases.diff()
        smoothed = new_cases.rolling(
            win_size,
            win_type='gaussian',
            min_periods=1,
            center=True).mean(std=2).round()
        idx_start = np.searchsorted(smoothed, min_cases)
        smoothed = smoothed.iloc[idx_start:]
        original = new_cases.loc[smoothed.index]
        return original, smoothed

    def get_posteriors(self, sr: pd.Series, sigma: float):
        # (1) Calculate Lambda
        lam = sr[:-1].values * np.exp(self.GAMMA * (self.r_t_range[:, None] - 1))
        # (2) Calculate each day's likelihood
        likelihoods = pd.DataFrame(
            data = sps.poisson.pmf(sr[1:].values, lam),
            index = self.r_t_range,
            columns = sr.index[1:])
        # (3) Create the Gaussian Matrix
        process_matrix = sps.norm(loc=self.r_t_range,
                                scale=sigma
                                ).pdf(self.r_t_range[:, None]) 
        # (3a) Normalize all rows to sum to 1
        process_matrix /= process_matrix.sum(axis=0)
        # (4) Calculate the initial prior
        prior0 = sps.gamma(a=4).pdf(self.r_t_range)
        prior0 /= prior0.sum()
        # Create a DataFrame that will hold our posteriors for each day
        # Insert our prior as the first posterior.
        posteriors = pd.DataFrame(
            index=self.r_t_range,
            columns=sr.index,
            data={sr.index[0]: prior0}
        )
        # We said we'd keep track of the sum of the log of the probability
        # of the data for maximum likelihood calculation.
        log_likelihood = 0.0
        # (5) Iteratively apply Bayes' rule
        for previous_day, current_day in zip(sr.index[:-1], sr.index[1:]):
            #(5a) Calculate the new prior
            current_prior = process_matrix @ posteriors[previous_day]
            #(5b) Calculate the numerator of Bayes' Rule: P(k|R_t)P(R_t)
            numerator = likelihoods[current_day] * current_prior
            #(5c) Calcluate the denominator of Bayes' Rule P(k)
            denominator = np.sum(numerator)
            # Execute full Bayes' Rule
            posteriors[current_day] = numerator/denominator
            # Add to the running sum of log likelihoods
            log_likelihood += np.log(denominator)
        return posteriors, log_likelihood


    def highest_density_interval(self, pmf, p=.9):
        # If we pass a DataFrame, just call this recursively on the columns
        if(isinstance(pmf, pd.DataFrame)):
            return pd.DataFrame([self.highest_density_interval(pmf[col], p=p) for col in pmf],
                                index=pmf.columns)
        cumsum = np.cumsum(pmf.values)
        # N x N matrix of total probability mass for each low, high
        total_p = cumsum - cumsum[:, None]
        # Return all indices with total_p > p
        lows, highs = (total_p > p).nonzero()
        # Find the smallest range (highest density)
        best = (highs - lows).argmin()
        low = pmf.index[lows[best]]
        high = pmf.index[highs[best]]
        return pd.Series(
            [low, high],
            index=[f'Low_{p*100:.0f}',
                   f'High_{p*100:.0f}'],
        )
    
    def run_projection(self, n_days, s_0, i_0, r_0, betas, gamma):
        raw = self.sim_sir(n_days, s_0, i_0, r_0, betas, gamma)
        self.calculate_dispositions(raw, self.rates, self.p.market_share)
        self.calculate_admits(raw, self.rates)
        self.calculate_census(raw, self.days)

        return raw

    def sim_sir(self, n_days, s_0, i_0, r_0, betas, gamma):
        """
        Runs the SIR model for n_days starting with the specified initial
        values of s, i, and r, using a variable `beta` for each of the n_days.
        """
        if len(betas) != n_days:
            raise ValueError(f"betas must have length == n_days({len(n_days)}). Got length == {len(betas)}")

        s_a, i_a, r_a = np.zeros(n_days), np.zeros(n_days), np.zeros(n_days)
    
        for index in range(n_days):
            s_a[index] = s_n
            i_a[index] = i_n
            r_a[index] = r_n

            s = s_n
            i = i_n
            r = r_n
            
            s_n = (-betas[index] * s * i) + s
            i_n = (betas[index] * s * i - gamma * i) + i
            r_n = gamma * i + r
        return {
            "day": np.arange(len(s_a)),
            "susceptible": s_a,
            "infected": i_a,
            "recovered": r_a,
            "ever_infected": i_a + r_a
        }